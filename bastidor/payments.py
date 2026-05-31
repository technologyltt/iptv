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

import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request

_API = "https://api.stripe.com/v1"
_PAID_DB = os.environ.get("PAID_DB", os.path.join(os.path.dirname(__file__), "paid.db"))


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
    """Comprueba que una sesión de Checkout está pagada (consulta directa)."""
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


# --- Almacén de pagos confirmados (vía webhook) -----------------------------
def _paid_con() -> sqlite3.Connection:
    con = sqlite3.connect(_PAID_DB)
    con.execute("CREATE TABLE IF NOT EXISTS pagado "
                "(vin TEXT PRIMARY KEY, ts INTEGER)")
    return con


def mark_paid(vin: str) -> None:
    con = _paid_con()
    con.execute("INSERT OR REPLACE INTO pagado VALUES (?,?)",
                (vin.strip().upper(), int(time.time())))
    con.commit()
    con.close()


def is_paid(vin: str) -> bool:
    if not os.path.exists(_PAID_DB):
        return False
    con = _paid_con()
    row = con.execute("SELECT 1 FROM pagado WHERE vin=?",
                      (vin.strip().upper(),)).fetchone()
    con.close()
    return row is not None


# --- Verificación de webhook de Stripe (sin dependencias) -------------------
def verify_webhook(payload: bytes, sig_header: str,
                   tolerance: int = 300) -> dict | None:
    """Valida la firma del webhook y devuelve el evento, o None si no es válida.

    Cabecera Stripe-Signature: 't=<ts>,v1=<firma>'. Se firma '<ts>.<payload>'
    con HMAC-SHA256 usando STRIPE_WEBHOOK_SECRET (whsec_...).
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret or not sig_header:
        return None
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts, v1 = parts.get("t"), parts.get("v1")
    if not ts or not v1:
        return None
    if abs(time.time() - int(ts)) > tolerance:
        return None  # protege contra replays
    signed = f"{ts}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, v1):
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return None
