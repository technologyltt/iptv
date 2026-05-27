# 04 · Instalación en Raspberry Pi

## Imagen
- **Raspberry Pi OS Lite 64-bit (Bookworm)** con Imager:
  - Hostname: `vtgpi`
  - SSH habilitado, user `pi` (o el que prefieras)
  - WiFi de casa pre-configurado
- Tarjeta microSD A1 16 GB+

## Primer arranque

```bash
ssh pi@vtgpi.local
sudo apt-get update && sudo apt-get -y upgrade
sudo reboot
```

## Clonar y montar

```bash
git clone <este-repo>.git ~/edc17-vtg
cd ~/edc17-vtg
bash scripts/install.sh
sudo systemctl start edc17-vtg
journalctl -u edc17-vtg -f
```

Abre desde el móvil: **http://vtgpi.local:5000**

## ELM327 Bluetooth (vGate iCar Pro BLE) — ruta recomendada

> El config.yaml por defecto espera `/dev/rfcomm0`. Para BT clásico (SPP).
> Si tu vGate es BLE puro, mejor usar un wrapper como `obdgateway` o seguir
> con SPP que también soporta. La iCar Pro BLE 4.0 expone perfil SPP.

1. Enchufa el ELM327 en el OBD-II del coche y da contacto.
2. En la Pi:
```bash
sudo bluetoothctl
> power on
> agent on
> scan on             # apunta la MAC del OBDII
> pair  XX:XX:XX:XX:XX:XX
> trust XX:XX:XX:XX:XX:XX
> exit
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX 1
ls -l /dev/rfcomm0
```

Si pide PIN, prueba `1234` o `0000`.

Para que `rfcomm bind` sea persistente al boot, crea
`/etc/systemd/system/elm-rfcomm.service`:

```ini
[Unit]
Description=Bind ELM327 to /dev/rfcomm0
After=bluetooth.target
[Service]
Type=oneshot
ExecStart=/usr/bin/rfcomm bind 0 XX:XX:XX:XX:XX:XX 1
RemainAfterExit=true
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now elm-rfcomm
```

## ELM327 USB (alternativa)
Aparece como `/dev/ttyUSB0`. Edita `app/config.yaml` → `port: /dev/ttyUSB0`.
```bash
dmesg | tail
ls /dev/ttyUSB*
```

Para que `rfcomm bind` sea persistente, añade a `/etc/rc.local` antes del `exit 0`:
```
rfcomm bind 0 XX:XX:XX:XX:XX:XX 1
```

## Modo hotspot (sin WiFi en el coche)

Para controlar la Pi desde el móvil sin router:

```bash
sudo nmcli device wifi hotspot ssid VTGPi password "edc17vtg!" ifname wlan0
sudo nmcli connection modify Hotspot connection.autoconnect yes
```
Te conectas con el móvil a la WiFi `VTGPi`, abres `http://10.42.0.1:5000`.

## Auto-shutdown al apagar el contacto (recomendado)

Si alimentas con +12 V permanente, añade un divisor a un GPIO y este script:

```bash
sudo tee /usr/local/bin/ign_watch.py <<'PY'
import RPi.GPIO as GPIO, time, subprocess
PIN = 17  # GPIO conectado al divisor de la IGN
GPIO.setmode(GPIO.BCM); GPIO.setup(PIN, GPIO.IN)
off_since = None
while True:
    if GPIO.input(PIN) == 0:
        off_since = off_since or time.time()
        if time.time() - off_since > 30:
            subprocess.run(["/sbin/poweroff"])
    else:
        off_since = None
    time.sleep(1)
PY
sudo systemctl --no-pager edit --force --full ign-watch.service <<'UNIT'
[Unit]
Description=Ignition watchdog
[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/ign_watch.py
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl enable --now ign-watch
```

## Comprobaciones rápidas

```bash
# Estado del servicio
sudo systemctl status edc17-vtg
# Ver log de borrados de DTC
tail -f ~/edc17-vtg/app/logs/clear.log
# Test rápido OBD
. ~/edc17-vtg/.venv/bin/activate
python -c "import obd; c=obd.OBD(); print(c.is_connected(), c.supported_commands)"
```
