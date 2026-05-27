# 03 · Seguridad — borrado selectivo de DTCs

## Por qué NO borrar todo cada 10 s

Un `MODE 04` (clear DTCs) borra **todos** los códigos pendientes y confirmados, además
del freeze frame, los readiness monitors y el km recorrido desde la última falla.
Hacerlo cada 10 s significa:

- Enmascaras un fallo real (p.ej. inyector, sensor MAF degradado, EGR pegado).
- Los **readiness monitors** nunca completan → ITV/TÜV te suspenden.
- Pierdes datos de freeze frame que serían valiosos para diagnosticar.
- Algunas ECUs detectan el clearing repetitivo y endurecen otros umbrales.

## Estrategia implementada en `obd_manager.py`

1. **Whitelist explícita** (`config.yaml → clearable_codes`). Solo se borran códigos
   que tú declares. El resto se reporta en la web pero **no** se borra automáticamente.
2. **Pre-condiciones obligatorias** antes de un clear automático:
   - RPM en idle (< 1100 rpm) **durante 5 s seguidos**, o motor parado.
   - Velocidad = 0 km/h.
   - Pedal acelerador < 5 %.
   - Sin códigos críticos fuera de whitelist (si los hay, se aborta el clear).
3. **Rate limit**: máximo 1 clear cada 10 s, y registro persistente (`logs/clear.log`)
   con timestamp + lista de códigos borrados.
4. **Blacklist absoluta**: códigos que NUNCA se borran aunque estén en whitelist:
   - `P0299` (underboost) — si recurre, hay problema real, no enmascarar.
   - `P003A` (boost limit performance) — síntoma de actuador degradado.
   - `P0606` (PCM internal) — fallo de ECU.
   - `P062F` (EEPROM error) — fallo de ECU.
   - Cualquier `U0xxx` (CAN bus) y `B0xxx` (airbag).
5. **Modo manual**: el botón "Clear" en la web siempre requiere confirmación y
   ejecuta el mismo flujo (con la blacklist activa).

## Whitelist típica para esta modificación

Códigos que **pueden** aparecer como falsos positivos al ajustar VTG y tiene
sentido borrar si la causa es la transición de mapas (revisa pre-condiciones
antes de añadir cualquiera):

| Código | Descripción | Por qué puede aparecer | ¿Borrable? |
|---|---|---|---|
| `P2563` | Turbocharger Boost Control Position Sensor "A" Circuit Range/Performance | Transición brusca de setpoint VTG | Sí, si solo aparece en transición |
| `P0046` | Turbocharger Boost Control "A" Circuit Range/Performance | Igual | Sí, condicional |
| `P132B` | Turbocharger Boost Control "A" Performance | Igual | Sí, condicional |
| `P0234` | Overboost | NUNCA | **No** — proteger motor |
| `P0299` | Underboost | NUNCA | **No** — investigar |

> Si después de afinar mapas el código sigue saliendo en **carga**, no es transición:
> es que la modificación está mal y necesita revisión, no borrado.

## Logging

Cada operación queda registrada en `logs/clear.log` en formato:

```
2026-05-27T18:21:34Z CLEAR codes=[P2563] precond_ok=True trigger=auto
2026-05-27T18:21:55Z SKIP  reason=load_too_high trigger=auto
2026-05-27T18:22:10Z CLEAR codes=[P2563] precond_ok=True trigger=manual user=mobile
```

Este log es importante: si llevas el coche a un taller, lo enseñas. Demuestra
qué se ha tocado y cuándo.
