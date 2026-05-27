"""Turbo VTG relay controller.

Lógica:
  BYPASS  → relé OFF → actuador VTG sin +12V → álabes en posición failsafe.
            Solo permitido con motor parado o idle muy estable.
  ENGAGED → relé ON  → actuador VTG con +12V → ECU recupera control.
            Tras 'engage', secuencia de borrado automático de DTCs VTG.

NO se intercepta ni LIN ni feedback. Solo se corta/devuelve el +12V del actuador.
"""
from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)


class State(str, enum.Enum):
    BYPASS = "bypass"      # relé OFF → sin corriente al VTG
    ENGAGED = "engaged"    # relé ON  → ECU controla el VTG


class TurboRelay:
    def __init__(self, cfg: dict, obd_mgr, relays):
        self.cfg = cfg
        self.obd_mgr = obd_mgr
        self.relays = relays
        self.relay_id = int(cfg["relay_id"])
        self.engage_settle_s = float(cfg.get("engage_settle_s", 3.0))
        self.clear_attempts = int(cfg.get("clear_attempts", 6))
        self.clear_interval_s = float(cfg.get("clear_interval_s", 1.5))
        self.vtg_codes = list(cfg.get("vtg_codes", ["P2563", "P0046", "P132B", "P003A"]))
        self.default_state = State(cfg.get("default_state", "engaged"))

        self._state: State = self.default_state
        self._busy = False
        self._last_action: str = "init"
        self._lock = threading.Lock()

        self._apply(self._state, reason="boot")

    # ---------- public ----------

    def snapshot(self) -> dict:
        return {
            "state": self._state.value,
            "busy": self._busy,
            "last_action": self._last_action,
        }

    def bypass(self, user: str = "mobile") -> dict:
        """Corta corriente al actuador VTG. Solo si motor parado o idle estable."""
        if self._busy:
            return {"ok": False, "reason": "busy"}
        s = self.obd_mgr.get_snapshot()
        if s.rpm is not None and s.rpm > 100:
            # Motor encendido — solo permitir si idle estable y velocidad 0
            if s.rpm > 1100 or (s.speed_kmh or 0) > 1 or (s.pedal_pct or 0) > 5:
                return {"ok": False, "reason": "engine_not_idle"}
        return self._do(State.BYPASS, user=user)

    def engage(self, user: str = "mobile") -> dict:
        """Devuelve corriente al actuador VTG y borra DTCs VTG en secuencia."""
        if self._busy:
            return {"ok": False, "reason": "busy"}
        return self._do(State.ENGAGED, user=user)

    # ---------- internals ----------

    def _apply(self, state: State, reason: str) -> None:
        relay_on = (state == State.ENGAGED)
        self.relays.set(self.relay_id, relay_on)
        self._state = state
        self._last_action = f"{state.value} ({reason})"
        log.info("VTG → %s (%s)", state.value, reason)

    def _do(self, target: State, user: str) -> dict:
        with self._lock:
            self._busy = True
        try:
            if target == State.BYPASS:
                self._apply(State.BYPASS, reason=f"manual:{user}")
                return {"ok": True, "state": "bypass"}

            # ENGAGE: relé ON, esperar self-cal del actuador, luego clear DTCs VTG
            self._apply(State.ENGAGED, reason=f"manual:{user}")
            time.sleep(self.engage_settle_s)

            cleared, attempts = self._clear_vtg_codes()
            return {
                "ok": True,
                "state": "engaged",
                "cleared": cleared,
                "attempts": attempts,
            }
        finally:
            with self._lock:
                self._busy = False

    def _clear_vtg_codes(self) -> tuple[list[str], int]:
        """Intenta borrar DTCs VTG hasta clear_attempts veces."""
        cleared: list[str] = []
        for i in range(1, self.clear_attempts + 1):
            present = [c for c, _ in self.obd_mgr.read_dtcs_now()]
            vtg_present = [c for c in present if c in self.vtg_codes]
            if not vtg_present:
                self._last_action = f"engaged + DTCs limpios (intentos {i - 1})"
                return cleared, i - 1
            ok = self.obd_mgr.force_clear(vtg_present)
            if ok:
                cleared.extend(vtg_present)
            time.sleep(self.clear_interval_s)
        # tras los intentos, leer estado final
        final = [c for c, _ in self.obd_mgr.read_dtcs_now()]
        remaining = [c for c in final if c in self.vtg_codes]
        if remaining:
            self._last_action = f"engaged pero DTCs persisten: {remaining}"
        else:
            self._last_action = f"engaged + DTCs limpios"
        return cleared, self.clear_attempts
