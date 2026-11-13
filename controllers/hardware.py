"""Optional Raspberry Pi GPIO and ADS1x15 input controller.

Hardware libraries are imported only while attempting to initialize controls.
Switches connect to GPIO input to GND; internal pull-ups are enabled.
"""
from __future__ import annotations

import logging
import threading
import time

import config as cfg

logger = logging.getLogger(__name__)


class HardwareController:
    """Poll navigation buttons and two ADS1115 turns potentiometers."""

    BUTTON_NAMES = tuple(cfg.HARDWARE_BUTTON_PINS)
    KNOB_NAMES = ("pot_np", "pot_ns")

    def __init__(self):
        self._lock = threading.Lock()
        self.connected = False
        self._status = "Hardware disabled"
        self._gpio = None
        self._ads = None
        self._i2c = None
        self._ads_channels = {}
        self._last = {**{name: False for name in self.BUTTON_NAMES},
                      **{name: None for name in self.KNOB_NAMES}}
        self._last_values = {name: None for name in self.KNOB_NAMES}
        self._last_sample_at = 0.0
        self._last_good_sample_at = None
        self._sampling_started_at = None
        self._i2c_failures = 0
        self._last_error = None
        self._worker_stop = threading.Event()
        self._worker = None

    @property
    def status(self):
        with self._lock:
            reference = self._last_good_sample_at or self._sampling_started_at
            stale = (bool(self._ads_channels) and reference is not None and
                     time.monotonic() - reference > 1.0)
            return "I2C bus unhealthy" if stale else self._status

    @status.setter
    def status(self, value):
        with self._lock:
            self._status = value

    @property
    def data_stale(self):
        with self._lock:
            reference = self._last_good_sample_at or self._sampling_started_at
            return (bool(self._ads_channels) and reference is not None and
                    time.monotonic() - reference > 1.0)

    def _read_channel(self, name, channel):
        """Read one ADS channel, preserving its last good value on bus errors."""
        for attempt in range(3):
            try:
                voltage = channel.voltage
                return voltage, True
            except OSError as exc:
                if str(exc) != self._last_error:
                    logger.warning("I2C read failed for %s: %s", name, exc)
                    self._last_error = str(exc)
                if attempt < 2:
                    if self._worker_stop.wait(0.05):
                        break
        with self._lock:
            return self._last_values.get(name), False

    def _mark_i2c_healthy(self):
        with self._lock:
            was_unhealthy = self._status.startswith("I2C bus unhealthy")
            self._status = "Hardware connected"
            self._last_error = None
        if was_unhealthy:
            logger.info("I2C bus recovered")

    def _recover_i2c(self):
        """Recreate the bus and ADS channels after repeated failed samples."""
        with self._lock:
            i2c = self._i2c
        if i2c is not None:
            try:
                i2c.deinit()
            except OSError:
                pass
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn

            new_i2c = busio.I2C(board.SCL, board.SDA)
            new_ads = ADS.ADS1115(new_i2c, address=cfg.ADS_ADDRESS)
            new_ads.gain = cfg.ADS_GAIN
            channels = (ADS.P0, ADS.P1, ADS.P2, ADS.P3)
            new_channels = {
                name: AnalogIn(new_ads, channels[channel])
                for name, channel in cfg.ADS_KNOB_CHANNELS.items()
            }
            with self._lock:
                self._i2c = new_i2c
                self._ads = new_ads
                self._ads_channels = new_channels
                self._i2c_failures = 0
            logger.info("I2C bus reopened")
        except (OSError, ImportError) as exc:
            logger.warning("I2C bus reopen failed: %s", exc)
        # Retry recovery only after another set of 10 failed samples.
        with self._lock:
            self._i2c_failures = 0

    def _start_ads_worker(self):
        with self._lock:
            if not self._ads_channels or (self._worker and self._worker.is_alive()):
                return
            self._worker_stop.clear()
            self._sampling_started_at = time.monotonic()
            self._worker = threading.Thread(
                target=self._sampling_loop, name="itlw-ads-sampler", daemon=True
            )
            worker = self._worker
        worker.start()

    def _sampling_loop(self):
        backoff = 0.5
        while not self._worker_stop.is_set():
            succeeded = self._sample_once()
            if self._worker_stop.is_set():
                break
            if succeeded:
                backoff = 0.5
                delay = cfg.ADS_SAMPLE_INTERVAL
            else:
                delay = backoff
                backoff = min(5.0, backoff * 2)
            if self._worker_stop.wait(delay):
                break

    def _sample_once(self):
        """Sample and cache ADS channels once; intended to run on the worker."""
        with self._lock:
            channels = tuple(self._ads_channels.items())
            last_values = self._last_values.copy()
        if not channels:
            return True

        sampled = {}
        cycle_failed = False
        for name, channel in channels:
            raw_voltage, succeeded = self._read_channel(name, channel)
            if not succeeded:
                cycle_failed = True
                sampled[name] = last_values.get(name)
                continue
            voltage = max(0.0, min(cfg.ADS_REFERENCE_VOLTAGE, raw_voltage))
            minimum, maximum, step = cfg.HARDWARE_KNOB_RANGES[name]
            raw_value = minimum + voltage / cfg.ADS_REFERENCE_VOLTAGE * (maximum - minimum)
            previous = last_values.get(name)
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
            sampled[name] = max(minimum, min(maximum, quantized))
            last_values[name] = sampled[name]

        with self._lock:
            for name, value in sampled.items():
                self._last_values[name] = value
                self._last[name] = value
            if cycle_failed:
                self._i2c_failures += 1
                self._status = "I2C bus unhealthy"
                recover = self._i2c_failures >= 10
            else:
                self._i2c_failures = 0
                self._last_sample_at = time.monotonic()
                self._last_good_sample_at = self._last_sample_at
                recover = False
        if cycle_failed:
            if recover:
                self._recover_i2c()
            return False
        self._mark_i2c_healthy()
        return True

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
            if self._ads_channels:
                self._start_ads_worker()
            return True
        except Exception as exc:
            self.close()
            self.status = f"Hardware unavailable: {exc}"
            logger.warning("Hardware initialization failed: %s", exc)
            return False

    def read_inputs(self):
        button_values = {}
        if self.connected:
            for name, button in getattr(self, "_gpio_buttons", {}).items():
                try:
                    button_values[name] = button.is_pressed
                except OSError as exc:
                    logger.warning("GPIO input read failed for %s: %s", name, exc)
        with self._lock:
            values = self._last.copy()
            values.update(button_values)
        for name in self.KNOB_NAMES:
            if values[name] is None:
                with self._lock:
                    values[name] = self._last_values[name]
        with self._lock:
            self._last.update(button_values)
        return values

    def update(self):
        return self.read_inputs()

    def close(self):
        self.stop()
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
            except OSError:
                pass
            self._i2c = None
        self.connected = False

    def stop(self):
        self._worker_stop.set()
        worker = self._worker
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join()
        self._worker = None

    def get_status(self):
        return self.status


def get_hardware_controller():
    controller = HardwareController()
    if cfg.HARDWARE_ENABLED:
        controller.connect()
    return controller
