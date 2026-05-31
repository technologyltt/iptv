"""Motor de historial de vehículo a partir de los Microdatos MATRABA de la DGT.

ESTE es el "secreto" de webs como seisenlinea: la DGT publica gratis, en
"DGT en Cifras → Microdatos", ficheros de texto de ANCHO FIJO con:

  - Matriculaciones  (altas)
  - Transferencias   (cambios de titular)
  - Bajas            (desguace / exportación / temporal)

Cada registro trae bastidor*, marca, modelo, fecha, provincia/municipio,
código postal, tipo de titular (persona física/jurídica) y las letras de la
matrícula (sin la parte numérica). NO trae nombres ni DNI -> datos anónimos.

Encadenando, por bastidor, la matriculación + todas las transferencias
ordenadas por fecha, se reconstruye:
  · número de propietarios
  · cuánto tiempo tuvo el coche cada uno
  · en qué provincia estaba en cada momento
  · si era particular o empresa

(*) IMPORTANTE: desde el 01/02/2025 la DGT dejó de incluir el bastidor
completo en los ficheros abiertos. Para datos anteriores funciona; para los
nuevos hay que pedir acceso a la DGT acreditando interés legítimo.

------------------------------------------------------------------------------
USO TÍPICO
------------------------------------------------------------------------------
    1. Descargar ficheros mensuales de:
       https://www.dgt.es/.../Microdatos-de-Transferencias-de-Vehiculos-mensual/
    2. Ingerirlos en SQLite:        python dgt_microdatos.py ingest export_*.txt
    3. Consultar un bastidor:       historial("WBABT31023JP07303")

El LAYOUT de ancho fijo (posiciones de cada campo) debe completarse con el
diseño de registro oficial en PDF (TRANSFERENCIAS_MATRABA.pdf /
MATRICULACIONES_MATRABA.pdf). Abajo va una plantilla con los campos clave;
verifica los offsets contra el PDF de tu año (han cambiado con el tiempo).
"""
from __future__ import annotations

import datetime
import glob
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DGT_DB", os.path.join(os.path.dirname(__file__), "dgt.db"))

# ---------------------------------------------------------------------------
# LAYOUT de ancho fijo. (inicio, fin) en base 0, fin exclusivo.
# >>> AJUSTAR a partir del PDF oficial "diseño de registro" de la DGT <<<
# Estos valores son una PLANTILLA orientativa, NO los definitivos.
# ---------------------------------------------------------------------------
LAYOUT_MATRICULACIONES = {
    "fecha_matricula": (0, 8),     # AAAAMMDD
    "marca":           (60, 90),
    "modelo":          (90, 120),
    "cod_provincia":   (120, 122),
    "cod_municipio":   (122, 127),
    "cod_postal":      (127, 132),
    "tipo_persona":    (132, 133),  # 'D' física / 'X' jurídica (ver PDF)
    "bastidor":        (200, 217),  # vacío en ficheros >= feb-2025
    "matricula_letras":(133, 136),
}

LAYOUT_TRANSFERENCIAS = {
    "fecha_tramite":   (0, 8),
    "marca":           (40, 70),
    "modelo":          (70, 100),
    "cod_provincia":   (100, 102),
    "cod_municipio":   (102, 107),
    "cod_postal":      (107, 112),
    "tipo_persona":    (112, 113),
    "bastidor":        (180, 197),
    "matricula_letras":(113, 116),
}


def _slice(line: str, span: tuple[int, int]) -> str:
    return line[span[0]:span[1]].strip()


def _parse_line(line: str, layout: dict) -> dict:
    return {k: _slice(line, span) for k, span in layout.items()}


def _parse_fecha(s: str) -> str | None:
    s = s.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return None


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def _connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS eventos (
            bastidor   TEXT NOT NULL,
            tipo       TEXT NOT NULL,        -- 'matricula' | 'transferencia' | 'baja'
            fecha      TEXT,                 -- ISO AAAA-MM-DD
            marca      TEXT,
            modelo     TEXT,
            provincia  TEXT,
            municipio  TEXT,
            cod_postal TEXT,
            tipo_persona TEXT,               -- particular | empresa
            matricula_letras TEXT
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_bastidor ON eventos(bastidor)")
    return con


def _tipo_persona(code: str) -> str:
    # Según el PDF de la DGT (verificar): física vs jurídica
    return {"D": "particular", "X": "empresa"}.get(code.upper(), code or "?")


def ingest_file(path: str, tipo: str, con: sqlite3.Connection) -> int:
    """Ingiere un fichero MATRABA. tipo: matricula|transferencia|baja."""
    layout = LAYOUT_MATRICULACIONES if tipo == "matricula" else LAYOUT_TRANSFERENCIAS
    n = 0
    with open(path, "r", encoding="latin-1", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = _parse_line(line, layout)
            bastidor = rec.get("bastidor", "").strip().upper()
            if not bastidor:
                continue  # ficheros >= feb-2025 vienen sin bastidor
            con.execute(
                "INSERT INTO eventos VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    bastidor, tipo,
                    _parse_fecha(rec.get("fecha_matricula") or rec.get("fecha_tramite", "")),
                    rec.get("marca"), rec.get("modelo"),
                    rec.get("cod_provincia"), rec.get("cod_municipio"),
                    rec.get("cod_postal"),
                    _tipo_persona(rec.get("tipo_persona", "")),
                    rec.get("matricula_letras"),
                ),
            )
            n += 1
    con.commit()
    return n


def _months_between(d1: str, d2: str | None) -> int | None:
    try:
        a = datetime.date.fromisoformat(d1)
    except (ValueError, TypeError):
        return None
    b = datetime.date.fromisoformat(d2) if d2 else datetime.date.today()
    return (b.year - a.year) * 12 + (b.month - a.month)


def historial(bastidor: str, db_path: str = DB_PATH) -> dict | None:
    """Reconstruye el historial de propietarios de un bastidor.

    Devuelve None si no hay datos (lo normal si aún no has ingerido ficheros).
    """
    bastidor = bastidor.strip().upper()
    if not os.path.exists(db_path):
        return None
    con = _connect(db_path)
    rows = con.execute(
        "SELECT tipo, fecha, marca, modelo, provincia, municipio, "
        "tipo_persona FROM eventos WHERE bastidor=? ORDER BY fecha",
        (bastidor,),
    ).fetchall()
    con.close()
    if not rows:
        return None

    eventos = [
        {
            "tipo": r[0], "fecha": r[1], "marca": r[2], "modelo": r[3],
            "provincia": r[4], "municipio": r[5], "tipo_persona": r[6],
        }
        for r in rows
    ]
    # Tramos de propiedad: cada evento abre un tramo que cierra el siguiente
    tramos = []
    for i, ev in enumerate(eventos):
        fin = eventos[i + 1]["fecha"] if i + 1 < len(eventos) else None
        tramos.append({
            "desde": ev["fecha"],
            "hasta": fin,
            "meses": _months_between(ev["fecha"], fin),
            "provincia": ev["provincia"],
            "tipo_persona": ev["tipo_persona"],
            "evento": ev["tipo"],
        })
    return {
        "bastidor": bastidor,
        "num_propietarios": len(tramos),
        "marca": eventos[0]["marca"],
        "modelo": eventos[0]["modelo"],
        "tramos": tramos,
    }


def _cli():
    if len(sys.argv) >= 3 and sys.argv[1] == "ingest":
        con = _connect()
        total = 0
        for pat in sys.argv[2:]:
            for path in glob.glob(pat):
                fname = os.path.basename(path).lower()
                tipo = ("transferencia" if "transf" in fname
                        else "baja" if "baja" in fname else "matricula")
                n = ingest_file(path, tipo, con)
                print(f"  {path} [{tipo}] -> {n} registros")
                total += n
        con.close()
        print(f"Total ingerido: {total}")
    elif len(sys.argv) == 3 and sys.argv[1] == "buscar":
        import json
        print(json.dumps(historial(sys.argv[2]), indent=2, ensure_ascii=False))
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
