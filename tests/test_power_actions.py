"""Power-action guard tests; every command is captured by a fake runner."""
import tempfile
import unittest
from pathlib import Path

from power_actions import PowerActions


class PowerActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.model = root / "model"
        self.cgroup = root / "cgroup"
        self.model.write_text("Raspberry Pi 4 Model B\0", encoding="utf-8")
        self.cgroup.write_text("0::/user.slice/app.slice/itlw.service\n", encoding="utf-8")
        self.commands = []

        def runner(command, **kwargs):
            self.commands.append((command, kwargs))

        self.runner = runner

    def make_actions(self, **kwargs):
        options = {
            "command_runner": self.runner,
            "platform_name": "linux",
            "hardware_enabled": True,
            "model_path": self.model,
            "cgroup_path": self.cgroup,
        }
        options.update(kwargs)
        return PowerActions(**options)

    def test_os_power_commands_require_linux_enabled_hardware_and_pi(self):
        actions = self.make_actions()
        self.assertEqual(actions.availability("poweroff"), (True, ""))
        self.assertTrue(actions.execute("poweroff"))
        self.assertEqual(self.commands[0][0], ["/usr/bin/loginctl", "poweroff"])

        windows = self.make_actions(platform_name="win32")
        self.assertFalse(windows.availability("reboot")[0])
        disabled = self.make_actions(hardware_enabled=False)
        self.assertIn("ITLW_HARDWARE=0", disabled.availability("reboot")[1])

        self.model.write_text("Generic Linux computer", encoding="utf-8")
        non_pi = self.make_actions()
        self.assertIn("non-Pi", non_pi.availability("poweroff")[1])
        self.assertEqual(len(self.commands), 1)

    def test_restart_is_only_available_in_itlw_user_service(self):
        actions = self.make_actions()
        self.assertEqual(actions.availability("restart_app"), (True, ""))
        self.assertTrue(actions.execute("restart_app"))
        self.assertEqual(
            self.commands[0][0],
            ["systemctl", "--user", "restart", "--no-block", "itlw.service"],
        )

        self.cgroup.write_text("0::/user.slice/app.slice/shell.service\n", encoding="utf-8")
        not_service = self.make_actions()
        self.assertFalse(not_service.availability("restart_app")[0])
        self.assertFalse(not_service.execute("restart_app"))
        self.assertEqual(len(self.commands), 1)

    def test_command_failure_is_reported_without_propagating(self):
        def failing_runner(*_args, **_kwargs):
            raise OSError("not authorized")

        actions = self.make_actions(command_runner=failing_runner)
        self.assertFalse(actions.execute("reboot"))


if __name__ == "__main__":
    unittest.main()
