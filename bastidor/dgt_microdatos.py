"""Motor de historial de vehículo a partir de los Microdatos MATRABA de la DGT.

ESTE es el "secreto" de webs como seisenlinea: la DGT publica gratis, en
"DGT en Cifras → Microdatos", ficheros de texto de ANCHO FIJO con:

  - Matriculaciones  (altas)
  - Transferencias   (cambios de titular)
  - Bajas            (desguace / exportación / temporal)

Cada registro trae bastidor*, marca, modelo, fecha, provincia, código postal,
tipo de titular (persona física/jurídica) y las letras de la matrícula. NO trae
nombres ni DNI -> datos anónimos. Encadenando por bastidor la matriculación +
las transferencias ordenadas por fecha se reconstruye el historial completo de
propietarios.

(*) Desde el 01/02/2025 la DGT dejó de incluir el bastidor completo en los
ficheros abiertos. Funciona con datos históricos (hasta ene-2025).

------------------------------------------------------------------------------
EL PROBLEMA DE LOS OFFSETS  ->  SOLUCIÓN: SNIFFER AUTOMÁTICO
------------------------------------------------------------------------------
El formato es de ancho fijo y las posiciones han cambiado a lo largo de los
años. En vez de depender del PDF de diseño de registro, este módulo DETECTA
automáticamente la columna del bastidor (busca tokens de 17 chars con forma de
VIN) y la de la fecha (8 dígitos AAAAMMDD plausibles) analizando una muestra del
fichero. Para provincia / tipo de persona puedes dar offsets opcionales.

------------------------------------------------------------------------------
USO
------------------------------------------------------------------------------
    python dgt_microdatos.py sniff   export_2023.txt          # ver columnas
    python dgt_microdatos.py ingest  export_*.txt             # cargar a SQLite
    python dgt_microdatos.py buscar  WBABT31023JP07303         # consultar
    python dgt_microdatos.py stats                             # qué hay cargado
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import sqlite3
import sys

from vin import is_vin

DB_PATH = os.environ.get("DGT_DB", os.path.join(os.path.dirname(__file__), "dgt.db"))

# Offsets opcionales para campos que el sniffer no infiere solo.
# Se pueden fijar con un fichero JSON (DGT_LAYOUT=ruta.json), p.ej.:
#   {"cod_provincia": [100,102], "tipo_persona": [112,113]}
_VIN_TOKEN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
_RUN = re.compile(r"(.)\1{5,}")  # 6+ veces el mismo carácter seguido
_TIPO_PERSONA = {"D": "particular", "F": "particular", "X": "empresa",
                 "J": "empresa", "E": "empresa"}


def _plausible_vin(tok: str) -> bool:
    """Filtro anti-falsos-positivos: un VIN real mezcla letras y dígitos y no
    tiene tiradas largas del mismo carácter (descarta rellenos tipo 'XXXX' o
    fechas+relleno '20100312XXXXXXXXX')."""
    tok = tok.upper()
    if not _VIN_TOKEN.match(tok):
        return False
    letters = sum(c.isalpha() for c in tok)
    digits = sum(c.isdigit() for c in tok)
    if letters < 2 or digits < 1:
        return False
    if len(set(tok)) < 6:
        return False
    if _RUN.search(tok):
        return False
    return True


def _load_extra_layout() -> dict:
    path = os.environ.get("DGT_LAYOUT")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return {k: tuple(v) for k, v in json.load(fh).items()}
    return {}


# ---------------------------------------------------------------------------
# Sniffer: detecta las columnas de bastidor y fecha analizando una muestra
# ---------------------------------------------------------------------------
def _sample_lines(path: str, n: int = 3000) -> list[str]:
    out = []
    with open(path, "r", encoding="latin-1", errors="replace") as fh:
        for i, line in enumerate(fh):
            line = line.rstrip("\n\r")
            if line.strip():
                out.append(line)
            if len(out) >= n:
                break
    return out


def _find_vin_column(lines: list[str]) -> tuple[int, int] | None:
    """Busca la posición de inicio donde, de forma consistente, hay un VIN."""
    if not lines:
        return None
    width = max(len(l) for l in lines)
    best, best_hits = None, 0
    for start in range(0, max(1, width - 16)):
        hits = 0
        checked = 0
        for l in lines:
            tok = l[start:start + 17]
            if len(tok) < 17:
                continue
            checked += 1
            if _plausible_vin(tok):
                hits += 1
        if checked and hits / checked > 0.6 and hits > best_hits:
            best, best_hits = (start, start + 17), hits
    return best


def _looks_like_date(tok: str) -> bool:
    if len(tok) != 8 or not tok.isdigit():
        return False
    y, m, d = int(tok[:4]), int(tok[4:6]), int(tok[6:8])
    return 1950 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31


def _find_date_column(lines: list[str]) -> tuple[int, int] | None:
    if not lines:
        return None
    width = max(len(l) for l in lines)
    best, best_hits = None, 0
    for start in range(0, max(1, width - 7)):
        hits = checked = 0
        for l in lines:
            tok = l[start:start + 8]
            if len(tok) < 8:
                continue
            checked += 1
            if _looks_like_date(tok):
                hits += 1
        if checked and hits / checked > 0.8 and hits > best_hits:
            best, best_hits = (start, start + 8), hits
    return best


def sniff_layout(path: str) -> dict:
    """Devuelve {'bastidor': (a,b), 'fecha': (a,b)} detectados + extras JSON."""
    lines = _sample_lines(path)
    layout = {}
    vin_col = _find_vin_column(lines)
    if vin_col:
        layout["bastidor"] = vin_col
    date_col = _find_date_column(lines)
    if date_col:
        layout["fecha"] = date_col
    layout.update(_load_extra_layout())
    return layout


def _slice(line: str, span) -> str:
    return line[span[0]:span[1]].strip()


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def _connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS eventos (
            bastidor   TEXT NOT NULL,
            tipo       TEXT NOT NULL,
            fecha      TEXT,
            provincia  TEXT,
            tipo_persona TEXT,
            origen     TEXT
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_bastidor ON eventos(bastidor)")
    # Evita duplicar al re-ingerir el mismo fichero
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_uniq "
        "ON eventos(bastidor, tipo, fecha, origen)"
    )
    return con


def _parse_fecha(tok: str) -> str | None:
    tok = (tok or "").strip()
    if _looks_like_date(tok):
        return f"{tok[:4]}-{tok[4:6]}-{tok[6:8]}"
    return None


def ingest_file(path: str, tipo: str, con: sqlite3.Connection,
                layout: dict | None = None) -> tuple[int, int]:
    """Ingiere un fichero. Devuelve (insertados, lineas_sin_bastidor)."""
    layout = layout or sniff_layout(path)
    if "bastidor" not in layout:
        return 0, 0  # fichero sin bastidor (>= feb-2025) o no detectado
    bcol = layout["bastidor"]
    fcol = layout.get("fecha")
    pcol = layout.get("cod_provincia")
    tcol = layout.get("tipo_persona")
    ins = skip = 0
    rows = []
    with open(path, "r", encoding="latin-1", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            bastidor = _slice(line, bcol).upper()
            if not _plausible_vin(bastidor):
                skip += 1
                continue
            fecha = _parse_fecha(_slice(line, fcol)) if fcol else None
            prov = _slice(line, pcol) if pcol else None
            tp = _TIPO_PERSONA.get(_slice(line, tcol).upper(), None) if tcol else None
            rows.append((bastidor, tipo, fecha, prov, tp, os.path.basename(path)))
    for r in rows:
        try:
            con.execute("INSERT INTO eventos VALUES (?,?,?,?,?,?)", r)
            ins += 1
        except sqlite3.IntegrityError:
            pass  # duplicado
    con.commit()
    return ins, skip


def _months_between(d1: str, d2: str | None) -> int | None:
    try:
        a = datetime.date.fromisoformat(d1)
    except (ValueError, TypeError):
        return None
    b = datetime.date.fromisoformat(d2) if d2 else datetime.date.today()
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def historial(bastidor: str, db_path: str = DB_PATH) -> dict | None:
    bastidor = bastidor.strip().upper()
    if not os.path.exists(db_path):
        return None
    con = _connect(db_path)
    rows = con.execute(
        "SELECT tipo, fecha, provincia, tipo_persona FROM eventos "
        "WHERE bastidor=? ORDER BY fecha", (bastidor,),
    ).fetchall()
    con.close()
    if not rows:
        return None
    eventos = [{"tipo": r[0], "fecha": r[1], "provincia": r[2],
                "tipo_persona": r[3]} for r in rows]
    tramos = []
    for i, ev in enumerate(eventos):
        fin = eventos[i + 1]["fecha"] if i + 1 < len(eventos) else None
        tramos.append({
            "desde": ev["fecha"], "hasta": fin,
            "meses": _months_between(ev["fecha"], fin),
            "provincia": ev["provincia"], "tipo_persona": ev["tipo_persona"],
            "evento": ev["tipo"],
        })
    return {"bastidor": bastidor, "num_propietarios": len(tramos), "tramos": tramos}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _tipo_from_name(fname: str) -> str:
    f = fname.lower()
    return ("transferencia" if "transf" in f
            else "baja" if "baja" in f else "matricula")


def _cli():
    args = sys.argv[1:]
    if args and args[0] == "sniff" and len(args) == 2:
        lay = sniff_layout(args[1])
        print(json.dumps(lay, indent=2, ensure_ascii=False))
        if "bastidor" not in lay:
            print("⚠️  No se detectó columna de bastidor (¿fichero >= feb-2025?).")
    elif args and args[0] == "ingest" and len(args) >= 2:
        con = _connect()
        tot_ins = tot_skip = 0
        for pat in args[1:]:
            for path in glob.glob(pat):
                tipo = _tipo_from_name(os.path.basename(path))
                ins, skip = ingest_file(path, tipo, con)
                print(f"  {path} [{tipo}] -> {ins} insertados, {skip} sin VIN")
                tot_ins += ins
                tot_skip += skip
        con.close()
        print(f"Total: {tot_ins} eventos cargados ({tot_skip} líneas sin VIN).")
    elif args and args[0] == "buscar" and len(args) == 2:
        print(json.dumps(historial(args[1]), indent=2, ensure_ascii=False))
    elif args and args[0] == "stats":
        if not os.path.exists(DB_PATH):
            print("No hay base de datos todavía.")
            return
        con = _connect()
        n = con.execute("SELECT COUNT(*) FROM eventos").fetchone()[0]
        nb = con.execute("SELECT COUNT(DISTINCT bastidor) FROM eventos").fetchone()[0]
        por_tipo = con.execute(
            "SELECT tipo, COUNT(*) FROM eventos GROUP BY tipo").fetchall()
        con.close()
        print(f"Eventos: {n} | Bastidores únicos: {nb}")
        for t, c in por_tipo:
            print(f"  {t}: {c}")
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
