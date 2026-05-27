# 02 · Hardware — lista de compra y cableado

## 2.1 Componentes electrónicos (Raspberry + OBD + relés)

| # | Pieza | Modelo recomendado | Aprox. | Notas |
|---|---|---|---|---|
| 1 | SBC | **Raspberry Pi Zero 2 W** | 18–25 € | WiFi/BT integrados |
| 2 | microSD | SanDisk Industrial 16–32 GB A1 | 8–15 € | A1 obligatorio por IOPS |
| 3 | Alim. coche | **Buck DC-DC 12→5V 3A** automotive (Pololu D24V22F5 / RECOM) | 8–18 € | Filtro de transitorios crítico |
| 4 | OBD-II | **ELM327 USB v1.5** (chip genuino) o vGate iCar Pro BLE 4.0 | 15–25 € | USB = más estable |
| 5 | Splitter OBD-II | Cable Y OBD-II (macho/2× hembra) | 8–12 € | Permite ELM + VCDS simultáneamente |
| 6 | Relé | **Módulo 4 canales 5 V con optoacoplador** | 6–10 € | OPTO obligatorio para proteger GPIO |
| 7 | Fusibles | Portafusibles ATC + 3 A | 3 € | Entre +12 V y buck |
| 8 | Cableado | 18 AWG silicona, 22 AWG dupont | 5 € | |
| 9 | Caja | ABS IP54 100×68×50 mm | 5–8 € | Mejor en habitáculo, no vano motor |

## 2.2 Hardware del sonido (el que hace el ruido)

Aquí hay **dos caminos**. Puedes hacer uno u otro, o los dos.

### Opción A — Válvula de bypass eléctrica en escape (recomendada para sonido real)

| # | Pieza | Modelo | Aprox. |
|---|---|---|---|
| A1 | Válvula 12 V con servo | Chino genérico 2.25"/2.5"/3" (51/63/76 mm) con motor 12 V tipo "QTP-like" — Aliexpress/Amazon "exhaust cutout valve" | 30–80 € |
| A2 | Tubo de bypass | Tubo inox 2" con codo y soldadura | 15–30 € + taller |
| A3 | Soldador / taller escape | Mano de obra para empalmar el bypass al silenciador trasero | 40–80 € |
| A4 | Diodo flyback | 1N4007 a través de los terminales del motor (proteger relé) | < 1 € |

**Ubicación**: bypass del silenciador trasero, **siempre post-DPF y post-CAT**. La salida del bypass desemboca después del silenciador o directamente al exterior con su propio remate.

**Cableado del motor de la válvula**:
- Una válvula típica de Aliexpress usa un controlador con 2 cables al motor (polaridad invertida = sentido de giro). Para esto necesitas **2 relés con contactos NC/NA** en configuración H-bridge, o más simple: comprar válvula con **fin de carrera + driver propio** y usar 1 relé que active "abrir" mantenido.
- Otra opción: **válvula "vacuum-like" controlada por entrada lógica** (3 cables: +12, GND, señal abrir/cerrar). Esta es la más cómoda — 1 relé y listo.
- Compra mirando que tenga **driver/controlador incluido y entrada de control** (no la cruda de solo motor DC). Marcas comerciales: BCS, QTP, GReddy, ThorTech.

### Opción B — Soundbooster activo (más fácil de instalar, sonido sintético)

| # | Pieza | Modelo | Aprox. |
|---|---|---|---|
| B1 | Amplificador clase D 12 V | TPA3116 o similar (mono 100 W) | 15–25 € |
| B2 | Altavoz de banda ancha 4–8 Ω | Visaton FRS 8 o exciter 50 W bajo capó / bajo coche | 20–40 € |
| B3 | DAC USB | Cheap USB sound card o usar PWM Pi + filtro RC | 5–15 € |
| B4 | Caja sellada o tubo | DIY o caja de subwoofer pequeña | 5–20 € |
| B5 | Muestras de sonido | Loops sintéticos V8/diesel — generados con un script Python | 0 € |

En esta opción la Pi reproduce un loop de sonido pre-grabado, **modulado en pitch/volumen según RPM** (RPM bajas = pitch grave, fade in/out). El relé 2 enciende el amp solo cuando se necesita. Es el principio que usan Kufatec Soundbooster, Maxhaust, etc., pero DIY a 1/10 del precio.

⚠️ Legalidad: tanto válvula como soundbooster pueden ser ilegales para circulación
según país (en España la ITV mide ruido estático). Úsalo bajo tu responsabilidad.

## 2.3 Diagrama de conexión (versión válvula)

```
[+12V perm.]──[Fusible 3A]──┐
                            │
[+12V Ignición]─────────────┼──────────┐
                            │          │
                          [Buck]── 5V ─┴── Pi USB-IN + relé VCC
                            │
                          [GND]── GND coche / Pi / relé (estrella, un solo punto)

Pi GPIO BCM 5 (pin 29) ─── IN1 relé   ──►  contacto NA al control de la válvula (+12V → COM)
Pi GPIO BCM 6 (pin 31) ─── IN2 relé   ──►  +12V amp soundbooster (opcional)
Pi GPIO BCM 13(pin 33) ─── IN3 relé   ──►  LED indicador en salpicadero
Pi GPIO BCM 19(pin 35) ─── IN4 relé   ──►  libre
Pi GPIO BCM 17(pin 11) ◄── divisor 100k/22k desde +12V Ignición  (detecta IGN ON/OFF)

OBD-II coche ── Y-splitter ── ELM327 USB ── Pi USB
                          └── DB9/OBD libre para VCDS
```

## 2.4 Diodo flyback (importante si controlas el motor de la válvula directamente)

Si la válvula es solo motor DC y controlas con relé, mete un diodo 1N4007
inverso en paralelo a los terminales del motor para absorber el back-EMF
cuando el relé desconecta. Sin diodo, el contacto del relé chispea y se
quema en pocas semanas.

## 2.5 Coste total estimado

| Configuración | Total |
|---|---|
| Pi + OBD + relés + cableado (sin sonido) | ~75 € |
| + Opción A (válvula escape instalada en taller) | ~190–250 € |
| + Opción B (soundbooster DIY) | ~125–175 € |
| + Ambas | ~250–300 € |

## 2.6 Lo que NO necesitas comprar

- ❌ Cable K-line / KKL — no hace falta, OBD-II CAN va por ELM327.
- ❌ Tristar / "tuning box" — no toca nada en la ECU.
- ❌ Sensor MAP externo — la Pi lo lee por OBD.
- ❌ Actuador VTG de repuesto — no tocas el original.
