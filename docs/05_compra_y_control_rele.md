# 05 · Qué comprar y cómo controla la Pi el relé (paso a paso)

## 5.1 Lista exacta de compra (Amazon.es / AliExpress)

> Términos de búsqueda y precios orientativos en mayo 2026. Marca preferida primero.

### Raspberry Pi y básicos

| # | Qué comprar | Búsqueda / modelo | Precio | Por qué este |
|---|---|---|---|---|
| 1 | **Raspberry Pi Zero 2 W** | "Raspberry Pi Zero 2 W" — Kubii / Berrybase / Amazon | **~22 €** | WiFi+BT, dual-core, 512 MB. Sobra para esto, consume <2 W. NO comprar Pi Zero W (v1), va lento. |
| 2 | microSD | "SanDisk Industrial 16GB A1" | ~10 € | A1 obligatorio. NO uses una SD lenta sin clase A1 — se corrompe con apagones |
| 3 | Cable mini-HDMI + adaptador micro-USB→USB-A | "Pi Zero starter kit" o suelto | ~8 € | Solo para configurar la primera vez por HDMI. Después todo por SSH |
| 4 | Disipador adhesivo | "heatsink raspberry pi zero" | ~3 € | Opcional pero recomendado en caja cerrada |

### OBD-II

| # | Qué comprar | Búsqueda / modelo | Precio |
|---|---|---|---|
| 5 | **ELM327 USB v1.5** chip genuino | "Vgate ELM327 USB" o "OBDLink SX USB" | 20 € (Vgate) — 60 € (OBDLink, mejor) |
| 6 | (Opcional) splitter OBD-II | "OBD2 Y splitter cable" | 10 € |

> Si vas justo de presupuesto: ELM327 BT 4.0 vGate iCar Pro (~25 €). Pero el USB es más estable: cero pérdidas de conexión.

### Alimentación 12V → 5V

| # | Qué comprar | Búsqueda / modelo | Precio |
|---|---|---|---|
| 7 | **Buck DC-DC automotive** | "DROK 12V to 5V 5A car USB" o "Pololu D24V22F5" | 8–18 € |
| 8 | Portafusibles ATC + fusibles 3 A | "ATC fuse holder inline" | 4 € |
| 9 | Cable rojo/negro 18 AWG silicona 2 m | cualquiera | 4 € |
| 10 | Terminales faston hembra 6.3 mm + crimpadora barata | cualquiera | 6 € |

⚠️ **No uses un cargador de móvil USB de coche cualquiera** como alimentación. El coche tiene picos de hasta 60 V (load dump) cuando arranca o se desconecta el alternador. El buck DROK/Pololu está pensado para automoción y aguanta. Un cargador de móvil barato muere a la primera.

### Relé (la parte importante para tu pregunta)

| # | Qué comprar | Búsqueda / modelo | Precio |
|---|---|---|---|
| 11 | **Módulo 4 relés 5 V con optoacoplador** | "4 channel relay module 5V optocoupler" — SainSmart o clon | 6–10 € |

**Cuidado al elegir el módulo de relé** — los hay de tres tipos, compra el correcto:

- ✅ **El bueno**: "5V trigger, optocoupler isolated, **active LOW**". Es el más común y barato. Tiene bornera de 3 pines (VCC/GND/IN), optoacoplador (chip negro de 4 patas, normalmente PC817 o LTV-817), y jumper "JD-VCC" separado de VCC. **Este es el que recomiendo.**
- ⚠️ **El regular**: "5V trigger" sin optoacoplador. Funciona pero un cortocircuito en el lado 12 V puede mandarte tensión al GPIO de la Pi. Evítalo.
- ❌ **El malo para esto**: "3.3 V trigger". No es necesario — los pines GPIO de la Pi son 3.3 V pero el módulo de 5 V se dispara perfectamente con 3.3 V de control. El de 3.3 V está pensado para Arduino 3V3 con relés de coil de 3.3 V y es más raro.

**Especificación del relé en el módulo** (el chip azul):
- Bobina: 5 V DC (la maneja el GPIO+optoacoplador)
- Contactos: **10 A @ 250 V AC o 10 A @ 30 V DC** ← más que suficiente para tu válvula de escape de 12 V/2 A o un soundbooster
- Modelo del relé: **SRD-05VDC-SL-C** (Songle). Estándar de la industria china, fiable.

### Cableado y caja

| # | Qué comprar | Búsqueda / modelo | Precio |
|---|---|---|---|
| 12 | Cables Dupont hembra-hembra 20 cm (pack) | cualquiera | 4 € |
| 13 | Caja ABS 100×68×50 mm IP54 | "ABS junction box IP54" | 5 € |
| 14 | Pasacables de goma | cualquiera | 2 € |
| 15 | Tubo termorretráctil mix | cualquiera | 3 € |

### Solo si vas con válvula de escape

| # | Qué comprar | Búsqueda / modelo | Precio |
|---|---|---|---|
| 16 | **Válvula bypass escape 12 V** | AliExpress: "exhaust cutout valve 2.5 inch electric with **wireless remote**" (~50 €), o **BCS Performance Cutout Valve** (mejor calidad, ~120 €). | 50–120 € |
| 17 | Soldadura del bypass en taller | Cualquier taller de escapes | 50–80 € |
| 18 | Diodo 1N4007 | cualquiera | 0.5 € |

> Las válvulas chinas de AliExpress vienen con un controlador propio. Para integrar con la Pi: o usas el **mando RF + módulo receptor RF** ignorando el relé (sin Pi), o conectas el relé a las dos líneas del botón "abrir" del controlador (el mando es solo un pulsador). La opción Pi+relé sustituye al mando inalámbrico.

### Totales

| Configuración | Coste |
|---|---|
| **Solo electrónica** (Pi + OBD + relé + cableado) | **~75 €** |
| + Válvula china + taller | ~175–200 € |
| + Válvula BCS (calidad) + taller | ~245–270 € |

---

## 5.2 Cómo la Pi controla el relé (eléctricamente)

### Concepto en una frase
El módulo de relé tiene un **lado de control** (3.3–5 V de la Pi) y un **lado de potencia** (12 V del coche). Están **aislados ópticamente** — el GPIO nunca ve los 12 V. La Pi solo "pide" al optoacoplador que active el electroimán del relé; este cierra mecánicamente el contacto de potencia.

### Pinout del módulo de relé

```
   Lado lógico (a la Pi)             Lado potencia (al coche)

   ┌──────────────────────┐
   │  VCC  ──────────┐    │
   │  GND  ────────┐ │    │      RELÉ 1:  COM1  NO1  NC1
   │  IN1  ──────┐ │ │    │              ●    ●    ●
   │  IN2  ────┐ │ │ │    │      RELÉ 2:  COM2  NO2  NC2
   │  IN3  ──┐ │ │ │ │    │              ●    ●    ●
   │  IN4  ┐ │ │ │ │ │    │              ...
   │       │ │ │ │ │ │    │
   │      [optoacopladores]│
   │       │ │ │ │ │ │    │
   └───────┴─┴─┴─┴─┴─┴────┘
```

**Lado lógico (entrada — a la Pi)**:
- `VCC` = +5 V (de la Pi, pin 2 o 4)
- `GND` = masa común (pin 6 de la Pi)
- `IN1, IN2, IN3, IN4` = entradas de control. **Activas en LOW**: poner el GPIO a 0 V activa el relé; ponerlo a 3.3 V lo desactiva.

**Lado potencia (salida — al cable de la válvula)**:
Cada relé tiene 3 bornes:
- `COM` (común): aquí conectas la entrada de tensión (p. ej. +12 V del coche)
- `NO` (normally open): contacto que se **cierra** cuando el relé se activa
- `NC` (normally closed): contacto que se **abre** cuando el relé se activa

Para una válvula que debe alimentarse cuando "modo sound = abrir":
```
+12V coche ──[fusible]──► COM1
                          NO1 ──► cable + de la válvula
                          NC1 ──► (sin conectar)
GND coche ─────────────────────► cable − de la válvula
```

Cuando el GPIO se pone a LOW → el optoacoplador conduce → la bobina del relé se energiza → el contacto COM-NO se cierra → la válvula recibe 12 V → se abre.

### Conexión completa Pi ↔ módulo de relé

Numeración **pin físico** del header de 40 pines de la Pi (mira el header con el USB hacia la izquierda):

```
   Pi pin físico   →  Módulo relé      Función
   ─────────────────────────────────────────────
   2  (5V)         →  VCC              alimenta lado lógico del módulo
   6  (GND)        →  GND              GND común
   29 (BCM 5)      →  IN1              relé 1 = válvula sound
   31 (BCM 6)      →  IN2              relé 2 = amp soundbooster (opcional)
   33 (BCM 13)     →  IN3              relé 3 = LED testigo en salpicadero
   35 (BCM 19)     →  IN4              relé 4 = libre
```

> Si tu módulo tiene un jumper "JD-VCC ↔ VCC", **déjalo puesto** (alimentar bobinas desde la propia Pi). Si quieres aislamiento total, separa el jumper y alimenta JD-VCC con otra fuente de 5 V independiente — para esta aplicación no hace falta.

### Diagrama completo

```
              +12 V batería (siempre activo)
                       │
                  [Fusible 3A]
                       │
       ┌───────────────┴───────────────┐
       │                               │
   [Buck DC-DC]                    +12 V → COM1 del relé
       │  in                                │
       │  out 5V ─── pin 2 Pi               │
       │  out GND ── pin 6 Pi + GND coche   │       Relé activado por Pi
       │                                    ▼
   Pi (Zero 2 W)                       NO1 ─── [Fusible 3A] ─── + Válvula escape
       │  GPIO BCM5 → IN1 módulo                                       │
       │  GPIO BCM6 → IN2 módulo                                       │
       │                                                       GND coche
       │ USB ── ELM327 ── OBD-II coche
       │
       └ WiFi → tu móvil
```

---

## 5.3 Código Python que controla el relé

### El mínimo absoluto (test, sin nada más)

Guarda como `~/test_relay.py`:

```python
import RPi.GPIO as GPIO
import time

RELAY_PIN = 5  # BCM 5 = pin físico 29

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

print("Activando relé 1 (debes oír 'click')")
GPIO.output(RELAY_PIN, GPIO.LOW)   # LOW = activo en este módulo
time.sleep(3)

print("Desactivando relé 1")
GPIO.output(RELAY_PIN, GPIO.HIGH)
time.sleep(1)

GPIO.cleanup()
```

Ejecuta:
```bash
sudo python3 ~/test_relay.py
```
Tienes que oír el **click** del relé al activarse y desactivarse, y ver el LED rojo del módulo encenderse/apagarse.

### Cómo lo hace el toolkit (`app/relay_controller.py`)

Ya está implementado:

```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.OUT)

def set_relay(state: bool, active_low: bool = True):
    level = (not state) if active_low else state
    GPIO.output(5, GPIO.HIGH if level else GPIO.LOW)
```

El `sound_controller.py` llama a esto cuando decide "abrir válvula" en función
de RPM/pedal/temperatura leídos por OBD. Tú no tocas nada, lo hace solo. Desde
el móvil eliges modo (AUTO / OPEN / CLOSED / COLD_ONLY) y ya.

---

## 5.4 Procedimiento de prueba antes de instalar en el coche

1. **En el banco** (Pi alimentada por USB del PC, sin OBD, sin coche):
   - Monta Pi + módulo de relé + cables Dupont.
   - Ejecuta `test_relay.py` arriba. Oye los clicks.
   - Conecta un LED + resistencia 1 kΩ a NO1-COM1 con una pila de 9 V para ver que el contacto realmente conmuta.

2. **Con OBD pero sin coche en marcha** (motor parado, contacto):
   - Alimenta la Pi por USB.
   - Conecta el ELM327 a la OBD del coche.
   - Arranca el servicio: `sudo systemctl start edc17-vtg`.
   - Abre la web del móvil. Pulsa el relé 1 manualmente. Verifica el click.

3. **En marcha**, con el buck conectado al coche:
   - Buck a +12 V conmutado por contacto (NO permanente).
   - Verifica que la Pi arranca al dar contacto y apaga sola al cortar (con el watchdog IGN del doc 04).
   - Modo AUTO, da una vuelta. Mira en la app el "motivo" debajo del estado de la válvula: vas viendo `cold_start`, `idle`, `pedal_high`, `speed_high`...

4. **Solo entonces**, conecta el relé a la válvula real.

---

## 5.5 Lista pega-y-compra en Amazon.es

Copia esto en el buscador:

```
Raspberry Pi Zero 2 W
SanDisk Industrial microSDHC 16GB
Vgate ELM327 USB OBD2
DROK 12V to 5V buck converter automotive
4 channel relay module 5V optocoupler SainSmart
ATC fuse holder 3A inline
Dupont female to female jumper wires 20cm
ABS junction box IP54 100x68x50
```

Y para AliExpress (si quieres ahorrar):

```
exhaust cutout valve 2.5 inch electric 12V
1N4007 diode
```
