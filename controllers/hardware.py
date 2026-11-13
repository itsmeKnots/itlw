"""Optional Raspberry Pi GPIO and ADS1x15 input controller.

Hardware libraries are imported only while attempting to initialize controls.
Switches connect to GPIO input to GND; internal pull-ups are enabled.
"""
from __future__ import annotations

import logging
import time

import config as cfg

logger = logging.getLogger(__name__)


class HardwareController:
    """Poll navigation buttons and two ADS1115 turns potentiometers."""

    BUTTON_NAMES = tuple(cfg.HARDWARE_BUTTON_PINS)
    KNOB_NAMES = ("pot_np", "pot_ns")

    def __init__(self):
        self.connected = False
        self.status = "Hardware disabled"
        self._gpio = None
        self._ads = None
        self._i2c = None
        self._ads_channels = {}
        self._last = {**{name: False for name in self.BUTTON_NAMES},
                      **{name: None for name in self.KNOB_NAMES}}
        self._last_values = {name: None for name in self.KNOB_NAMES}
        self._last_sample_at = 0.0
        self._i2c_failures = 0
        self._last_error = None

    def _read_channel(self, name, channel):
        """Read one ADS channel, preserving its last good value on bus errors."""
        for attempt in range(3):
            try:
                voltage = channel.voltage
                self._mark_i2c_healthy()
                return voltage
            except OSError as exc:
                if str(exc) != self._last_error:
                    logger.warning("I2C read failed for %s: %s", name, exc)
                    self._last_error = str(exc)
                if attempt < 2:
                    time.sleep(0.05)
        return self._last_values.get(name)

    def _mark_i2c_healthy(self):
        if self.status.startswith("I2C bus unhealthy"):
            self.status = "Hardware connected"
            logger.info("I2C bus recovered")
        self._last_error = None

    def _recover_i2c(self):
        """Recreate the bus and ADS channels after repeated failed samples."""
        if self._i2c is not None:
            try:
                self._i2c.deinit()
            except OSError:
                pass
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn

            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS.ADS1115(self._i2c, address=cfg.ADS_ADDRESS)
            self._ads.gain = cfg.ADS_GAIN
            channels = (ADS.P0, ADS.P1, ADS.P2, ADS.P3)
            self._ads_channels = {
                name: AnalogIn(self._ads, channels[channel])
                for name, channel in cfg.ADS_KNOB_CHANNELS.items()
            }
            self._i2c_failures = 0
            logger.info("I2C bus reopened")
        except (OSError, ImportError) as exc:
            logger.warning("I2C bus reopen failed: %s", exc)
        # Retry recovery only after another set of 10 failed samples.
        self._i2c_failures = 0

    def is_connected(self):
        return self.connected

    def connect(self):
        """Initialize optional Pi GPIO and ADS hardware; report errors, don't crash UI."""
        if not cfg.HARDWARE_ENABLED:
            self.status = "Hardware disabled"
            return False
        try:
            from gpiozero import Button as GPIOButton
            # Raspberry Pi OS Bookworm ships lgpio; select it explicitly so
            # gpiozero does not fall back to the incompatible RPi.GPIO backend
            # on Pi 5 (and so the backend is predictable on supported Pis).
            from gpiozero.pins.lgpio import LGPIOFactory
            from gpiozero import Device

            Device.pin_factory = LGPIOFactory()
            self._gpio = GPIOButton
            self._gpio_buttons = {
                name: GPIOButton(pin, pull_up=True, bounce_time=cfg.HARDWARE_DEBOUNCE_SECONDS)
                for name, pin in cfg.HARDWARE_BUTTON_PINS.items()
            }
            adc_status = ""
            if cfg.ADS_ENABLED:
                try:
                    import board
                    import busio
                    import adafruit_ads1x15.ads1115 as ADS
                    from adafruit_ads1x15.analog_in import AnalogIn

                    self._i2c = busio.I2C(board.SCL, board.SDA)
                    self._ads = ADS.ADS1115(self._i2c, address=cfg.ADS_ADDRESS)
                    self._ads.gain = cfg.ADS_GAIN
                    channels = (ADS.P0, ADS.P1, ADS.P2, ADS.P3)
                    self._ads_channels = {
                        name: AnalogIn(self._ads, channels[channel])
                        for name, channel in cfg.ADS_KNOB_CHANNELS.items()
                    }
                except Exception as exc:
                    adc_status = f"; ADS unavailable: {exc}"
                    logger.warning("ADS initialization failed; GPIO controls remain active: %s", exc)
            self.connected = True
            self.status = f"Hardware connected{adc_status}"
            return True
        except Exception as exc:
            self.close()
            self.status = f"Hardware unavailable: {exc}"
            logger.warning("Hardware initialization failed: %s", exc)
            return False

    def read_inputs(self):
        values = self._last.copy()
        for name in self.BUTTON_NAMES:
            values.setdefault(name, False)
        if not self.connected:
            return values
        for name, button in getattr(self, "_gpio_buttons", {}).items():
            try:
                values[name] = button.is_pressed
            except OSError as exc:
                logger.warning("GPIO input read failed for %s: %s", name, exc)
            if name in ("btn_mode", "btn_reset") and values[name] != self._last.get(name, False):
                if values[name]:
        now = time.monotonic()
        if self._ads_channels and now - self._last_sample_at >= cfg.ADS_SAMPLE_INTERVAL:
            sample_failed = False
            for name, channel in self._ads_channels.items():
                raw_voltage = self._read_channel(name, channel)
                if raw_voltage is None:
                    values[name] = self._last_values[name]
                    sample_failed = True
                    continue
                voltage = max(0.0, min(cfg.ADS_REFERENCE_VOLTAGE, raw_voltage))
                minimum, maximum, step = cfg.HARDWARE_KNOB_RANGES[name]
                raw_value = minimum + voltage / cfg.ADS_REFERENCE_VOLTAGE * (maximum - minimum)
                previous = self._last_values[name]
                # Hysteresis is centred on the last accepted value, so a value
                # holds only while the raw reading stays close to it.
                if previous is not None and abs(raw_value - previous) <= step / 2 + cfg.ADS_DEADBAND[name]:
                    quantized = previous
                else:
                    quantized = round((raw_value - minimum) / step) * step + minimum
                # Snap the last bit of travel to the ends so the knob can always
                # reach the minimum and the maximum.
                if raw_value >= maximum - step / 2:
                    quantized = maximum
                elif raw_value <= minimum + step / 2:
                    quantized = minimum
                values[name] = max(minimum, min(maximum, quantized))
            if sample_failed:
                self._i2c_failures += 1
                self.status = "I2C bus unhealthy"
                if self._i2c_failures >= 10:
                    self._recover_i2c()
            else:
                self._i2c_failures = 0
                self._last_sample_at = now
        for name in self.KNOB_NAMES:
            if values[name] is None:
                values[name] = self._last_values[name]
            else:
                self._last_values[name] = values[name]
        self._last = values.copy()
        return values

    def update(self):
        return self.read_inputs()

    def close(self):
        for button in getattr(self, "_gpio_buttons", {}).values():
            try:
                button.close()
            except Exception:
                pass
        self._gpio_buttons = {}
        self._ads_channels = {}
        self._ads = None
        if self._i2c is not None:
            try:
                self._i2c.deinit()
            except Exception:
                pass
            self._i2c = None
        self.connected = False

    def get_status(self):
        return self.status


def get_hardware_controller():
    controller = HardwareController()
    if cfg.HARDWARE_ENABLED:
        controller.connect()
    return controller
