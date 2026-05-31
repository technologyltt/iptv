"""Calculadoras (herramientas tipo seisenlinea).

Potencia fiscal (CVF) — fórmula oficial española (Orden de 16/07/1984):

    CVF = T · (0.785 · D² · R · N)^0.6

  D = diámetro del cilindro (cm)
  R = carrera del pistón (cm)
  N = número de cilindros
  T = 0.08 (motores de 4 tiempos)  /  0.11 (2 tiempos)

El resultado se redondea a 2 decimales (los CVF tributan en el IVTM municipal).
"""
from __future__ import annotations


def potencia_fiscal(diametro_cm: float, carrera_cm: float, cilindros: int,
                    cuatro_tiempos: bool = True) -> float:
    if diametro_cm <= 0 or carrera_cm <= 0 or cilindros <= 0:
        raise ValueError("Diámetro, carrera y cilindros deben ser positivos.")
    t = 0.08 if cuatro_tiempos else 0.11
    cvf = t * (0.785 * diametro_cm ** 2 * carrera_cm * cilindros) ** 0.6
    return round(cvf, 2)


# ---------------------------------------------------------------------------
# Valor fiscal del vehículo (Hacienda) — tabla oficial de depreciación
# (Orden anual de precios medios de venta, BOE). El % se aplica sobre el precio
# medio del modelo a estrenar (lo das tú: viene en el anexo de la propia Orden).
# ---------------------------------------------------------------------------
# (años de uso cumplidos -> porcentaje del valor original)
DEPRECIACION = [
    (1, 100), (2, 84), (3, 67), (4, 56), (5, 47), (6, 39), (7, 34),
    (8, 28), (9, 24), (10, 19), (11, 17), (12, 13),
]  # más de 12 años -> 10 %


def porcentaje_depreciacion(anios_uso: float) -> int:
    """% del valor original según años de uso (tabla oficial de Hacienda)."""
    if anios_uso < 0:
        raise ValueError("Los años de uso no pueden ser negativos.")
    for limite, pct in DEPRECIACION:
        if anios_uso <= limite:
            return pct
    return 10


def valor_fiscal(precio_medio_nuevo: float, anios_uso: float) -> float:
    """Valor a efectos fiscales = precio medio a estrenar × % depreciación."""
    if precio_medio_nuevo < 0:
        raise ValueError("El precio medio no puede ser negativo.")
    return round(precio_medio_nuevo * porcentaje_depreciacion(anios_uso) / 100, 2)


# ---------------------------------------------------------------------------
# Coste de transferencia de un vehículo usado
#   = ITP (tipo % de la CCAA · valor fiscal) + tasa DGT + gestoría (opcional)
# ---------------------------------------------------------------------------
# Tasa DGT por cambio de titularidad (vigente): turismos 55,70 € · ciclomotores
# y otros 27,85 €. Verifica el importe del año en curso.
TASA_DGT_COCHE = 55.70
TASA_DGT_MOTO = 27.85

# Tipo general de ITP por CCAA (ORIENTATIVO: cambia cada año y varias CCAA usan
# tablas de cuota fija para coches viejos/baratos). Verifica el vigente.
ITP_CCAA = {
    "Andalucía": 4.0, "Aragón": 4.0, "Asturias": 4.0, "Baleares": 4.0,
    "Canarias": 5.5, "Cantabria": 8.0, "Castilla-La Mancha": 6.0,
    "Castilla y León": 5.0, "Cataluña": 5.0, "C. Valenciana": 6.0,
    "Extremadura": 6.0, "Galicia": 8.0, "Madrid": 4.0, "Murcia": 8.0,
    "Navarra": 4.0, "País Vasco": 4.0, "La Rioja": 4.0,
}


def coste_transferencia(valor_fiscal_eur: float, tipo_itp_pct: float,
                        es_moto: bool = False, gestoria: float = 0.0) -> dict:
    """Desglosa el coste de una transferencia. Importes en euros."""
    if valor_fiscal_eur < 0 or tipo_itp_pct < 0 or gestoria < 0:
        raise ValueError("Los importes no pueden ser negativos.")
    itp = round(valor_fiscal_eur * tipo_itp_pct / 100, 2)
    tasa = TASA_DGT_MOTO if es_moto else TASA_DGT_COCHE
    total = round(itp + tasa + gestoria, 2)
    return {"itp": itp, "tasa_dgt": tasa, "gestoria": round(gestoria, 2),
            "total": total}

