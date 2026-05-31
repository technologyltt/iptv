"""Decodificación de VIN / número de bastidor.

- Valida longitud y caracteres permitidos.
- Calcula el dígito de control (posición 9) -- obligatorio en coches de
  EE.UU./Canadá, opcional en europeos.
- Extrae el año de modelo (posición 10).
- Identifica fabricante/marca y país vía tabla WMI local (wmi.py).
- Si hay internet, enriquece con la API pública y gratuita de la NHTSA
  (modelo, motor, cilindrada, carrocería, etc.).
"""
from __future__ import annotations

import datetime
import json
import urllib.request
import urllib.error

from wmi import brand_from_vin, country_from_vin

# Caracteres válidos: el VIN no usa I, O ni Q (para no confundir con 1/0)
_VALID = set("ABCDEFGHJKLMNPRSTUVWXYZ0123456789")

# Transliteración para el dígito de control
_TRANSLIT = {
    **{str(d): d for d in range(10)},
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

# Año de modelo por la posición 10 (código -> año base 1980-2009)
_YEAR_BASE = {
    "A": 1980, "B": 1981, "C": 1982, "D": 1983, "E": 1984, "F": 1985,
    "G": 1986, "H": 1987, "J": 1988, "K": 1989, "L": 1990, "M": 1991,
    "N": 1992, "P": 1993, "R": 1994, "S": 1995, "T": 1996, "V": 1997,
    "W": 1998, "X": 1999, "Y": 2000, "1": 2001, "2": 2002, "3": 2003,
    "4": 2004, "5": 2005, "6": 2006, "7": 2007, "8": 2008, "9": 2009,
}


class VinError(ValueError):
    pass


def normalize(vin: str) -> str:
    return (vin or "").strip().upper().replace(" ", "").replace("-", "")


def is_vin(s: str) -> bool:
    """True si `s` tiene pinta de VIN válido (17 chars, sin I/O/Q)."""
    s = (s or "").strip().upper()
    return len(s) == 17 and all(c in _VALID for c in s)


def validate(vin: str) -> tuple[bool, str | None]:
    """Devuelve (es_valido, mensaje_error)."""
    if len(vin) != 17:
        return False, f"El bastidor debe tener 17 caracteres (tiene {len(vin)})."
    bad = [c for c in vin if c not in _VALID]
    if bad:
        return False, f"Caracteres no válidos: {', '.join(sorted(set(bad)))}. " \
                      "El VIN no usa las letras I, O ni Q."
    return True, None


def check_digit_ok(vin: str) -> bool | None:
    """True/False si el dígito de control cuadra; None si no es comprobable."""
    try:
        total = sum(_TRANSLIT[c] * w for c, w in zip(vin, _WEIGHTS))
    except KeyError:
        return None
    rem = total % 11
    expected = "X" if rem == 10 else str(rem)
    return vin[8] == expected


def model_year(vin: str) -> int | None:
    """Año de modelo. Resuelve la ambigüedad de 30 años (1980-2009 vs 2010-2039)
    eligiendo el año más reciente que no supere el actual."""
    code = vin[9]
    base = _YEAR_BASE.get(code)
    if base is None:
        return None
    now = datetime.date.today().year + 1  # los modelos salen ~1 año antes
    candidate = base
    while candidate + 30 <= now:
        candidate += 30
    return candidate


def _nhtsa_lookup(vin: str, timeout: float = 6.0) -> dict | None:
    """Consulta la API gratuita de la NHTSA (vPIC). Devuelve None si falla."""
    url = (
        "https://vpic.nhtsa.dot.gov/api/vehicles/"
        f"DecodeVinValues/{vin}?format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bastidor-detective/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    results = data.get("Results") or []
    if not results:
        return None
    row = results[0]
    keep = {
        "Marca": row.get("Make"),
        "Modelo": row.get("Model"),
        "Año": row.get("ModelYear"),
        "Tipo de vehículo": row.get("VehicleType"),
        "Carrocería": row.get("BodyClass"),
        "Cilindrada (L)": row.get("DisplacementL"),
        "Cilindros": row.get("EngineCylinders"),
        "Potencia (CV)": row.get("EngineHP"),
        "Combustible": row.get("FuelTypePrimary"),
        "Puertas": row.get("Doors"),
        "Tracción": row.get("DriveType"),
        "Planta de fabricación": row.get("PlantCity"),
        "País de la planta": row.get("PlantCountry"),
    }
    cleaned = {k: v for k, v in keep.items() if v not in (None, "", "Not Applicable")}
    return cleaned or None


def decode(vin_raw: str, online: bool = True) -> dict:
    """Decodifica un VIN. Lanza VinError si no es válido."""
    vin = normalize(vin_raw)
    ok, err = validate(vin)
    if not ok:
        raise VinError(err)

    result: dict = {
        "vin": vin,
        "wmi": vin[:3],
        "marca": brand_from_vin(vin),
        "pais_fabricacion": country_from_vin(vin),
        "anio_modelo": model_year(vin),
        "digito_control": check_digit_ok(vin),
        "numero_serie": vin[11:],
        "fuente_online": False,
        "detalle": {},
    }

    if online:
        extra = _nhtsa_lookup(vin)
        if extra:
            result["detalle"] = extra
            result["fuente_online"] = True
            if not result["marca"] and extra.get("Marca"):
                result["marca"] = extra["Marca"]
    return result
