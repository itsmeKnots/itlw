#!/usr/bin/env python3
"""Show Raspberry Pi header GPIO pins and report raw HIGH/LOW levels.

Run with the application closed:
    .venv/bin/python scripts/test_buttons.py

The tester configures available GPIOs as inputs with pull-ups and reports
their electrical logic level. A low unconnected pin is not evidence of a
pressed button; board defaults, alternate functions, or attached circuitry can
affect the reading. GPIO 2/3 are skipped for the ADS1115 I2C bus; GPIO 0/1 are
reserved for the HAT ID EEPROM.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from gpiozero import Button
except ImportError as exc:
    print(f"gpiozero is missing: {exc}", file=sys.stderr)
    print("Install the hardware requirements first:", file=sys.stderr)
    print("  .venv/bin/pip install -r requirements-hardware.txt", file=sys.stderr)
    raise SystemExit(1)

import config as cfg


# Raspberry Pi 4 header GPIOs: BCM number -> physical header pin.
BCM_TO_PHYSICAL = {
    2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13,
    22: 15, 23: 16, 24: 18, 10: 19, 9: 21, 25: 22, 11: 23,
    8: 24, 7: 26, 0: 27, 1: 28, 5: 29, 6: 31, 12: 32,
    13: 33, 19: 35, 16: 36, 26: 37, 20: 38, 21: 40,
}
SKIP_BCM = {0, 1, 2, 3}


def main() -> int:
    buttons = {}
    try:
        app_names = {pin: name for name, pin in cfg.HARDWARE_BUTTON_PINS.items()}
        print("GPIO inputs on the 40-pin header:")
        for bcm_pin, physical_pin in BCM_TO_PHYSICAL.items():
            if bcm_pin in SKIP_BCM:
                reason = "ADS1115 I2C" if bcm_pin in (2, 3) else "HAT ID EEPROM"
                print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2}: skipped ({reason})")
                continue
            name = app_names.get(bcm_pin, "unassigned")
            buttons[bcm_pin] = Button(
                bcm_pin,
                pull_up=True,
                bounce_time=cfg.HARDWARE_DEBOUNCE_SECONDS,
            )
            print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2}: {name}")

        print("\nRaw GPIO levels (unconnected pins may read LOW; Ctrl+C to stop):")
        previous = {}
        for bcm_pin, button in buttons.items():
            high = bool(button.value)
            previous[bcm_pin] = high
            physical_pin = BCM_TO_PHYSICAL[bcm_pin]
            name = app_names.get(bcm_pin, "unassigned")
            level = "HIGH (1)" if high else "LOW (0)"
            print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2} ({name}): {level}")

        while True:
            for bcm_pin, button in buttons.items():
                high = bool(button.value)
                if high != previous[bcm_pin]:
                    previous[bcm_pin] = high
                    physical_pin = BCM_TO_PHYSICAL[bcm_pin]
                    name = app_names.get(bcm_pin, "unassigned")
                    level = "HIGH (1)" if high else "LOW (0)"
                    print(f"BCM {bcm_pin} / physical pin {physical_pin} ({name}) -> {level}", flush=True)
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nGPIO test stopped.")
    except Exception as exc:
        print(f"\nGPIO test error: {exc}", file=sys.stderr)
        return 1
    finally:
        for button in buttons.values():
            button.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
