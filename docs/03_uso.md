# 03 · Uso diario

## Flujo normal

1. **Subes al coche**, das contacto. La Pi arranca (~30 s).
2. **Abres la app** en el móvil: `http://vtgpi.local:5000` (o IP de la Pi en hotspot).
3. **Estado por defecto al boot**: `ENGAGED` (relé ON, VTG con corriente).

### Si quieres arrancar con sonido grave
- Pulsa **CORTAR (sonido)**. El estado cambia a `BYPASS`.
- Arranca el coche. Suena ronco.
- Verás aparecer los DTCs en la lista (P2563, P0046…). Es esperado.
- La luz MIL del cuadro se enciende.

### Cuando quieras conducir normal
- Mejor parado o muy lento.
- Pulsa **ACTIVAR TURBO**.
- La app muestra "Procesando…". Espera 3–10 s.
- Estado vuelve a `ENGAGED + DTCs limpios`. La MIL se apaga.
- A conducir.

## Si pulsas y dice "Bloqueado: engine_not_idle"
Estás pulsando CORTAR con el coche en marcha y a velocidad > 1 km/h, RPM > 1100
o pedal > 5 %. Para; vuelve a intentarlo.

## Si tras ACTIVAR los DTCs no se borran (estado dice "DTCs persisten")
La ECU se ha quedado pegada en el flag de fallo. Soluciones:

1. **Apaga el motor, espera 30 s, key-on sin arrancar.** Pulsa ACTIVAR de nuevo.
   En el 90 % de casos esto basta.
2. Si persiste: borra con VCDS si lo tienes a mano. La diferencia con el ELM327
   es que VCDS habla UDS al módulo turbo concreto y limpia flags que el modo
   04 estándar no toca.

## Si el motor entra en limp visible al ACTIVAR
Es decir: aceleras y no hay par, RPM no suben más allá de 3000.
- Para el coche. Para el motor.
- Key-off 30 s.
- Arranca de nuevo (sin tocar nada — estado ENGAGED por defecto).
- En el 99 % de casos la ECU sale de limp en ese ciclo.

Si no sale, es que la ECU ha guardado un código que NO es de la whitelist
VTG (por ejemplo P0299 por underboost real durante el bypass). Lee fallos
desde la app, dimelo si te encuentras eso y miramos.

## Antes de pasar la ITV / inspección

1. Devolver al **estado stock**: desconectar el relé del cable +12 V del
   actuador y dejar el cable como estaba. El pigtail facilita esto.
2. Borrar todos los DTCs.
3. Conducir **~150 km** para que los readiness monitors completen.
4. Pasar ITV.

> Dejar la Pi y la caja montadas en el habitáculo no es problema para la
> ITV — no inspeccionan electrónica auxiliar. Lo que tienes que dejar como
> estaba es el cable del actuador.

## Logs

Todo queda en `app/logs/clear.log` en la Pi:

```
2026-05-27T20:14:22Z CLEAR codes=['P2563','P0046'] trigger=turbo_engage
2026-05-27T20:18:11Z CLEAR codes=['P2563'] trigger=manual user=192.168.4.1
```

Si vas al taller con un problema raro, esto es útil para enseñar qué se ha
hecho.
