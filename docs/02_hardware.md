# 02 · Hardware — lista de compra y cableado

## 2.1 Componentes (≈ 70–110 €)

| # | Pieza | Modelo recomendado | Aprox. | Notas |
|---|---|---|---|---|
| 1 | SBC | **Raspberry Pi Zero 2 W** (o Pi 4 si quieres pantalla) | 18–45 € | WiFi/BT integrados, suficiente para Flask + OBD |
| 2 | microSD | SanDisk Industrial 16–32 GB A1 | 8–15 € | A1 obligatorio por IOPS |
| 3 | Alimentación coche | **Buck DC-DC 12→5V 3A** con protección (LM2596 + TVS, mejor un módulo automotive Pololu D24V22F5) | 8–18 € | Filtro de transitorios del coche es crítico |
| 4 | OBD-II ELM327 | **ELM327 USB v1.5 con chip genuino** (o vgate iCar Pro BLE 4.0) | 15–25 € | Los chinos clónicos van, pero el genuino aguanta mejor el ruido CAN |
| 5 | Splitter OBD-II | Cable Y OBD-II (macho/2× hembra) | 8–12 € | Permite tener ELM + VCDS simultáneamente |
| 6 | Relé | **Módulo relé 4 canales 5 V con optoacoplador** (SRD-05VDC-SL-C) | 6–10 € | Optoacoplado obligatorio para proteger GPIO |
| 7 | Fusibles | Portafusibles ATC + fusible 3 A | 3 € | Entre +12 V coche y buck |
| 8 | Cable | 18 AWG silicona rojo/negro 2 m, 22 AWG dupont | 5 € | |
| 9 | Caja | Caja ABS IP54 100×68×50 mm | 5–8 € | Cuidado con calor en compartimento motor; mejor en habitáculo |
| 10 | (Opcional) Pantalla | Waveshare 3.5" táctil HDMI | 25 € | Si quieres dashboard físico además del móvil |

**Total mínimo** (sin pantalla): **~75 €**.

## 2.2 Diagrama de conexión

```
[+12V perm. coche]──[Fusible 3A]──┐
                                   │
[Llave/Ignición +12V SW]──────┐    │   ← detectar contacto on/off (opcional, GPIO con divisor)
                              │    │
                              │   [Buck 12→5V]──┬── 5V Pi (GPIO pin 2/4)
                              │                 └── 5V módulo relé (VCC)
                              │
                              └──[Divisor 100k/22k]──GPIO17 (entrada "IGN_ON")

[GND coche] ──┬── GND Pi (pin 6)
              └── GND módulo relé

Pi GPIO → Módulo relé (4 canales, opto):
  GPIO 5  (pin 29) → IN1  (Relé 1: p.ej. válvula sound)
  GPIO 6  (pin 31) → IN2  (Relé 2: LED indicador modo)
  GPIO 13 (pin 33) → IN3  (Relé 3: libre)
  GPIO 19 (pin 35) → IN4  (Relé 4: libre)

OBD-II:
  Conector OBD-II → Splitter Y → ELM327 USB → Pi USB
                                ↘ → segundo puerto libre (VCDS)
```

> ⚠️ **Alimentación**: si conectas el buck a **+12 V permanente**, la Pi sigue
> encendida con el coche apagado y vacía batería. Usa **+12 V conmutada por
> contacto** (post-llave) o añade el detector IGN_ON con divisor para que la
> Pi haga `shutdown` ordenado al perder contacto (script `scripts/ign_watch.py`,
> incluido aparte si lo pides).

## 2.3 Anti-ruido eléctrico

- Buck con condensador adicional **470 µF + 100 nF cerámico** a la entrada.
- Cable OBD-II: si la Pi reinicia con el coche en marcha → problema EMI. Mete
  ferrita en el cable USB del ELM327.
- GND único: la Pi y el módulo relé comparten **el mismo GND** que el buck;
  no mezclar con GND de chasis por puntos distintos (loops).

## 2.4 Para qué usar los relés (ideas)

1. **Válvula sonora externa**: tipo "active exhaust valve" en el escape posterior,
   normalmente abierta para sonido grave a baja velocidad, cerrada por encima de
   X RPM/velocidad.
2. **LED de modo** en salpicadero (verde = control normal, ámbar = modo sound).
3. **Switch ECU dual-map** (si tu flasher soporta tabla doble por entrada CAN).
4. **Corte de cargas no críticas** (relé de fan auxiliar en pruebas estáticas).
5. **Botón virtual de "borrar DTC"** desde móvil (sin tocar el actuador).

⚠️ **Nunca** uses un relé para cortar la señal de control o feedback del actuador
VTG Hella. Genera P2563 instantáneo y limp. Esto está bloqueado por diseño en el
firmware del toolkit.
