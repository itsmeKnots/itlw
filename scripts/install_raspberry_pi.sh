#!/usr/bin/env bash
# Install the runtime on Raspberry Pi OS Bookworm (64-bit) or later.
set -euo pipefail

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

sudo apt update
sudo apt install -y python3-full python3-venv python3-dev python3-lgpio liblgpio-dev swig i2c-tools libegl1 libgl1 libgl1-mesa-dri
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

# labwc autostart imports the graphical environment and starts these units.
service_dir="$HOME/.config/systemd/user"
autostart_dir="$HOME/.config/labwc"
mkdir -p "$service_dir" "$autostart_dir"

cat > "$service_dir/itlw.service" <<EOF
[Unit]
Description=ITLW Transformer Learning Workbench

[Service]
Type=simple
WorkingDirectory=$project_dir
EnvironmentFile=-$project_dir/.env
Environment=TRANSFORMER_FULLSCREEN=1
ExecStart=$project_dir/.venv/bin/python $project_dir/main.py
Restart=on-failure
RestartSec=5
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

# Poll the public GitHub main branch as this same unprivileged desktop user.
cat > "$service_dir/itlw-update.service" <<EOF
[Unit]
Description=Update ITLW from GitHub main

[Service]
Type=oneshot
WorkingDirectory=$project_dir
ExecStart=$project_dir/scripts/update_from_github.sh
EnvironmentFile=-$project_dir/.env
Environment=XDG_RUNTIME_DIR=%t
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=%t/bus
EOF

cat > "$service_dir/itlw-update.timer" <<'EOF'
[Unit]
Description=Check ITLW for GitHub updates every five minutes

[Timer]
OnActiveSec=2min
OnUnitActiveSec=5min
Unit=itlw-update.service

[Install]
WantedBy=default.target
EOF

chmod 0755 "$project_dir/scripts/update_from_github.sh"
systemctl --user daemon-reload

update_mode=manual
if [[ -f "$project_dir/.env" ]]; then
    configured_mode="$(sed -n 's/^[[:space:]]*ITLW_UPDATE_MODE[[:space:]]*=[[:space:]]*//p' \
        "$project_dir/.env" | tail -n 1 | tr -d "'\"[:space:]")"
    if [[ -n "$configured_mode" ]]; then
        update_mode="$configured_mode"
    fi
fi
case "$update_mode" in
    auto)
        systemctl --user enable --now itlw-update.timer
        ;;
    manual|off)
        systemctl --user disable --now itlw-update.timer
        ;;
    *)
        printf 'Unknown ITLW_UPDATE_MODE=%s; using manual mode.\n' "$update_mode" >&2
        update_mode=manual
        systemctl --user disable --now itlw-update.timer
        ;;
esac

# The helper runs from labwc autostart, after the desktop exports its display.
# Do not enable linger: without a desktop session there is no display for the
# Pygame service to use. Auto mode's timer defers itself until a display exists.

printf '\nGit working tree after installation:\n'
git_status="$(git -C "$project_dir" status --porcelain)"
if [[ -n "$git_status" ]]; then
    printf '%s\n' "$git_status"
    printf 'WARNING: the checkout is not clean; auto-update will refuse to run until resolved.\n' >&2
else
    printf '(clean)\n'
fi

printf '\nInstallation complete. Start the application with:\n'
printf '  bash scripts/run_raspberry_pi.sh\n'
printf 'Watch physical controls in the terminal with:\n'
printf '  bash scripts/watch_hardware.sh\n'
printf 'ADS1115 support for Np/Ns potentiometers is installed and enabled by default.\n'
printf 'Reboot the Pi after installation to activate I2C for the ADS1115.\n'
printf 'The workbench will start automatically when the labwc desktop session opens.\n'
printf 'The five-minute GitHub update timer starts from the same labwc session hook.\n'
