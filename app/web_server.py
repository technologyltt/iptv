"""Flask + SocketIO web server. Mobile-first UI."""
from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from obd_manager import OBDManager
from relay_controller import RelayController
from sound_controller import Mode, SoundCfg, SoundController

ROOT = Path(__file__).parent
log = logging.getLogger(__name__)


def load_cfg() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def create_app():
    cfg = load_cfg()
    logging.basicConfig(
        level=getattr(logging, cfg["logging"].get("level", "INFO")),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    log_dir = Path(cfg["logging"]["dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, template_folder=str(ROOT / "templates"),
                static_folder=str(ROOT / "static"))
    app.config["SECRET_KEY"] = "edc17-vtg-local"
    sio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    obd_mgr = OBDManager(cfg, clear_log_path=log_dir / "clear.log")
    relays = RelayController(cfg["relays"])
    sound_cfg = SoundCfg(**cfg["sound"])
    sound = SoundController(sound_cfg, obd_mgr, relays)
    try:
        sound.set_mode(cfg["sound"].get("mode", "auto"))
    except ValueError:
        pass

    obd_mgr.start()
    sound.start()

    def status_payload() -> dict:
        s = obd_mgr.get_snapshot()
        return {
            "connected": s.connected,
            "ts": s.ts,
            "rpm": s.rpm, "speed_kmh": s.speed_kmh,
            "coolant_c": s.coolant_c, "intake_c": s.intake_c,
            "maf_gs": s.maf_gs, "map_kpa": s.map_kpa, "boost_bar": s.boost_bar,
            "throttle_pct": s.throttle_pct, "pedal_pct": s.pedal_pct,
            "fuel_rate_lh": s.fuel_rate_lh,
            "dtcs": s.dtcs,
            "auto_clear": obd_mgr.auto_clear,
            "relays": relays.snapshot(),
            "sound": sound.snapshot(),
        }

    # ---------------- HTTP ----------------

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            relays=relays.snapshot(),
            modes=[m.value for m in Mode],
        )

    @app.route("/api/status")
    def api_status():
        return jsonify(status_payload())

    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        res = obd_mgr.manual_clear(user=request.remote_addr or "unknown")
        return jsonify(res)

    @app.route("/api/auto_clear", methods=["POST"])
    def api_auto_clear():
        data = request.get_json(force=True, silent=True) or {}
        enabled = bool(data.get("enabled"))
        obd_mgr.set_auto_clear(enabled)
        return jsonify({"ok": True, "auto_clear": enabled})

    @app.route("/api/relay/<int:rid>", methods=["POST"])
    def api_relay(rid: int):
        data = request.get_json(force=True, silent=True) or {}
        if "state" in data:
            r = relays.set(rid, bool(data["state"]))
        else:
            r = relays.toggle(rid)
        return jsonify({"ok": True, "id": r.id, "state": r.state})

    @app.route("/api/sound/mode", methods=["POST"])
    def api_sound_mode():
        data = request.get_json(force=True, silent=True) or {}
        try:
            m = sound.set_mode(data.get("mode", "auto"))
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        return jsonify({"ok": True, "mode": m})

    # ---------------- broadcaster ----------------

    def broadcaster():
        interval = cfg["web"].get("poll_interval_s", 0.5)
        while True:
            try:
                sio.emit("status", status_payload())
            except Exception:
                log.exception("broadcaster error")
            time.sleep(interval)

    threading.Thread(target=broadcaster, daemon=True, name="ws-broadcast").start()

    def _shutdown(*_):
        log.info("Shutting down…")
        sound.stop()
        obd_mgr.stop()
        relays.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    return app, sio, cfg


if __name__ == "__main__":
    app, sio, cfg = create_app()
    sio.run(app, host=cfg["web"]["host"], port=cfg["web"]["port"], debug=False)
