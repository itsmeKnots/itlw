#!/usr/bin/env python3
"""Check configured BCM button pins against internal pull-up/down resistors.

Disconnect buttons and other wiring from the pins before running. Stop the app
first so it releases GPIO. Run with: .venv/bin/python scripts/diagnose_gpio_pulls.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    import RPi.GPIO as GPIO
except ImportError as exc:
    print(f"RPi.GPIO is unavailable: {exc}", file=sys.stderr)
    raise SystemExit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config as cfg


SAMPLES = 200
SAMPLE_DELAY = 0.001
SETTLE_DELAY = 0.2


def main() -> int:
    pins = list(dict.fromkeys(cfg.HARDWARE_BUTTON_PINS.values()))
    GPIO.setmode(GPIO.BCM)
    try:
        for mode, label in ((GPIO.PUD_UP, "PULL-UP"), (GPIO.PUD_DOWN, "PULL-DOWN")):
            for pin in pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=mode)
            time.sleep(SETTLE_DELAY)
            print(label)
            for pin in pins:
                highs = 0
                for _ in range(SAMPLES):
                    highs += GPIO.input(pin)
                    time.sleep(SAMPLE_DELAY)
                print(f"  GPIO{pin}: {highs}/{SAMPLES} HIGH")
        return 0
    except Exception as exc:
        print(f"GPIO diagnostic failed: {exc}", file=sys.stderr)
        return 1
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
