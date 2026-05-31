"""Pasarela de pago (Stripe Checkout) para el informe completo.

Sin dependencias externas: habla con la API de Stripe por HTTPS. Se activa solo
si defines en el entorno:

    STRIPE_SECRET_KEY     (sk_live_... o sk_test_...)
    INFORME_PRECIO_CENT   (precio en céntimos, p.ej. 1499 = 14,99 €; def. 1499)

El modelo de negocio (igual que seisenlinea & co): cobras al usuario MÁS de lo
que te cuesta el informe del proveedor. El margen es tuyo.

NOTA DE SEGURIDAD: en producción, confirma el pago vía webhook de Stripe
(checkout.session.completed) antes de entregar el informe. Aquí, por
simplicidad, se verifica el estado de la sesión al volver.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
import json

_API = "https://api.stripe.com/v1"


def enabled() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def precio_centimos() -> int:
    try:
        return int(os.environ.get("INFORME_PRECIO_CENT", "1499"))
    except ValueError:
        return 1499


def _post(path: str, params: list[tuple[str, str]]) -> dict:
    key = os.environ["STRIPE_SECRET_KEY"]
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"{_API}{path}", data=data, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def crear_checkout(vin: str, success_url: str, cancel_url: str) -> dict:
    """Crea una sesión de Stripe Checkout. Devuelve {'url':..., 'id':...}."""
    params = [
        ("mode", "payment"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("client_reference_id", vin),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", "eur"),
        ("line_items[0][price_data][unit_amount]", str(precio_centimos())),
        ("line_items[0][price_data][product_data][name]",
         f"Informe completo del vehículo {vin}"),
    ]
    s = _post("/checkout/sessions", params)
    return {"url": s.get("url"), "id": s.get("id")}


def pago_confirmado(session_id: str) -> bool:
    """Comprueba que una sesión de Checkout está pagada."""
    if not enabled() or not session_id:
        return False
    key = os.environ["STRIPE_SECRET_KEY"]
    req = urllib.request.Request(
        f"{_API}/checkout/sessions/{urllib.parse.quote(session_id)}",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            s = json.loads(r.read().decode("utf-8"))
    except Exception:
        return False
    return s.get("payment_status") == "paid"
