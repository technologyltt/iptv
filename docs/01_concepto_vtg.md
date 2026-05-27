# 01 · Concepto VTG/VNT — sonido grave sin DTC

Motor: **CAN / BPP / BSG** (Audi 2.7 TDI V6, 140–190 CV), ECU **Bosch EDC17CP14**,
turbo con actuador **electrónico Hella** (no neumático). Bosch ETK suele identificar
estos motores como `CR_3.0V6_TDI_BiT` / `CR_2.7V6_TDI` en proyecto Damos.

## 1.1 Qué produce el "sonido grave" buscado

El sonido grave/ronco a bajas RPM en un TDI con VTG nace de:

1. **Vanos más abiertos** en idle/baja carga → menor restricción en housing → mayor
   sección de paso → frecuencia fundamental del flujo más baja → tono "diésel
   antiguo" más audible.
2. **Menos pre-spool** → menos silbido alto, más ronquido.
3. **Recirculación EGR moderada** (no tocar si no es necesario): aire más caliente
   en colector → combustión ligeramente más ruidosa.

Objetivo: abrir vanos un 5–15 % respecto al mapa stock **solo** en zonas idle,
arranque y baja carga (≤ ~20 % pedal), volviendo de forma progresiva al control
ECU normal a medida que crece la demanda de par.

## 1.2 Mapas clave en EDC17CP14 (nombres orientativos Damos)

> Los nombres pueden variar 1–2 caracteres según release de SW. Usar `WinOLS`
> con Damos/A2L original, o `ECM Titanium` con driver correcto.

| Bloque | Mapa (ejemplos) | Acción |
|---|---|---|
| VTG target idle/startup | `LDPVNZ_KF`, `KF_VTGLLN` (low load), `MLDOFS` | Aumentar apertura 5–15 % entre 600–1400 rpm con load < 25 % |
| VTG cold start | `LDPVNZ_KF_KaSt` o eje paralelo con factor `fKLAK` (cold corr.) | Mantener apertura extra mientras ECT < 50 °C; **no agresivo** para no romper light-off DPF/CAT |
| Boost target low rpm | `LDRXN`, `LDPBN`, `KFLDIMX` | **No bajar** target absoluto; solo suavizar pendiente de subida en zona idle→1400 |
| Torque request low load | `MDFAHFKMS`, `MDMAX_KF` | No tocar a menos que haya tirón al volver a control normal |
| Smoke / airmass limiter | `KFMLLAK`, `LAMFAW_KF` | Solo revisar; si se cierra demasiado al abrir vanos puede haber humo al transicionar |
| Diagnóstico VTG | `LDRVMX`, `LDRVMN`, `DLDR_*` thresholds, `B_ldrabs` | **Solo ampliar ventanas** si aparece P003A/P0046/P2563 por la modificación; nunca desactivar el monitor |
| Protecciones turbo | `LDPBOMX`, `LDOAT`, overspeed, `EGT_max` | **No tocar nunca** |

## 1.3 Estrategia de cambio (suave y reversible)

1. **Backup** del fichero original (`*.bin` + checksum).
2. Subir VTG target en `LDPVNZ_KF`:
   - Filas 600/800/1000/1200/1400 rpm
   - Columnas load 0–25 %
   - Aumentar `+5 %` apertura (= bajar 5 % posición si la convención es 0 = abierto).
   - Verificar dirección en Damos: en EDC17 la convención de `LDPVNZ` puede ser
     "% cerrado" o "% abierto", varía por SW. Comprueba con MWB en VCDS o
     bloque 11/115 (ldraus_w) antes y después.
3. Cold start: mantener el factor `fKLAK` neutro o leve. Subir apertura mientras
   ECT < 40 °C, devolver a normal con rampa hasta 60 °C.
4. **Suavizado de transición**: en `LDPVNZ_KF` los valores deben crecer
   monotónicamente al subir load/RPM. Si dejas un escalón a 25 % de pedal, vas a
   notar tirón o flat-spot. Hazlo en pendiente con 3–4 filas de mezcla.
5. **No tocar** límites de protección (`LDRVMX/LDRVMN`), umbrales de overboost,
   EGT, ni el lazo cerrado del actuador (PID). Solo se cambia el setpoint, no la
   capacidad de la ECU de seguirlo.
6. Recalcular **checksum** (WinOLS lo hace; en EDC17 son CRC32+RSA — necesitas
   bootloader/tricore tool si el flasher no recalcula).

## 1.4 Validación en banco/calle

Antes de tocar el coche:
- Log VCDS / Ross-Tech con MWB de actuador VTG, MAF (g/s), MAP (mbar), demanda
  de par, posición pedal, ECT, EGT pre-turbo, n_motor.
- Comparar pre/post-mod en idle, 1000 rpm sostenido en punto muerto, marcha a
  1200 rpm carga baja en 3ª.
- Verificar que el lazo cerrado VTG converge: error |posición real – setpoint|
  < 3 % en estado estable. Si oscila → has movido un punto fuera del rango
  mecánico del actuador.

## 1.5 Lo que no se hace

- **No** desconectar actuador (genera P2563 inmediato + limp).
- **No** poner resistencia en serie con el feedback (rompe el lazo PID).
- **No** desactivar monitor de turbo en CBS.
- **No** bajar threshold de DPF/EGT.
- **No** clearear DTCs P0299, P003A, P2563 de forma automática sin investigar.
  El borrado automático del toolkit solo aplica a una whitelist explícita y
  **nunca** durante carga (ver `docs/03_seguridad_dtc.md`).
