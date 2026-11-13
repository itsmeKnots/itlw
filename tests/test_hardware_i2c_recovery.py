"""Hardware-free regression checks for ADS I2C sampling and recovery."""
import threading
import time
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


class SlowFailingChannel:
    def __init__(self, started):
        self.started = started

    @property
    def voltage(self):
        self.started.set()
        time.sleep(0.2)
        raise OSError(5, "Input/output error")


class HardwareI2CTest(unittest.TestCase):
    def make_controller(self, channel):
        controller = HardwareController()
        controller.connected = True
        controller.status = "Hardware connected"
        controller._ads_channels = {"pot_np": channel}
        return controller

    def test_transient_oserror_retries_then_recovers(self):
        controller = self.make_controller(FlakyChannel(2, 1.65))
        with patch.object(controller._worker_stop, "wait", return_value=False):
            succeeded = controller._sample_once()

        self.assertTrue(succeeded)
        self.assertEqual(controller.read_inputs()["pot_np"], cfg.Np_MAX // 2)
        self.assertEqual(controller.get_status(), "Hardware connected")
        self.assertEqual(controller._ads_channels["pot_np"].failures, 0)
        self.assertEqual(controller._i2c_failures, 0)

    def test_persistent_oserror_keeps_last_good_value_and_marks_unhealthy(self):
        controller = self.make_controller(FlakyChannel(100, 1.65))
        controller._last_values["pot_np"] = 450
        controller._last["pot_np"] = 450
        with patch.object(controller._worker_stop, "wait", return_value=False):
            succeeded = controller._sample_once()

        self.assertFalse(succeeded)
        self.assertEqual(controller.read_inputs()["pot_np"], 450)
        self.assertEqual(controller.get_status(), "I2C bus unhealthy")
        self.assertEqual(controller._i2c_failures, 1)

    def test_ten_failed_cycles_recover_bus(self):
        controller = self.make_controller(FlakyChannel(100, 1.65))
        with patch.object(controller._worker_stop, "wait", return_value=False), \
                patch.object(controller, "_recover_i2c") as recover:
            for _ in range(10):
                controller._sample_once()

        recover.assert_called_once_with()

    def test_read_inputs_does_not_wait_for_slow_i2c_failure(self):
        started = threading.Event()
        controller = self.make_controller(SlowFailingChannel(started))
        controller._start_ads_worker()
        self.addCleanup(controller.close)
        self.assertTrue(started.wait(1.0), "sampling worker did not start")

        started_at = time.perf_counter()
        values = controller.read_inputs()
        elapsed = time.perf_counter() - started_at

        self.assertLess(elapsed, 0.01)
        self.assertIsNone(values["pot_np"])

    def test_worker_backoff_grows_and_resets_after_success(self):
        controller = HardwareController()
        results = iter((False, False, True))
        delays = []

        def sample_once():
            return next(results)

        def wait(delay):
            delays.append(delay)
            if len(delays) == 3:
                controller._worker_stop.set()
                return True
            return False

        controller._sample_once = sample_once
        with patch.object(controller._worker_stop, "wait", side_effect=wait):
            controller._sampling_loop()

        self.assertEqual(delays, [0.5, 1.0, cfg.ADS_SAMPLE_INTERVAL])

    def test_stale_data_exposes_unhealthy_status(self):
        controller = self.make_controller(FlakyChannel(0, 1.65))
        self.assertFalse(controller.data_stale)
        self.assertEqual(controller.get_status(), "Hardware connected")
        controller._last_good_sample_at = time.monotonic() - 1.1

        self.assertTrue(controller.data_stale)
        self.assertEqual(controller.get_status(), "I2C bus unhealthy")

    def test_disabled_controller_does_not_start_worker(self):
        controller = HardwareController()

        controller.close()

        self.assertIsNone(controller._worker)
        self.assertEqual(controller.get_status(), "Hardware disabled")


if __name__ == "__main__":
    unittest.main()
