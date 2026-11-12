#!/usr/bin/env bash
# Install the runtime on Raspberry Pi OS Bookworm (64-bit) or later.
set -euo pipefail

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

sudo apt update
sudo apt install -y python3-full python3-venv python3-lgpio swig i2c-tools libegl1 libgl1 libgl1-mesa-dri
# Enable the I2C bus used by the ADS1115. A reboot activates the bus driver.
sudo raspi-config nonint do_i2c 0

# Share Raspberry Pi OS GPIO bindings (lgpio) with the app environment. The
# Debian lgpio package depends on the system liblgpio and cannot be rebuilt
# reliably from PyPI inside an isolated venv.
python3 -m venv --system-site-packages "$project_dir/.venv"
# --system-site-packages may leave this setting unchanged when an existing
# venv is upgraded, so enforce it for both fresh and previously created venvs.
sed -i 's/^include-system-site-packages = false$/include-system-site-packages = true/' \
    "$project_dir/.venv/pyvenv.cfg"
"$project_dir/.venv/bin/python" -m pip install --upgrade pip
"$project_dir/.venv/bin/python" -m pip install -r "$project_dir/requirements.txt"
# Install GPIO buttons and ADS1115 support for two turns potentiometers.
# Missing hardware does not prevent app startup.
"$project_dir/.venv/bin/python" -m pip install -r "$project_dir/requirements-hardware.txt" \
    --no-build-isolation
# Blinka provides the `board` and `busio` modules that the app imports, and
# adafruit-circuitpython-ads1x15 is the ADS1115 driver. The driver is pinned
# below 3 because hardware.py uses the 2.x API (ADS.P0 ... ADS.P3); version 3
# removed those names, which silently disabled the potentiometers. This also
# downgrades the driver if requirements-hardware.txt pulled in a 3.x release.
"$project_dir/.venv/bin/python" -m pip install adafruit-blinka "adafruit-circuitpython-ads1x15<3"
# Fail the install now, with a clear message, if the ADS API the app needs is
# missing (module import, channel constants and AnalogIn).
"$project_dir/.venv/bin/python" -c "
import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
ADS.P0, ADS.P1, ADS.P2, ADS.P3
" || { echo "ADS1115 Python modules failed to import or have an incompatible API" >&2; exit 1; }

# Start the user service only after labwc has provided the graphical display
# variables. A user service enabled at default.target starts too early on boot.
service_dir="$HOME/.config/systemd/user"
autostart_dir="$HOME/.config/labwc"
mkdir -p "$service_dir" "$autostart_dir"

cat > "$service_dir/itlw.service" <<EOF
[Unit]
Description=ITLW Transformer Learning Workbench
After=default.target

[Service]
Type=simple
WorkingDirectory=$project_dir
ExecStart=/bin/bash $project_dir/scripts/run_raspberry_pi.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

session_start="$project_dir/scripts/start_raspberry_pi_session.sh"
autostart_file="$autostart_dir/autostart"
session_marker="# ITLW Transformer Learning Workbench"
if ! grep -Fq "$session_marker" "$autostart_file" 2>/dev/null; then
    {
        printf '\n%s\n' "$session_marker"
        printf 'bash %q\n' "$session_start"
    } >> "$autostart_file"
fi

systemctl --user daemon-reload
systemctl --user enable --now itlw.service

printf '\nInstallation complete. Start the application with:\n'
printf '  bash scripts/run_raspberry_pi.sh\n'
printf 'Watch physical controls in the terminal with:\n'
printf '  bash scripts/watch_hardware.sh\n'
printf 'ADS1115 support for Np/Ns potentiometers is installed and enabled by default.\n'
printf 'Reboot the Pi after installation to activate I2C for the ADS1115.\n'
printf 'The workbench will start automatically when the labwc desktop session opens.\n'