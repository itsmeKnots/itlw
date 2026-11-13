"""Hardware-free regression check for transient ADS I2C errors."""
import unittest
from unittest.mock import patch

import config as cfg
from controllers.hardware import HardwareController


class FlakyChannel:
    def __init__(self, failures, value):
        self.failures = failures
        self.value = value

    @property
    def voltage(self):
        if self.failures:
            self.failures -= 1
            raise OSError(5, "Input/output error")
        return self.value


class HardwareI2CTest(unittest.TestCase):
    def test_transient_oserror_retries_then_recovers(self):
        controller = HardwareController()
        controller.connected = True
        controller.status = "Hardware connected"
        controller._ads_channels = {"pot_np": FlakyChannel(2, 1.65)}
        controller._last_sample_at = 0

        with patch("controllers.hardware.time.sleep"):
            values = controller.read_inputs()

        self.assertEqual(values["pot_np"], cfg.Np_MAX // 2)
        self.assertEqual(controller.get_status(), "Hardware connected")
        self.assertEqual(controller._ads_channels["pot_np"].failures, 0)

    def test_persistent_oserror_returns_safe_default(self):
        controller = HardwareController()
        controller.connected = True
        controller.status = "Hardware connected"
        controller._ads_channels = {"pot_np": FlakyChannel(100, 1.65)}
        controller._last_sample_at = 0

        with patch("controllers.hardware.time.sleep"), patch.object(controller, "_recover_i2c"):
            values = controller.read_inputs()

        self.assertIsNone(values["pot_np"])
        self.assertEqual(controller.get_status(), "I2C bus unhealthy")


if __name__ == "__main__":
    unittest.main()
