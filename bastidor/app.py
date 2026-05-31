"""Detective de bastidor — web Flask.

Fuentes GRATIS:
  1. Decode del VIN (marca/modelo/año/motor)  -> vin.py  (+ API NHTSA opcional)
  2. Historial de titulares                    -> dgt_microdatos.py (Open Data DGT)

Producto de PAGO (opcional, modelo de negocio de seisenlinea & co):
  3. Informe completo (km, golpes...)          -> providers.py + payments.py

Arrancar:  python app.py   ->  http://localhost:5000
"""
from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, url_for

from vin import decode, normalize, validate, VinError
from dgt_microdatos import historial
from providers import get_provider
import payments
import calc
import matricula

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/buscar", methods=["POST"])
def buscar():
    vin_raw = request.form.get("bastidor", "")
    vin = normalize(vin_raw)
    ok, err = validate(vin)
    if not ok:
        return render_template("index.html", error=err, valor=vin_raw)
    try:
        datos = decode(vin, online=True)
    except VinError as e:
        return render_template("index.html", error=str(e), valor=vin_raw)
    hist = historial(vin)
    return render_template(
        "resultado.html", d=datos, hist=hist,
        pago_activo=payments.enabled(),
        precio=payments.precio_centimos() / 100,
    )


# --- Informe completo (de pago) ---------------------------------------------
@app.route("/informe-completo/<vin>", methods=["GET"])
def informe_completo(vin):
    vin = normalize(vin)
    ok, _ = validate(vin)
    if not ok:
        return redirect(url_for("index"))

    # Entregamos el informe si el pago está confirmado, ya sea por webhook
    # (almacén) o por verificación directa de la sesión al volver de Stripe.
    session_id = request.args.get("session_id")
    if payments.is_paid(vin) or (session_id and payments.pago_confirmado(session_id)):
        payments.mark_paid(vin)
        datos = get_provider().fetch(vin)
        return render_template("informe.html", vin=vin, pago=datos)

    return render_template(
        "informe.html", vin=vin, pago=None,
        pago_activo=payments.enabled(),
        proveedor_activo=get_provider().available(),
        precio=payments.precio_centimos() / 100,
    )


@app.route("/pago/crear/<vin>", methods=["POST"])
def pago_crear(vin):
    vin = normalize(vin)
    ok, _ = validate(vin)
    if not ok:
        return redirect(url_for("index"))
    if not payments.enabled():
        return render_template("informe.html", vin=vin, pago=None,
                               pago_activo=False, proveedor_activo=False,
                               precio=payments.precio_centimos() / 100,
                               error="Pago no configurado (falta STRIPE_SECRET_KEY).")
    success = url_for("informe_completo", vin=vin, _external=True) + \
        "?session_id={CHECKOUT_SESSION_ID}"
    cancel = url_for("informe_completo", vin=vin, _external=True)
    try:
        sesion = payments.crear_checkout(vin, success, cancel)
    except Exception as e:  # noqa: BLE001
        return render_template("informe.html", vin=vin, pago=None,
                               pago_activo=True, proveedor_activo=True,
                               precio=payments.precio_centimos() / 100,
                               error=f"Error creando el pago: {e}")
    return redirect(sesion["url"])


@app.route("/pago/webhook", methods=["POST"])
def pago_webhook():
    """Webhook de Stripe: marca el VIN como pagado de forma segura."""
    evento = payments.verify_webhook(request.get_data(),
                                     request.headers.get("Stripe-Signature", ""))
    if evento is None:
        abort(400)
    if evento.get("type") == "checkout.session.completed":
        vin = (evento.get("data", {}).get("object", {})
               .get("client_reference_id"))
        if vin:
            payments.mark_paid(vin)
    return "", 200


# --- Herramientas ------------------------------------------------------------
@app.route("/herramientas", methods=["GET"])
def herramientas():
    return render_template("herramientas.html")


@app.route("/fecha-matriculacion", methods=["GET", "POST"])
def fecha_matriculacion():
    resultado = error = None
    if request.method == "POST":
        anclas = {}
        ref_p = request.form.get("ref_matricula", "").strip()
        ref_f = request.form.get("ref_fecha", "").strip()
        if ref_p and ref_f:
            anclas[ref_p] = ref_f
        try:
            resultado = matricula.estimar_fecha(
                request.form.get("matricula", ""), anclas).isoformat()
        except matricula.MatriculaError as e:
            error = str(e)
    return render_template("fecha_matriculacion.html",
                           resultado=resultado, error=error)


@app.route("/valor-hacienda", methods=["GET", "POST"])
def valor_hacienda():
    resultado = pct = error = None
    if request.method == "POST":
        try:
            precio = float(request.form.get("precio", 0).replace(",", "."))
            anios = float(request.form.get("anios", 0).replace(",", "."))
            pct = calc.porcentaje_depreciacion(anios)
            resultado = calc.valor_fiscal(precio, anios)
        except (ValueError, TypeError) as e:
            error = f"Datos no válidos: {e}"
    return render_template("valor_hacienda.html",
                           resultado=resultado, pct=pct, error=error)


@app.route("/coste-transferencia", methods=["GET", "POST"])
def coste_transferencia():
    resultado = error = None
    ccaa = request.form.get("ccaa", "Madrid")
    if request.method == "POST":
        try:
            valor = float(request.form.get("valor", 0).replace(",", "."))
            override = request.form.get("tipo_itp", "").strip().replace(",", ".")
            tipo = float(override) if override else calc.ITP_CCAA.get(ccaa, 4.0)
            gestoria = float(request.form.get("gestoria", 0) or 0)
            resultado = calc.coste_transferencia(
                valor, tipo, request.form.get("tipo_veh") == "moto", gestoria)
            resultado["tipo_aplicado"] = tipo
        except (ValueError, TypeError) as e:
            error = f"Datos no válidos: {e}"
    return render_template("coste_transferencia.html", resultado=resultado,
                           error=error, ccaas=calc.ITP_CCAA, ccaa_sel=ccaa)


@app.route("/potencia-fiscal", methods=["GET", "POST"])
def potencia_fiscal():
    resultado = error = None
    if request.method == "POST":
        try:
            resultado = calc.potencia_fiscal(
                float(request.form.get("diametro", 0).replace(",", ".")),
                float(request.form.get("carrera", 0).replace(",", ".")),
                int(request.form.get("cilindros", 0)),
                request.form.get("tiempos", "4") == "4",
            )
        except (ValueError, TypeError) as e:
            error = f"Datos no válidos: {e}"
    return render_template("potencia_fiscal.html", resultado=resultado, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
