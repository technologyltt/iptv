# 01 · Concepto — sonido grave SIN tocar la ECU

## 1.1 Qué se puede y qué no, sin reflashear

| ¿Quieres…?                                          | ¿Sin tocar mapa?                | Por qué |
|---|---|---|
| Cambiar posición VTG / abrir álabes                 | **No**                          | Lazo cerrado ECU↔actuador Hella. Intercepción = P2563 + limp |
| Cambiar boost target o torque request               | **No**                          | Solo en mapas EDC17 |
| Cambiar estrategia cold-start                       | **No**                          | Idem |
| **Modular el sonido del escape** con válvula externa| **Sí**                          | Es hardware aguas abajo del cat/DPF — no afecta a la ECU |
| Añadir generador de sonido activo (altavoz+amp)     | **Sí**                          | Es audio en cabina/bajo capó — totalmente externo |
| Leer telemetría (RPM/MAF/boost/DTC) por OBD         | **Sí**                          | Modo 01/03/04 estándar |
| Borrar DTCs puntualmente                            | **Sí**, con whitelist           | Modo 04 estándar (con cuidado) |
| Encender/cortar accesorios (relé)                   | **Sí**                          | GPIO de la Pi |

Conclusión: el ronquido grave a 600–1400 rpm baja carga lo vas a conseguir
con **una válvula de bypass eléctrica en el escape** (o un sound-booster activo),
y la Raspberry decide cuándo abrirla/cerrarla en función de lo que lee por OBD.
**No se toca ECU, no hay riesgo de DTC por VTG**, no hay limp mode.

## 1.2 Arquitectura

```
                      ┌──────────────────┐
                      │   ECU EDC17CP14  │  ← intacto, sin reflash
                      └─────────┬────────┘
                                │
                                │  OBD-II (lectura)
                                ▼
       ┌────────────────────────────────────────────┐
       │           Raspberry Pi Zero 2 W            │
       │ ─ python-obd: RPM, MAF, ECT, pedal, DTCs   │
       │ ─ sound_controller.py: decide modo         │
       │ ─ Flask + WS: UI móvil                     │
       │ ─ GPIO → módulo relé 4 ch                  │
       └─────────────┬──────────────────┬───────────┘
                     │                  │
            Relé 1   │                  │  Relé 2 (opcional)
            (sound)  ▼                  ▼  (LED modo / amp ON)
              ┌─────────────┐    ┌──────────────────┐
              │ Válvula     │    │ Soundbooster     │
              │ bypass      │    │ activo (altavoz) │
              │ escape 12V  │    │ bajo capó        │
              └─────────────┘    └──────────────────┘
```

## 1.3 Lógica del controlador de sonido

El módulo `sound_controller.py` evalúa cada 200 ms:

```
abrir_valvula =
   (RPM en [rpm_min, rpm_max])           # 600–1400 por defecto
   AND (pedal_pct ≤ pedal_max)           # baja carga (≤ 20 %)
   AND (boost_bar ≤ boost_max)           # confirma que no hay demanda real
   AND (speed_kmh ≤ speed_max)           # solo a baja velocidad
   AND (ECT en cold_start_range  OR  modo == AUTO)   # frío = válvula abierta
   AND (modo != FORCED_CLOSED)
```

Con **histeresis** para evitar chatter del relé:
- Apertura: cuando se cumplen condiciones durante `hold_open_ms` (p. ej. 300 ms)
- Cierre: cuando dejan de cumplirse durante `hold_close_ms` (p. ej. 500 ms)

Modos manuales desde la UI:
- **AUTO** — comportamiento descrito arriba
- **OPEN** — siempre abierta (modo "show" estacionado)
- **CLOSED** — siempre cerrada (autopista, gasolinera, ITV)
- **COLD_ONLY** — solo abre con ECT < 50 °C (sonido en arranque, silencioso después)

## 1.4 Por qué pasa "P0299/P003A no aparece"

Porque no estás tocando nada que la ECU monitorice. La válvula está en el
escape trasero, después de DPF/CAT y del sensor de presión diferencial DPF.
La ECU no sabe que existe. Riesgo de DTC: 0 (siempre que no metas la válvula
en una sección que mida — no ponerla entre turbo y DPF).

## 1.5 Dónde NO instalar la válvula

- ❌ Entre turbo y catalizador (afecta contrapresión y sensor de gases)
- ❌ Entre cat y DPF (idem)
- ❌ Antes del sensor diferencial DPF
- ✅ Después del silenciador trasero, o en bypass del silenciador trasero
- ✅ Bypass de un resonador intermedio (zona ya tranquila, post-DPF)

## 1.6 Lo que aporta la Raspberry (vs. un simple interruptor)

Un interruptor manual también abre/cierra la válvula. Lo que añade la Pi:

1. **Automatización con sensado real** — abre solo cuando merece (idle, frío, baja carga); cierra sola en autopista para no atronar a 130 km/h.
2. **Modo cold start** automático — ronquido en los primeros 2–3 minutos, después silencioso.
3. **Diagnóstico OBD** integrado — ves códigos, los borras si quieres, todo en el móvil.
4. **Histeresis y "no chattering"** — el relé no traquetea en transiciones.
5. **Logging** — guarda CSV de todo (útil si algún día quieres llevarlo al taller).
6. **Botón de pánico** — un toque en la UI deja la válvula cerrada y todo en estado stock.
