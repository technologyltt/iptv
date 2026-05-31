"""Calculadora de fecha de matriculación (matrículas españolas desde sep-2000).

Formato actual: NNNN LLL  (4 dígitos + 3 consonantes), p.ej. "1234 BCD".
Las letras usan solo consonantes, en este orden (sin vocales ni Ñ ni Q):

    B C D F G H J K L M N P R S T V W X Y Z   (20 letras)

Las matrículas se asignan de forma SECUENCIAL a nivel nacional: primero avanza
el número 0000→9999, y al agotarse sube el sufijo de letras como un cuentakm
(la letra de la derecha es la que cambia más rápido). La primera matrícula del
sistema fue **0000 BBB el 18/09/2000**.

Como la velocidad de emisión varía, NO se puede saber la fecha exacta a partir
de la matrícula sola: se ESTIMA interpolando entre "anclas" conocidas
(matrícula ↔ fecha real). Cuantas más anclas, más precisión. Anclas de calidad:
la página de la DGT "última matrícula asignada" (mensual, exacta) o tus propios
microdatos de la DGT.

Aquí no inventamos datos: se parte del ancla cierta (BBB = 18/09/2000) y tú
añades al menos una matrícula reciente que conozcas (o cargas anclas por JSON
con MATRICULA_ANCHORS) para poder estimar.
"""
from __future__ import annotations

import datetime
import json
import os
import re

ALFABETO = "BCDFGHJKLMNPRSTVWXYZ"  # 20 consonantes, en orden de asignación
_IDX = {c: i for i, c in enumerate(ALFABETO)}
_RE = re.compile(r"^(\d{4})\s*([" + ALFABETO + r"]{3})$")

# Ancla cierta: primera matrícula del sistema.
_ANCLA_BASE = ("0000BBB", "2000-09-18")


class MatriculaError(ValueError):
    pass


def normaliza(plate: str) -> str:
    return (plate or "").strip().upper().replace("-", " ")


def parse(plate: str) -> tuple[int, str]:
    m = _RE.match(normaliza(plate).replace(" ", ""))
    if not m:
        raise MatriculaError(
            "Formato no válido. Debe ser 4 dígitos + 3 consonantes "
            "(sin vocales, Ñ ni Q), p.ej. 1234 BCD.")
    return int(m.group(1)), m.group(2)


def indice(plate: str) -> int:
    """Posición secuencial absoluta de la matrícula (BBB 0000 = 0)."""
    num, letras = parse(plate)
    suf = _IDX[letras[0]] * 400 + _IDX[letras[1]] * 20 + _IDX[letras[2]]
    return suf * 10000 + num


def _carga_anclas() -> list[tuple[int, datetime.date]]:
    anclas = {_ANCLA_BASE[0]: _ANCLA_BASE[1]}
    extra = os.environ.get("MATRICULA_ANCHORS")
    if extra and os.path.exists(extra):
        with open(extra, encoding="utf-8") as fh:
            anclas.update(json.load(fh))  # {"1234BCD": "2003-05-01", ...}
    out = []
    for plate, fecha in anclas.items():
        try:
            out.append((indice(plate), datetime.date.fromisoformat(fecha)))
        except (MatriculaError, ValueError):
            continue
    out.sort()
    return out


def estimar_fecha(plate: str,
                  anclas_extra: dict[str, str] | None = None) -> datetime.date:
    """Estima la fecha de matriculación interpolando entre anclas.

    `anclas_extra`: {matrícula: 'AAAA-MM-DD'} que el usuario conozca.
    Lanza MatriculaError si no hay al menos 2 anclas para interpolar.
    """
    objetivo = indice(plate)
    anclas = _carga_anclas()
    for p, f in (anclas_extra or {}).items():
        try:
            anclas.append((indice(p), datetime.date.fromisoformat(f)))
        except (MatriculaError, ValueError):
            continue
    anclas = sorted(set(anclas))
    if len(anclas) < 2:
        raise MatriculaError(
            "Necesito al menos 2 anclas para estimar. Añade una matrícula "
            "reciente que conozcas con su fecha (o configura MATRICULA_ANCHORS).")

    # Elige las dos anclas que rodean al objetivo (o las dos extremas para
    # extrapolar) y haz interpolación lineal sobre el índice.
    lo = hi = None
    for a in anclas:
        if a[0] <= objetivo:
            lo = a
        if a[0] >= objetivo and hi is None:
            hi = a
    if lo is None:
        lo, hi = anclas[0], anclas[1]
    elif hi is None:
        lo, hi = anclas[-2], anclas[-1]
    if lo[0] == hi[0]:
        return lo[1]

    frac = (objetivo - lo[0]) / (hi[0] - lo[0])
    dias = (hi[1] - lo[1]).days
    est = lo[1] + datetime.timedelta(days=round(frac * dias))
    # Cordura: no antes de la 1ª matrícula del sistema ni en el futuro. Una
    # estimación que se sale de rango suele indicar anclas poco representativas.
    minimo = datetime.date(2000, 9, 18)
    hoy = datetime.date.today()
    return min(max(est, minimo), hoy)
