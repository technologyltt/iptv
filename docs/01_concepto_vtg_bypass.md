# 01 · Concepto — bypass del actuador VTG con relé

## 1.1 Idea en una frase

Un **relé corta el +12 V del actuador VTG Hella** durante el arranque. Sin
energía, los álabes quedan en su posición mecánica de reposo (failsafe). El
coche arranca y rueda en ese estado. Cuando quieres potencia normal, pulsas el
botón "ACTIVAR TURBO" en el móvil → la Pi cierra el relé → el actuador recibe
+12 V → la ECU recupera el control y la Pi borra los DTCs VTG automáticamente
vía ELM327 Bluetooth.

## 1.2 ⚠️ Lo que tienes que verificar ANTES de comprar nada

El actuador Hella no falla siempre en "abierto". Hay dos versiones:

- **Failsafe ABIERTO** — sin corriente, el muelle deja los álabes abiertos →
  sonido grave, sin spool, poco par. ✅ Tu mod funciona.
- **Failsafe CERRADO** — sin corriente, el muelle cierra los álabes →
  alta restricción, motor ahogado, posible overboost al subir rpm. ❌ Tu mod
  no aplica.

La mayoría de turbos VAG con actuador Hella en este motor (BorgWarner KP39,
PSP14140 o similar) son **failsafe cerrado**. Un porcentaje pequeño es abierto.

**Test gratis de 30 segundos antes de gastar un euro**:
1. Coche frío, contacto quitado.
2. Desenchufa el conector del actuador VTG (debajo del turbo, conector
   eléctrico de 6 pines).
3. Da contacto, espera 5 s, arranca.
4. Escucha:
   - Suena ronco/grave, ralenti irregular pero sin ahogo → **abierto** ✅
   - Ralenti normal pero sin par al pisar, posible humo, alarma → **cerrado** ❌
5. Apaga, vuelve a conectar el actuador, da contacto sin arrancar, espera 30 s,
   borra los códigos con VAG-COM o ELM327.

Si suena ahogado, **abandona este enfoque**. No hay forma con un relé de
forzar la posición opuesta a la failsafe.

## 1.3 Qué cable corta el relé exactamente

El actuador Hella tiene un conector de 6 pines. Los pines típicos son:

| Pin | Función |
|---|---|
| 1 | +12 V switched (ignición) ← **éste es el que cortamos** |
| 2 | GND |
| 3 | LIN bus (comunicación con ECU) |
| 4 | (reserva / sensor de temperatura) |
| 5 | (reserva) |
| 6 | (reserva) |

**Solo se corta el pin de +12 V.** GND y LIN siguen conectados a la ECU.
Resultado: el actuador no tiene de dónde sacar corriente para mover su motor
interno, pero la ECU sigue "viendo" el bus LIN (aunque no recibe respuesta,
lo que sí dispara DTC).

Identifica el pin +12 V con un multímetro:
- Contacto puesto sin arrancar
- Mide cada pin del conector (lado del coche, no del actuador) contra GND chasis
- El que da ~12 V es el de alimentación

> No cortes el LIN ni el GND. Cortar LIN puede activar DTCs adicionales no
> recuperables hasta key-off. Cortar GND deja flotando el sensor de
> posición y puede provocar lecturas erráticas.

## 1.4 DTCs esperados al cortar

En cuanto la ECU detecta al actuador sin respuesta (típicamente en 1–3 s
después de cortar) guarda uno o varios de estos:

| Código | Significado |
|---|---|
| P2563 | Turbocharger Boost Control Position Sensor "A" Circuit Range/Performance |
| P0046 | Turbocharger/Supercharger Boost Control "A" Circuit Range/Performance |
| P132B | Turbocharger Boost Control "A" Performance |
| P003A | Turbocharger/Supercharger Boost Control "A" Position Exceeded Learning Limit |

La ECU **entra en estrategia limp** (par reducido, boost limitado). Esto es lo
que da el sonido "natural sin VTG".

## 1.5 Procedimiento de uso

### Arranque "sonido"
1. Pi alimentada (le das contacto al coche o tienes la Pi siempre on).
2. Abres la app en el móvil (`http://vtgpi.local:5000`).
3. Estado por defecto al boot: **ENGAGED** (relé ON, actuador alimentado).
4. Pulsas **"CORTAR (sonido)"** → relé OFF → actuador sin +12 V.
5. Arrancas el coche.
6. Suena grave. La app muestra los DTCs apareciendo. Estado: **BYPASS**.

### Volver a conducir normal
1. Estás parado o en marcha lenta.
2. Pulsas **"ACTIVAR TURBO"**.
3. La Pi:
   - Cierra el relé → actuador recibe +12 V.
   - Espera 3 s para que el actuador haga su self-calibration interna.
   - Lee DTCs y borra los VTG de la whitelist.
   - Repite hasta 6 veces con 1.5 s de intervalo si los códigos persisten.
4. Si todo va bien: estado **ENGAGED + DTCs limpios**. Conduces normal.
5. Si los códigos persisten tras 6 intentos: la ECU está pegada en limp.
   Solución: parar el motor, key-off 30 s, key-on, volver a pulsar engage.
   Esto fuerza una re-inicialización completa del módulo turbo.

### Si por error pulsas "CORTAR" en marcha
La app rechaza la acción si RPM > 1100, velocidad > 1 km/h, o pedal > 5 %.
No es accidental.

## 1.6 Lo que NO debes esperar

- **No vas a tener boost normal en modo BYPASS.** Vas a tener par muy
  reducido, aceleración floja, posiblemente humo. Es la realidad de rodar
  sin VTG activo en un diésel moderno.
- **No conduzcas largo rato en BYPASS.** El motor sin gestión de turbo
  trabaja en zonas no diseñadas (mezcla pobre, EGT pueden subir si tiras de
  él). Pensado para arrancar, oír el sonido, y devolver a normal.
- **El testigo MIL (luz de motor) se va a encender** mientras estés en
  BYPASS. Al borrar los DTCs con ENGAGE se apaga, pero los códigos quedan
  en el historial como "pendientes" hasta que pase un drive cycle completo.
- **Los readiness monitors se resetean** cada vez que borras. La ITV/TÜV te
  va a suspender si vas justo después. Necesitas ~100–200 km en modo normal
  para que vuelvan a OK.

## 1.7 Riesgos reales

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Posición failsafe = cerrado (mod no funciona) | Media–alta | Test del paso 1.2 antes de comprar nada |
| ECU pegada en limp tras varios ciclos | Baja | Key-off 30 s y engage de nuevo |
| Carbonilla en álabes por estancarlos en posición fija mucho tiempo | Baja a corto, alta a largo | No usar BYPASS más de unos minutos por sesión |
| Sensor MAP detecta underboost severo y guarda P0299 | Media | P0299 está en blacklist — si aparece, investigar. No borrarlo automático |
| Daño en el actuador al re-energizar contra álabes pegados | Muy baja | engage_settle_s en config da 3 s antes de pedir nada al actuador |
| Anulación de garantía / ITV | Alta si lo dejas instalado para inspección | Volver a stock antes de ITV (es un relé, se desmonta en 5 min) |
