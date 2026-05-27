"""ELM327 manager: live PIDs, DTC read, selective DTC clear with preconditions."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import obd

log = logging.getLogger(__name__)


@dataclass
class LiveData:
    rpm: Optional[float] = None
    speed_kmh: Optional[float] = None
    coolant_c: Optional[float] = None
    intake_c: Optional[float] = None
    maf_gs: Optional[float] = None
    map_kpa: Optional[float] = None
    boost_bar: Optional[float] = None
    throttle_pct: Optional[float] = None
    pedal_pct: Optional[float] = None
    fuel_rate_lh: Optional[float] = None
    dtcs: list[tuple[str, str]] = field(default_factory=list)
    ts: float = 0.0
    connected: bool = False


class OBDManager:
    """Background thread that polls the ELM and exposes the latest snapshot."""

    def __init__(self, cfg: dict, clear_log_path: Path):
        self.cfg = cfg
        self.obd_cfg = cfg["obd"]
        self.dtc_cfg = cfg["dtc"]
        self.snapshot = LiveData()
        self._conn: Optional[obd.OBD] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_clear_ts = 0.0
        self._idle_since: Optional[float] = None
        self.auto_clear = bool(self.dtc_cfg.get("auto_clear_enabled", False))
        self.clear_log_path = clear_log_path
        self.clear_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- lifecycle ----------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="obd-poll")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._conn:
            self._conn.close()

    # ---------- public API ----------

    def get_snapshot(self) -> LiveData:
        with self._lock:
            return LiveData(**{k: getattr(self.snapshot, k) for k in self.snapshot.__dataclass_fields__})

    def set_auto_clear(self, enabled: bool) -> None:
        self.auto_clear = enabled
        log.info("auto_clear=%s", enabled)

    def manual_clear(self, user: str = "mobile") -> dict:
        """Triggered by the user. Same safety pipeline as automatic, but logs trigger=manual."""
        return self._maybe_clear(trigger="manual", user=user, force_no_rate_limit=True)

    # ---------- internals ----------

    def _connect(self) -> bool:
        try:
            self._conn = obd.OBD(
                portstr=self.obd_cfg.get("port"),
                baudrate=self.obd_cfg.get("baudrate"),
                timeout=self.obd_cfg.get("timeout", 2.0),
                fast=self.obd_cfg.get("fast", False),
            )
            ok = self._conn.is_connected()
            with self._lock:
                self.snapshot.connected = ok
            if ok:
                log.info("OBD connected on %s", self.obd_cfg.get("port"))
            else:
                log.warning("OBD not connected")
            return ok
        except Exception as e:
            log.exception("OBD connect failed: %s", e)
            return False

    def _query(self, cmd) -> Optional[float]:
        if not self._conn or not self._conn.is_connected():
            return None
        try:
            r = self._conn.query(cmd, force=True)
            if r.is_null():
                return None
            v = r.value
            return float(v.magnitude) if hasattr(v, "magnitude") else float(v)
        except Exception:
            return None

    def _read_dtcs(self) -> list[tuple[str, str]]:
        if not self._conn or not self._conn.is_connected():
            return []
        try:
            r = self._conn.query(obd.commands.GET_DTC, force=True)
            if r.is_null() or not r.value:
                return []
            return [(code, desc) for code, desc in r.value]
        except Exception:
            return []

    def _preconditions_met(self, snap: LiveData) -> tuple[bool, str]:
        p = self.dtc_cfg["precondition"]
        # Engine off counts as OK (no harm clearing while engine off)
        if snap.rpm is None or snap.rpm < 50:
            return True, "engine_off"
        if snap.rpm > p["max_rpm"]:
            return False, f"rpm_too_high({snap.rpm:.0f}>{p['max_rpm']})"
        if snap.speed_kmh is not None and snap.speed_kmh > p["max_speed_kmh"]:
            return False, f"speed>0({snap.speed_kmh:.1f})"
        if snap.pedal_pct is not None and snap.pedal_pct > p["max_pedal_pct"]:
            return False, f"pedal_too_high({snap.pedal_pct:.1f}%)"
        if self._idle_since is None:
            return False, "idle_window_starting"
        if time.time() - self._idle_since < p["stable_window_s"]:
            return False, f"idle_window_{time.time() - self._idle_since:.1f}s"
        return True, "ok"

    def _filter_clearable(self, dtcs: list[tuple[str, str]]) -> list[tuple[str, str]]:
        wl = set(self.dtc_cfg.get("clearable_codes") or [])
        bl = set(self.dtc_cfg.get("blacklist_codes") or [])
        out = []
        for code, desc in dtcs:
            if code in bl:
                continue
            if code in wl:
                out.append((code, desc))
        return out

    def _has_critical(self, dtcs: list[tuple[str, str]]) -> bool:
        bl = set(self.dtc_cfg.get("blacklist_codes") or [])
        for code, _ in dtcs:
            if code in bl or code.startswith("U") or code.startswith("B"):
                return True
        return False

    def _maybe_clear(self, trigger: str, user: str = "auto",
                     force_no_rate_limit: bool = False) -> dict:
        now = time.time()
        if not force_no_rate_limit:
            if now - self._last_clear_ts < self.dtc_cfg["auto_clear_interval_s"]:
                return {"ok": False, "reason": "rate_limited"}

        snap = self.get_snapshot()
        ok, reason = self._preconditions_met(snap)
        if not ok:
            self._append_log(f"SKIP reason={reason} trigger={trigger}")
            return {"ok": False, "reason": reason}

        dtcs = self._read_dtcs()
        if self._has_critical(dtcs):
            self._append_log(
                f"SKIP reason=critical_dtc_present codes={[c for c,_ in dtcs]} trigger={trigger}"
            )
            return {"ok": False, "reason": "critical_dtc_present", "dtcs": dtcs}

        clearable = self._filter_clearable(dtcs)
        if not clearable:
            return {"ok": True, "cleared": [], "reason": "nothing_in_whitelist"}

        try:
            self._conn.query(obd.commands.CLEAR_DTC, force=True)
            self._last_clear_ts = now
            codes = [c for c, _ in clearable]
            self._append_log(
                f"CLEAR codes={codes} precond_ok=True trigger={trigger} user={user}"
            )
            return {"ok": True, "cleared": codes}
        except Exception as e:
            log.exception("Clear failed")
            return {"ok": False, "reason": f"exception:{e}"}

    def _append_log(self, line: str) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.clear_log_path, "a") as f:
            f.write(f"{ts} {line}\n")

    def _run(self) -> None:
        c = obd.commands
        backoff = 2.0
        while not self._stop.is_set():
            if not self._conn or not self._conn.is_connected():
                if not self._connect():
                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, 30.0)
                    continue
                backoff = 2.0

            snap = LiveData()
            snap.rpm = self._query(c.RPM)
            snap.speed_kmh = self._query(c.SPEED)
            snap.coolant_c = self._query(c.COOLANT_TEMP)
            snap.intake_c = self._query(c.INTAKE_TEMP)
            snap.maf_gs = self._query(c.MAF)
            snap.map_kpa = self._query(c.INTAKE_PRESSURE)
            snap.boost_bar = (snap.map_kpa / 100.0 - 1.013) if snap.map_kpa else None
            snap.throttle_pct = self._query(c.THROTTLE_POS)
            snap.pedal_pct = self._query(c.ACCELERATOR_POS_D) or self._query(c.ACCELERATOR_POS_E)
            snap.fuel_rate_lh = self._query(c.FUEL_RATE)
            snap.dtcs = self._read_dtcs()
            snap.ts = time.time()
            snap.connected = True

            # Idle window tracking
            if snap.rpm is not None and snap.rpm < self.dtc_cfg["precondition"]["max_rpm"] \
                    and (snap.pedal_pct or 0) < self.dtc_cfg["precondition"]["max_pedal_pct"]:
                if self._idle_since is None:
                    self._idle_since = time.time()
            else:
                self._idle_since = None

            with self._lock:
                self.snapshot = snap

            if self.auto_clear:
                self._maybe_clear(trigger="auto")

            time.sleep(self.cfg["web"]["poll_interval_s"])
