# EDC17CP14 VTG Sound Tuning Toolkit
**Audi A6 C6 2.7 TDI (BPP/BSG/CAN) — 2009**

Sistema de apoyo para tuning de VTG (sonido grave a bajas RPM, sin DTC) basado en
Raspberry Pi + ELM327 + relé, con interfaz web para móvil.

> ⚠️ **Aviso legal y de seguridad**
> Modificar el software de la ECU puede invalidar la garantía, afectar emisiones
> y la legalidad en circulación (ITV/TÜV). Este repositorio es una guía técnica
> y un toolkit para banco/pruebas privadas, no asesoría legal. Cualquier mapa
> publicado de Bosch EDC17 es propiedad intelectual del fabricante: trabaja
> siempre sobre tu propio fichero (read original → backup → modificar).

## Estructura

```
docs/
  01_concepto_vtg.md       # Lógica de la modificación, mapas, parámetros
  02_hardware.md           # Lista de compra y cableado
  03_seguridad_dtc.md      # Estrategia de borrado selectivo (no enmascarar fallos reales)
  04_instalacion.md        # Pasos en la Raspberry
app/
  obd_manager.py           # ELM327: lectura PIDs, DTCs, borrado selectivo
  relay_controller.py      # Control GPIO de los relés
  web_server.py            # Flask + SocketIO, UI móvil
  config.yaml              # Whitelist de DTCs, GPIO, OBD port
  templates/index.html     # UI móvil responsive
systemd/
  edc17-vtg.service        # Arranque automático en boot
scripts/
  install.sh               # Instalación en Raspberry Pi OS Lite
```

## Resumen del sistema

1. La Raspberry Pi se alimenta del coche (12 V → 5 V) por buck convertidor con fusible.
2. ELM327 USB conectado a OBD-II → `python-obd` lee PIDs (RPM, MAP, MAF, IAT, ECT, demanda de par, DTCs).
3. Relé HAT controla salidas auxiliares por GPIO (uso libre: válvula sound, LED, switch de modo).
4. Servicio Flask + WebSocket sirve dashboard en `http://raspberrypi.local:5000` o por hotspot WiFi de la Pi.
5. Borrado de DTC **selectivo** (whitelist) cada 10 s **solo si** la ECU está parada o en idle estable — nunca durante carga, nunca códigos críticos.
