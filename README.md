# VTG Bypass Toolkit · Audi A6 C6 2.7 TDI (EDC17CP14)

Un relé corta el +12 V del actuador VTG antes de arrancar → el coche arranca
con los álabes en posición failsafe → sonido. Botón en el móvil "ACTIVAR
TURBO" → la Raspberry devuelve corriente al actuador y borra los DTCs VTG
automáticamente por ELM327 Bluetooth.

> **Sin reflash de ECU. Sin tocar mapas.** Un relé, una Pi, un ELM327 BT.

## Funcionamiento

```
   Móvil ◄──WiFi/hotspot──► Raspberry Pi Zero 2 W
                              │            │
                              │            └── BT ──► ELM327 ──► OBD-II
                              │                                  (lectura
                              │                                   + clear DTC)
                              │
                              └── GPIO 5 ──► Módulo relé 1ch 5V
                                                │
                                                ├── COM ◄── +12V mazo coche
                                                └── NO  ──► +12V actuador VTG
```

## Antes de comprar nada

⚠️ Lee `docs/01_concepto_vtg_bypass.md` sección **1.2** — hay un test de
30 segundos que te dice si tu actuador concreto falla en abierto (mod
funciona) o en cerrado (mod no aplica).

## Estructura

```
docs/
  01_concepto_vtg_bypass.md   # Cómo funciona, qué cable cortar, riesgos
  02_hardware.md              # Lista de compra exacta (~100 €)
  03_uso.md                   # Flujo diario, qué hacer si X
  04_instalacion.md           # Pi OS, pairing BT, systemd
app/
  obd_manager.py              # ELM327: lectura + clear DTCs
  turbo_relay.py              # Lógica bypass/engage + secuencia de clear
  relay_controller.py         # GPIO
  web_server.py               # Flask + SocketIO
  templates/index.html        # UI móvil: 2 botones grandes + DTCs + tele
  static/{app.css, app.js}
  config.yaml
systemd/edc17-vtg.service
scripts/
  install.sh
  test_relay.py               # Test del relé en banco
```

## Lista de compra resumida (~100 €)

1. Raspberry Pi Zero 2 W — 22 €
2. microSD Industrial 16 GB — 10 €
3. vGate iCar Pro BLE 4.0 (ELM327 Bluetooth) — 25 €
4. Buck DC-DC 12→5V automotive — 12 €
5. Módulo relé 1 ch 5V opto — 5 €
6. Pigtail conector VTG + cables + fusible + caja — 25 €

Detalle en `docs/02_hardware.md`.

## Uso en 4 pasos

1. Subes al coche. Pi arranca con contacto.
2. App en móvil → `CORTAR (sonido)` → arrancas → suena grave.
3. Cuando quieras conducir normal → `ACTIVAR TURBO` → ya.
4. Antes de ITV: desconecta el pigtail, deja el cable original como estaba.
