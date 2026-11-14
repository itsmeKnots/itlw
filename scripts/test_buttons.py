#!/usr/bin/env python3
"""Show Raspberry Pi header GPIO levels and diagnose assigned button noise.

Run with the application closed:
    .venv/bin/python scripts/test_buttons.py
    .venv/bin/python scripts/test_buttons.py --noise 30

The tester configures GPIOs as inputs with pull-ups. For assigned signals,
value 1 means pressed (pin LOW) with pull_up=True. The noise check assumes
nothing is pressed and counts physical HIGH/LOW level changes; it never sets
an output. BCM7/8 require dtparam=spi=off; BCM15 requires the serial console
to be disabled. GPIO 2/3 are skipped for the ADS1115 I2C bus; GPIO 0/1 are
reserved for the HAT ID EEPROM when unassigned.
"""
from __future__ import annotations

import sys
import time
import argparse
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
    8: 24, 7: 26, 0: 27, 1: 28, 12: 32, 19: 35, 16: 36,
    20: 38, 21: 40,
}
SKIP_BCM = {0, 1, 2, 3}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--noise", type=float, default=None, metavar="N", nargs="?", const=30.0,
        help="count changes on assigned buttons for N seconds (default: 30 when used)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    buttons = {}
    try:
        app_names = {pin: name for name, pin in cfg.HARDWARE_BUTTON_PINS.items()}
        print("GPIO inputs on the 40-pin header:")
        for bcm_pin, physical_pin in BCM_TO_PHYSICAL.items():
            if bcm_pin in SKIP_BCM and bcm_pin not in app_names:
                reason = "ADS1115 I2C" if bcm_pin in (2, 3) else "HAT ID EEPROM (unassigned)"
                print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2}: skipped ({reason})")
                continue
            name = app_names.get(bcm_pin, "unassigned")
            buttons[bcm_pin] = Button(
                bcm_pin,
                pull_up=True,
                bounce_time=cfg.HARDWARE_DEBOUNCE_SECONDS,
            )
            print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2}: {name}")

        print("\nGPIO levels and button states (Ctrl+C to stop):")
        print("  value 1 means pressed (pin LOW) with pull_up=True.")
        previous = {}
        for bcm_pin, button in buttons.items():
            high = bool(button.value)
            previous[bcm_pin] = high
            physical_pin = BCM_TO_PHYSICAL[bcm_pin]
            name = app_names.get(bcm_pin, "unassigned")
            level = "HIGH" if high else "LOW"
            pressed = "pressed" if button.is_pressed else "released"
            print(f"  BCM {bcm_pin:2} / physical pin {physical_pin:2} ({name}): {level}, {pressed}")

        if args.noise is not None:
            duration = max(0.0, args.noise)
            assigned = {pin: name for pin, name in app_names.items()}
            changes = {pin: 0 for pin in assigned}
            noise_previous = {pin: bool(buttons[pin].value) for pin in assigned}
            print(f"\nNoise check for {duration:g} seconds; leave all buttons unpressed.")
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                for pin in assigned:
                    level = bool(buttons[pin].value)
                    if level != noise_previous[pin]:
                        changes[pin] += 1
                        noise_previous[pin] = level
                time.sleep(0.02)
            print("\nNoise results (sorted by level changes):")
            print("BCM  Physical  Signal          Changes  Status")
            for pin, count in sorted(changes.items(), key=lambda item: (-item[1], item[0])):
                status = "NOISY" if count > 2 else "OK"
                print(f"{pin:3}  {BCM_TO_PHYSICAL[pin]:8}  {assigned[pin]:15} {count:7}  {status}")
            return 0

        while True:
            for bcm_pin, button in buttons.items():
                high = bool(button.value)
                if high != previous[bcm_pin]:
                    previous[bcm_pin] = high
                    physical_pin = BCM_TO_PHYSICAL[bcm_pin]
                    name = app_names.get(bcm_pin, "unassigned")
                    level = "HIGH" if high else "LOW"
                    pressed = "pressed" if button.is_pressed else "released"
                    print(f"BCM {bcm_pin} / physical pin {physical_pin} ({name}) -> {level}, {pressed}", flush=True)
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
