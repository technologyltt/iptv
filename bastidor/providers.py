"""Proveedores de datos de PAGO para el 'informe completo'.

Lo gratis (decode VIN + historial de titulares DGT) ya lo cubren vin.py y
dgt_microdatos.py. Lo que NO es gratis —kilómetros, golpes/siniestros, fotos,
pérdida total— sale de agregadores comerciales: carVertical, autoDNA, CarFax…

Aquí va una interfaz genérica + un cliente configurable por variables de
entorno. No incluye claves: tú das de alta tu cuenta y rellenas:

    CARVERTICAL_API_URL   (endpoint del partner/API que contrates)
    CARVERTICAL_API_KEY   (tu clave)

Si no están configuradas, `available()` devuelve False y la web muestra el
producto como "no disponible / configura tu proveedor" en vez de romper.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class HistoryProvider:
    """Interfaz mínima de un proveedor de historial de pago."""

    name = "generic"

    def available(self) -> bool:
        raise NotImplementedError

    def fetch(self, vin: str) -> dict:
        """Devuelve dict con los datos de pago (km, daños, etc.)."""
        raise NotImplementedError


class CarVerticalProvider(HistoryProvider):
    name = "carVertical"

    def __init__(self):
        self.url = os.environ.get("CARVERTICAL_API_URL")
        self.key = os.environ.get("CARVERTICAL_API_KEY")

    def available(self) -> bool:
        return bool(self.url and self.key)

    def fetch(self, vin: str, timeout: float = 15.0) -> dict:
        if not self.available():
            return {"error": "Proveedor no configurado"}
        payload = json.dumps({"vin": vin}).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=payload, method="POST",
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            return {"error": f"No se pudo consultar el proveedor: {e}"}
        return _normalize_carvertical(data)


def _normalize_carvertical(data: dict) -> dict:
    """Adapta la respuesta cruda del proveedor a nuestro esquema de informe.
    Ajusta las claves a las del partner real cuando lo integres."""
    return {
        "kilometros": data.get("mileage") or data.get("odometer"),
        "registros_km": data.get("mileageRecords") or [],
        "danios": data.get("damages") or [],
        "perdida_total": data.get("totalLoss"),
        "robado": data.get("stolen"),
        "fotos": data.get("photos") or [],
        "_raw_keys": list(data.keys()),
    }


def get_provider() -> HistoryProvider:
    """Selecciona el proveedor activo (de momento, carVertical)."""
    return CarVerticalProvider()
