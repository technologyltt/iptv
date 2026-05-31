"""Detective de bastidor — web Flask.

Fuentes GRATIS:
  1. Decode del VIN (marca/modelo/año/motor)  -> vin.py  (+ API NHTSA opcional)
  2. Historial de titulares                    -> dgt_microdatos.py (Open Data DGT)

Producto de PAGO (opcional, modelo de negocio de seisenlinea & co):
  3. Informe completo (km, golpes...)          -> providers.py + payments.py

Arrancar:  python app.py   ->  http://localhost:5000
"""
from __future__ import annotations

from flask import Flask, redirect, render_template, request, url_for

from vin import decode, normalize, validate, VinError
from dgt_microdatos import historial
from providers import get_provider
import payments
import calc

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

    # Si vuelve de Stripe con sesión pagada -> entregamos el informe
    session_id = request.args.get("session_id")
    if session_id and payments.pago_confirmado(session_id):
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


# --- Herramientas ------------------------------------------------------------
@app.route("/herramientas", methods=["GET"])
def herramientas():
    return render_template("herramientas.html")


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
