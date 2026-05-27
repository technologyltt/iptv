# Audi A6 C6 2.7 TDI · Sound Control toolkit
**EDC17CP14 — sin reflash de ECU**

Toolkit para conseguir un sonido grave a bajas RPM en el Audi 2.7 TDI **sin
tocar el software de la ECU**, controlando una válvula de bypass de escape (o
un soundbooster activo) desde una Raspberry Pi con telemetría OBD y UI móvil.

> No se modifican mapas. No se intercepta el actuador VTG. Cero riesgo de
> P2563/limp por la modificación. La válvula va aguas abajo del DPF, fuera de
> cualquier lazo de control de la ECU.

## Qué hace

1. La Pi lee por OBD-II (ELM327): RPM, MAF, MAP/boost, ECT, pedal, velocidad, DTCs.
2. Decide cuándo abrir la válvula de escape (relé 1) — modo AUTO con histeresis:
   - **Abre** en 600–1400 rpm con pedal ≤ 20 % y boost ≤ 0.2 bar (idle, marcha lenta, frío).
   - **Cierra** automáticamente en autopista o bajo carga.
   - Modos manuales: AUTO / OPEN / CLOSED / COLD_ONLY.
3. Sirve dashboard móvil (Flask + WebSocket) con telemetría, control y borrado de DTC.
4. Borrado **selectivo** de DTCs con whitelist + pre-condiciones (no enmascarar fallos reales).

## Estructura

```
docs/
  01_concepto_sonido_externo.md   # Por qué este enfoque y cómo funciona
  02_hardware.md                   # Lista de compra y cableado
  03_seguridad_dtc.md              # Estrategia de borrado seguro
  04_instalacion.md                # Pasos en la Raspberry
app/
  obd_manager.py                   # ELM327: PIDs, DTCs, borrado con guards
  sound_controller.py              # Lógica AUTO/manual de apertura válvula
  relay_controller.py              # GPIO de los relés
  web_server.py                    # Flask + SocketIO
  config.yaml                      # Toda la configuración
  templates/index.html             # UI móvil
  static/{app.css, app.js}
systemd/edc17-vtg.service
scripts/install.sh
```

## Empieza por aquí

1. Lee `docs/01_concepto_sonido_externo.md` (qué se puede y qué no).
2. `docs/02_hardware.md` para la lista de compra (~75 € Pi + OBD + relés, +120–150 € la válvula instalada).
3. `docs/04_instalacion.md` para flashear Pi OS y dejar el servicio corriendo.

## Coste y tiempo

- Componentes electrónicos: **~75 €**
- Válvula de escape + soldadura en taller: **~120–170 €**
- Tiempo Pi (config + cableado): 2–3 h
- Tiempo taller (válvula): 1–2 h
