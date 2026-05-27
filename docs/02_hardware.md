# 02 · Hardware — lista de compra exacta

## 2.1 Lista pega-y-compra

| # | Búsqueda en Amazon.es | Modelo | Precio |
|---|---|---|---|
| 1 | **Raspberry Pi Zero 2 W** | Raspberry Pi Foundation | ~22 € |
| 2 | **SanDisk Industrial microSD 16 GB A1** | SDSDQAF3-016G | ~10 € |
| 3 | **vGate iCar Pro Bluetooth 4.0 BLE OBD2** | iCar Pro BLE | ~25 € |
| 4 | **DROK 12V to 5V buck converter 5A automotive** | DROK 090408 o Pololu D24V22F5 | ~12 € |
| 5 | **Módulo relé 1 canal 5 V optoacoplador** | SongHe / SainSmart 1ch 5V | ~5 € |
| 6 | **Cable extensión conector actuador VTG Hella** o pigtail genérico de 6 pines 2.8 mm | "VTG actuator pigtail Hella" o se hace casero | ~8–15 € |
| 7 | **Portafusibles ATC inline + fusibles 3 A** | cualquiera | ~4 € |
| 8 | **Cables Dupont F-F 20 cm** (pack) | cualquiera | ~4 € |
| 9 | **Cable silicona 18 AWG rojo/negro 2 m** | cualquiera | ~4 € |
| 10 | **Caja ABS IP54 100×68×50 mm** | cualquiera | ~5 € |
| 11 | **Terminales faston 2.8 mm + crimpadora** | cualquiera | ~6 € |
| 12 | **Diodo 1N4007** (×5) | cualquiera | ~1 € |

**Total: ~100 €.**

⚠️ Solo necesitas **1 canal de relé**, no 4. El módulo de 1 canal es más
barato y ocupa menos. Si ya tienes uno de 4, vale igual; usas un solo
canal.

## 2.2 Por qué cada cosa

- **Pi Zero 2 W**: dual-core, WiFi+BT, 22 €. No uses Pi Zero W (v1, lenta).
  La Zero 2 W lleva Bluetooth integrado, no necesitas dongle.
- **ELM327 Bluetooth (no USB)**: te lo pidió tú. El Bluetooth simplifica el
  cableado (no hay USB OTG entre el coche y la Pi). La iCar Pro BLE 4.0 es
  estable, dura años. Evita las ELM327 BT clásicas (BT 2.0) — son lentas
  y dan problemas con la Pi.
- **DROK buck automotive**: filtros para load dump del coche (picos hasta
  60 V al arrancar). Un cargador USB de coche normal **no aguanta**.
- **Módulo de relé 1ch 5V opto**: la bobina del relé se alimenta a 5 V
  desde la Pi, el optoacoplador aísla el GPIO de los 12 V del coche. El
  relé interno (SRD-05VDC-SL-C) corta hasta 10 A — sobrado para los <2 A
  que tira el actuador VTG.
- **Pigtail / cable extensión del conector VTG**: para no cortar el cable
  original del mazo del coche. Empalmas el extensión y, si algún día
  quieres volver a stock, desconectas el extensión y todo queda como
  estaba. Si no encuentras pigtail específico Hella, el truco es: comprar
  un actuador VTG averiado de desguace por 10 €, cortarle el conector con
  20 cm de cable, y usarlo como pigtail.
- **Diodo 1N4007**: en paralelo a la bobina del relé Bosch (si decides
  añadir uno automotive). No imprescindible si usas solo el módulo opto.

## 2.3 Diagrama de conexión

```
Coche +12V ignición ─┬──[Fusible 3A]──[Buck DC-DC]──┬── 5V → Pi pin 2
                     │                              └── GND → Pi pin 6
                     │
                     │
                     │     ┌──────────────────────────┐
                     │     │   Módulo relé 1 ch 5V    │
                     │     │                          │
                     │     │ VCC ← 5V Pi              │
                     │     │ GND ← GND Pi             │
Pi BCM5 (pin 29) ────┼─────┤ IN  ← señal control      │
                     │     │                          │
                     │     │ COM ◄────── +12V coche   │ ← desde el cable
                     │     │                          │   del mazo que iba
                     │     │ NO  ──────► +12V VTG     │   al pin 1 del VTG
                     │     │ NC  (no usar)            │
                     │     └──────────────────────────┘
                     │
                     │
Cable +12V del mazo ─┘── (era el pin 1 del conector actuador)
del coche al actuador      ahora va a COM del relé
                           del relé a NO sale al actuador (con pigtail)

GND coche ────────────────► pin 2 del actuador VTG (sin tocar)
LIN ECU ──────────────────► pin 3 del actuador VTG (sin tocar)
```

**Resumen**: solo intervienes el cable +12 V del actuador. Lo cortas, metes
el relé en serie. El resto del conector se queda igual.

### Cuando el relé está ON (estado ENGAGED):
- Bobina energizada (GPIO LOW por active-low).
- Contacto COM–NO cerrado.
- +12 V del coche llega al actuador.
- ECU controla VTG normalmente.

### Cuando el relé está OFF (estado BYPASS):
- Bobina sin energía (GPIO HIGH).
- COM–NO abierto.
- Actuador sin +12 V.
- Álabes en posición failsafe mecánica.

## 2.4 Punto físico donde meter el relé en el motor

El conector del actuador VTG en el 2.7 TDI está **debajo del turbo**, en el
lado derecho del motor mirando desde delante. Acceso:
- Por arriba: difícil, conducto de admisión por medio.
- Por debajo: foso o rampa.
- Recomendado: quita el deflector inferior del motor (5 min, 4 tornillos T30).

Pasa el cable nuevo (que va del relé al pin 1 del actuador) por un grommet
del firewall hacia el habitáculo, donde estará la Pi y el relé. Selladura
con tubo termorretráctil + sikaflex.

## 2.5 Lo que ya NO necesitas (del proyecto anterior)

- ❌ Válvula de bypass de escape
- ❌ Soldadura en taller
- ❌ Soundbooster, altavoz, amplificador
- ❌ Splitter OBD-II (con BT no hace falta)
- ❌ ELM327 USB

## 2.6 Tiempo de instalación

- Pi + flasheo SD + config: 1 h
- Pairing Bluetooth ELM327: 15 min
- Identificar el pin +12 V con multímetro: 15 min
- Cortar y empalmar el cable: 30 min
- Pruebas en banco antes de meter en coche: 30 min
- Instalación final: 1 h

**Total: ~3.5 h** un sábado por la mañana.
