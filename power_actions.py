"""Guarded power and systemd actions with an injectable command runner."""
from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys
from typing import Callable

import config as cfg


class PowerActions:
    def __init__(self, command_runner: Callable | None = None, *,
                 platform_name: str | None = None, hardware_enabled: bool | None = None,
                 model_path: str | Path = "/proc/device-tree/model",
                 cgroup_path: str | Path = "/proc/self/cgroup",
                 logger: logging.Logger | None = None):
        self.command_runner = command_runner or subprocess.run
        self.platform_name = platform_name or sys.platform
        self.hardware_enabled = (cfg.HARDWARE_ENABLED if hardware_enabled is None
                                 else hardware_enabled)
        self.model_path = Path(model_path)
        self.cgroup_path = Path(cgroup_path)
        self.logger = logger or logging.getLogger(__name__)

    def is_raspberry_pi(self) -> bool:
        if not self.platform_name.startswith("linux"):
            return False
        try:
            model = self.model_path.read_bytes().replace(b"\x00", b"").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            return False
        return "raspberry pi" in model.lower()

    def is_itlw_service(self) -> bool:
        try:
            cgroups = self.cgroup_path.read_text(encoding="utf-8")
        except OSError:
            return False
        return any(
            part == "itlw.service"
            for line in cgroups.splitlines()
            for part in line.split("/")
        )

    def availability(self, action: str) -> tuple[bool, str]:
        if action in {"return_to_app", "exit_to_desktop"}:
            return True, ""
        if action == "restart_app":
            if self.is_itlw_service():
                return True, ""
            return False, "Restart app is available only when ITLW runs as itlw.service."
        if action in {"reboot", "poweroff"}:
            if not self.platform_name.startswith("linux"):
                return False, "System power controls are available only on the Raspberry Pi."
            if not self.hardware_enabled:
                return False, "System power controls are disabled because ITLW_HARDWARE=0."
            if not self.is_raspberry_pi():
                return False, "System power controls are disabled on non-Pi computers."
            return True, ""
        return False, "Unknown power action."

    def execute(self, action: str) -> bool:
        """Run an allowed system command; return false for blocked or failed actions."""
        allowed, reason = self.availability(action)
        if not allowed:
            self.logger.warning("Blocked power action %s: %s", action, reason)
            return False
        commands = {
            "restart_app": ["systemctl", "--user", "restart", "--no-block", "itlw.service"],
            "reboot": ["/usr/bin/loginctl", "reboot"],
            "poweroff": ["/usr/bin/loginctl", "poweroff"],
        }
        command = commands.get(action)
        if command is None:
            return action in {"return_to_app", "exit_to_desktop"}
        try:
            self.command_runner(command, check=True, timeout=10)
            return True
        except (OSError, subprocess.SubprocessError):
            self.logger.exception("Power action failed: %s", action)
            return False
