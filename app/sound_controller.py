"""Sound-mode controller: decide cuándo abrir/cerrar la válvula de escape
(o activar el soundbooster) en función de los datos OBD.

No toca la ECU. Solo manda al relé.
"""
from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)


class Mode(str, enum.Enum):
    AUTO = "auto"
    OPEN = "open"
    CLOSED = "closed"
    COLD_ONLY = "cold_only"


@dataclass
class SoundCfg:
    relay_id: int = 1
    rpm_min: int = 600
    rpm_max: int = 1400
    pedal_max_pct: float = 20.0
    boost_max_bar: float = 0.20
    speed_max_kmh: float = 30.0
    cold_below_c: float = 50.0
    warm_above_c: float = 60.0
    hold_open_ms: int = 300
    hold_close_ms: int = 500
    tick_ms: int = 200


class SoundController:
    """Loop que mira el snapshot del OBDManager y mueve un relé con histeresis."""

    def __init__(self, cfg: SoundCfg, obd_mgr, relays):
        self.cfg = cfg
        self.obd_mgr = obd_mgr
        self.relays = relays
        self.mode = Mode.AUTO
        self._open = False
        self._wants_open_since: float | None = None
        self._wants_close_since: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._reason = "init"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="sound")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def set_mode(self, mode: str) -> str:
        try:
            self.mode = Mode(mode)
        except ValueError:
            raise ValueError(f"modo inválido: {mode}")
        log.info("sound mode = %s", self.mode.value)
        return self.mode.value

    def snapshot(self) -> dict:
        return {
            "mode": self.mode.value,
            "open": self._open,
            "reason": self._reason,
        }

    # ---------- internals ----------

    def _conditions_open(self, s) -> tuple[bool, str]:
        c = self.cfg
        if s.rpm is None:
            return False, "no_rpm"
        if not (c.rpm_min <= s.rpm <= c.rpm_max):
            return False, f"rpm_out({s.rpm:.0f})"
        if (s.pedal_pct or 0) > c.pedal_max_pct:
            return False, f"pedal_high({s.pedal_pct:.0f}%)"
        if s.boost_bar is not None and s.boost_bar > c.boost_max_bar:
            return False, f"boost_high({s.boost_bar:.2f})"
        if (s.speed_kmh or 0) > c.speed_max_kmh:
            return False, f"speed_high({s.speed_kmh:.0f})"
        return True, "ok"

    def _decide(self) -> tuple[bool, str]:
        s = self.obd_mgr.get_snapshot()
        if self.mode == Mode.OPEN:
            return True, "forced_open"
        if self.mode == Mode.CLOSED:
            return False, "forced_closed"
        if self.mode == Mode.COLD_ONLY:
            if s.coolant_c is not None and s.coolant_c < self.cfg.cold_below_c:
                return True, f"cold({s.coolant_c:.0f}C)"
            return False, "warm"
        # AUTO
        if s.coolant_c is not None and s.coolant_c < self.cfg.cold_below_c:
            return True, f"cold_start({s.coolant_c:.0f}C)"
        return self._conditions_open(s)

    def _run(self) -> None:
        cfg = self.cfg
        while not self._stop.is_set():
            try:
                want_open, reason = self._decide()
                now = time.time()

                if want_open and not self._open:
                    self._wants_close_since = None
                    self._wants_open_since = self._wants_open_since or now
                    if (now - self._wants_open_since) * 1000 >= cfg.hold_open_ms:
                        self.relays.set(cfg.relay_id, True)
                        self._open = True
                        self._reason = reason
                        log.info("sound OPEN (%s)", reason)
                elif (not want_open) and self._open:
                    self._wants_open_since = None
                    self._wants_close_since = self._wants_close_since or now
                    if (now - self._wants_close_since) * 1000 >= cfg.hold_close_ms:
                        self.relays.set(cfg.relay_id, False)
                        self._open = False
                        self._reason = reason
                        log.info("sound CLOSE (%s)", reason)
                else:
                    self._wants_open_since = None
                    self._wants_close_since = None
                    self._reason = reason
            except Exception:
                log.exception("sound loop error")
            time.sleep(cfg.tick_ms / 1000.0)
