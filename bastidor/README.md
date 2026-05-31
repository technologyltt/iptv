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
2. Ingiere. **No necesitas el PDF de diseño**: el módulo detecta solo las
   columnas de bastidor y fecha (sniffer). Para provincia/tipo de titular puedes
   dar offsets con un JSON (`DGT_LAYOUT=lay.json`).
   ```bash
   python dgt_microdatos.py sniff  /ruta/export_2023.txt    # ver columnas detectadas
   python dgt_microdatos.py ingest /ruta/export_*.txt        # cargar a SQLite
   python dgt_microdatos.py buscar WBABT31023JP07303          # consultar
   python dgt_microdatos.py stats                             # qué hay cargado
   ```
   (El nombre del fichero decide el tipo: *transf* → transferencia, *baja* → baja,
   resto → matriculación.)

## Informe completo de pago (opcional — el negocio)

KM, golpes y siniestros NO son Open Data. Para ofrecerlos integras un proveedor
de pago y cobras al usuario con margen. Variables de entorno:

```bash
export STRIPE_SECRET_KEY=sk_live_...      # pasarela de pago
export INFORME_PRECIO_CENT=1499           # 14,99 € (lo que cobras tú)
export CARVERTICAL_API_URL=https://...    # endpoint del proveedor que contrates
export CARVERTICAL_API_KEY=...            # tu clave
```

Sin estas variables, la web muestra el producto como "no disponible" en vez de
romper. En producción, confirma el pago por **webhook de Stripe** antes de
entregar el informe.

## Estructura

```
bastidor/
  app.py              # Web Flask (junta todo)
  vin.py              # Decode VIN: validación, dígito control, año, NHTSA
  wmi.py              # Tabla WMI local (fabricante + país, offline)
  dgt_microdatos.py   # Sniffer + ingesta + historial de titulares (Open Data DGT)
  providers.py        # Proveedor de pago (carVertical/autoDNA), configurable
  payments.py         # Stripe Checkout (sin dependencias, vía HTTPS)
  calc.py             # Calculadora de potencia fiscal (fórmula oficial)
  templates/          # index, resultado, informe, herramientas, potencia_fiscal
  static/style.css
```

## Legal / RGPD

Los microdatos de la DGT son datos abiertos publicados para su reutilización y
van **anonimizados** (sin nombre ni DNI). No intentes reidentificar titulares.
Para "golpes/km" se necesita un proveedor de pago: ahí el negocio es cobrar al
usuario un poco más de lo que te cuesta el informe (modelo de seisenlinea & co).
