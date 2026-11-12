#!/usr/bin/env bash
# Live terminal monitor for the configured physical buttons and ADS1115 knobs.
set -euo pipefail

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python_bin="$project_dir/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
    echo "Virtual environment not found. Run: bash scripts/install_raspberry_pi.sh" >&2
    exit 1
fi

cd "$project_dir"
exec "$python_bin" -u - <<'PY'
import sys
import time

try:
    import board
    import busio
    from gpiozero import Button
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError as exc:
    print(f"Hardware dependencies are missing: {exc}", file=sys.stderr)
    print("Run: bash scripts/install_raspberry_pi.sh", file=sys.stderr)
    raise SystemExit(1)

import config as cfg

buttons = {}
i2c = None
ads = None
channels = {}

try:
    for name, pin in cfg.HARDWARE_BUTTON_PINS.items():
        buttons[name] = Button(
            pin,
            pull_up=True,
            bounce_time=cfg.HARDWARE_DEBOUNCE_SECONDS,
        )

    if cfg.ADS_ENABLED:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=cfg.ADS_ADDRESS)
        ads.gain = cfg.ADS_GAIN
        pins = (ADS.P0, ADS.P1, ADS.P2, ADS.P3)
        channels = {
            name: AnalogIn(ads, pins[channel])
            for name, channel in cfg.ADS_KNOB_CHANNELS.items()
        }

    print("Live hardware monitor (Ctrl+C to stop)")
    print("Buttons are active-low with internal pull-ups; knobs show ADS voltage.")
    while True:
        button_state = "  ".join(
            f"{name}={'PRESSED' if button.is_pressed else 'released'}"
            for name, button in buttons.items()
        )
        knob_state = "  ".join(
            f"{name}={channel.voltage:.3f} V"
            for name, channel in channels.items()
        ) or "ADS knobs disabled"
        print(f"\r{button_state}  |  {knob_state}   ", end="", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nMonitor stopped.")
except Exception as exc:
    print(f"\nHardware monitor error: {exc}", file=sys.stderr)
    raise SystemExit(1)
finally:
    for button in buttons.values():
        button.close()
    if i2c is not None:
        i2c.deinit()
PY
