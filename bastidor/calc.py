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
