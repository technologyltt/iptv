# Detective de Bastidor 🕵️

Clon del "Detective de bastidor" de webs tipo *seisenlinea*: metes un VIN
(número de bastidor) y te saca marca, modelo, año, motor e **historial de
titulares** — todo con fuentes **gratis y legales**.

## El "secreto" (cómo lo hacen ellos, y esto)

No hay ninguna API mágica de pago. Son dos fuentes abiertas:

| Dato | Fuente | Coste |
|---|---|---|
| Marca, modelo, año, motor, país | Estándar VIN (tabla WMI) + API pública **NHTSA vPIC** | Gratis |
| Nº de titulares, tiempo con cada uno, provincia, particular/empresa | **Microdatos MATRABA de la DGT** (Open Data) | Gratis |
| **Golpes / siniestros / km** | NO están en abierto → servicio de pago (carVertical, ITV) | De pago |

La DGT publica en *"DGT en Cifras → Microdatos"* ficheros de **texto de ancho
fijo** de Matriculaciones, Transferencias y Bajas. Encadenando por bastidor la
matriculación + las transferencias ordenadas por fecha se reconstruye el
historial de propietarios — **sin nombres ni DNI** (van anonimizados).

> ⚠️ **Desde el 01/02/2025** la DGT dejó de incluir el bastidor completo en los
> ficheros abiertos. Funciona con datos históricos (hasta ene-2025); para datos
> nuevos hay que pedir acceso a la DGT acreditando interés legítimo.

## Arrancar

```bash
pip install flask
cd bastidor
python app.py          # http://localhost:5000
```

## Cargar el historial de la DGT (opcional pero es la gracia)

1. Descarga los ficheros mensuales de Microdatos de la DGT:
   - Transferencias: <https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-Transferencias-de-Vehiculos-mensual/>
   - Matriculaciones: <https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-Matriculaciones-de-Vehiculos-mensual/>
2. **Ajusta el LAYOUT de ancho fijo** en `dgt_microdatos.py` con el diseño de
   registro oficial en PDF (`MATRICULACIONES_MATRABA.pdf` /
   `TRANSFERENCIAS_MATRABA.pdf`). Las posiciones de la plantilla son
   orientativas. Atajo: el repo `jcaubin/DgtDataFileHelpers` ya tiene layouts.
3. Ingiere:
   ```bash
   python dgt_microdatos.py ingest /ruta/export_*.txt
   python dgt_microdatos.py buscar WBABT31023JP07303
   ```

## Estructura

```
bastidor/
  app.py              # Web Flask (junta las dos fuentes)
  vin.py              # Decode VIN: validación, dígito control, año, NHTSA
  wmi.py              # Tabla WMI local (fabricante + país, offline)
  dgt_microdatos.py   # Ingesta + historial de titulares (Open Data DGT)
  templates/          # index.html, resultado.html
  static/style.css
```

## Legal / RGPD

Los microdatos de la DGT son datos abiertos publicados para su reutilización y
van **anonimizados** (sin nombre ni DNI). No intentes reidentificar titulares.
Para "golpes/km" se necesita un proveedor de pago: ahí el negocio es cobrar al
usuario un poco más de lo que te cuesta el informe (modelo de seisenlinea & co).
