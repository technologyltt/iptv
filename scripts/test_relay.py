#!/usr/bin/env python3
"""Prueba rápida del módulo de relé conectado a la Pi.

Conexión:
  Pi pin 2  (5V)   → VCC del módulo
  Pi pin 6  (GND)  → GND del módulo
  Pi pin 29 (BCM5) → IN1 del módulo
  Pi pin 31 (BCM6) → IN2 del módulo
  Pi pin 33 (BCM13)→ IN3
  Pi pin 35 (BCM19)→ IN4

Uso:
  sudo python3 test_relay.py            # ciclo a todos los relés
  sudo python3 test_relay.py 1          # solo relé 1
  sudo python3 test_relay.py 1 on       # solo relé 1, deja ON y sale
"""
import sys
import time

import RPi.GPIO as GPIO  # type: ignore

# BCM pins, active LOW (módulo típico)
RELAYS = {1: 5, 2: 6, 3: 13, 4: 19}
ACTIVE_LOW = True


def set_relay(rid: int, state: bool) -> None:
    pin = RELAYS[rid]
    level = (not state) if ACTIVE_LOW else state
    GPIO.output(pin, GPIO.HIGH if level else GPIO.LOW)


def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in RELAYS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)  # OFF

    args = sys.argv[1:]
    try:
        if not args:
            print("Ciclo a todos los relés (3 s cada uno)…")
            for rid in RELAYS:
                print(f"  Relé {rid} ON  → click")
                set_relay(rid, True)
                time.sleep(3)
                print(f"  Relé {rid} OFF")
                set_relay(rid, False)
                time.sleep(0.5)
        else:
            rid = int(args[0])
            state = args[1].lower() in ("on", "1", "true") if len(args) > 1 else None
            if state is None:
                print(f"Relé {rid} ON 3s → OFF")
                set_relay(rid, True); time.sleep(3); set_relay(rid, False)
            else:
                set_relay(rid, state)
                print(f"Relé {rid} = {'ON' if state else 'OFF'} (sale sin cleanup)")
                return  # no GPIO.cleanup → mantiene el estado
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
