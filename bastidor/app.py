"""Detective de bastidor — web Flask.

Junta dos fuentes 100% gratis:
  1. Decode del VIN (marca/modelo/año/motor)  -> vin.py  (+ API NHTSA opcional)
  2. Historial de titulares                    -> dgt_microdatos.py (Open Data DGT)

Arrancar:  python app.py   ->  http://localhost:5000
"""
from __future__ import annotations

from flask import Flask, render_template, request

from vin import decode, normalize, validate, VinError
from dgt_microdatos import historial

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

    hist = historial(vin)  # None si aún no hay microdatos ingeridos
    return render_template("resultado.html", d=datos, hist=hist)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
