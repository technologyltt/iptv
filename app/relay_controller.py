"""GPIO relay controller. Uses RPi.GPIO when present; otherwise a stub for dev."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

log = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO  # type: ignore
    _HAS_GPIO = True
except Exception:
    _HAS_GPIO = False
    log.warning("RPi.GPIO not available — relay controller running in STUB mode")


@dataclass
class Relay:
    id: int
    gpio: int
    name: str
    active_low: bool
    state: bool = False


class RelayController:
    def __init__(self, relay_cfg: list[dict]):
        self.relays: dict[int, Relay] = {}
        self._lock = threading.Lock()
        for r in relay_cfg:
            self.relays[r["id"]] = Relay(
                id=r["id"], gpio=r["gpio"], name=r["name"],
                active_low=r.get("active_low", True), state=False,
            )
        if _HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for r in self.relays.values():
                GPIO.setup(r.gpio, GPIO.OUT)
                self._write(r, r.state)

    def _write(self, r: Relay, state: bool) -> None:
        if not _HAS_GPIO:
            return
        level = (not state) if r.active_low else state
        GPIO.output(r.gpio, GPIO.HIGH if level else GPIO.LOW)

    def set(self, rid: int, state: bool) -> Relay:
        with self._lock:
            r = self.relays[rid]
            r.state = bool(state)
            self._write(r, r.state)
            log.info("relay %s (%s) -> %s", rid, r.name, r.state)
            return r

    def toggle(self, rid: int) -> Relay:
        return self.set(rid, not self.relays[rid].state)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [
                {"id": r.id, "gpio": r.gpio, "name": r.name, "state": r.state}
                for r in self.relays.values()
            ]

    def cleanup(self) -> None:
        if _HAS_GPIO:
            GPIO.cleanup()
