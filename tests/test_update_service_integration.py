import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ui.theme import Theme, init_fonts
from ui.update_ui import UpdateUI
from update_check import UpdateManager, UpdateSnapshot


class AvailableChecker:
    def __init__(self, repo_dir):
        self.repo_dir = Path(repo_dir)
        self.value = UpdateSnapshot("update_available", "oldhash", "newhash", "Test update")

    def start(self):
        pass

    def stop(self):
        pass

    def request_check(self):
        pass

    def get_snapshot(self):
        return self.value

    @staticmethod
    def local_commit_reader(_path):
        return "a" * 40


class UpdateServiceIntegrationTests(unittest.TestCase):
    def run_command(self, args, cwd=None, env=None):
        result = subprocess.run(args, cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            self.fail(f"Command failed ({result.returncode}): {args}\n{result.stdout}")
        return result.stdout.strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bare = self.root / "origin.git"
        self.seed = self.root / "seed"
        self.checkout = self.root / "pi" / "itlw"
        self.stub_dir = self.root / "bin"
        self.home = self.root / "home"
        self.runtime = self.root / "runtime"
        for path in (self.stub_dir, self.home, self.runtime, self.checkout.parent):
            path.mkdir(parents=True, exist_ok=True)
        self.run_command(["git", "init", "--bare", "--initial-branch=main", str(self.bare)])
        self.run_command(["git", "init", "--initial-branch=main", str(self.seed)])
        self.git_config(self.seed)
        (self.seed / "scripts").mkdir()
        (self.seed / "requirements.txt").write_text("pygame==2.6.1\n")
        (self.seed / "requirements-hardware.txt").write_text("gpiozero>=2.0\n")
        (self.seed / "main.py").write_text("APP OK\n")
        (self.seed / ".gitignore").write_text(".venv/\n")
        updater = Path(__file__).resolve().parents[1] / "scripts/update_from_github.sh"
        (self.seed / "scripts/update_from_github.sh").write_text(updater.read_text())
        (self.seed / "scripts/update_from_github.sh").chmod(0o755)
        self.run_command(["git", "add", "."], self.seed)
        self.run_command(["git", "commit", "-m", "initial"], self.seed)
        self.run_command(["git", "remote", "add", "origin", str(self.bare)], self.seed)
        self.run_command(["git", "push", "-u", "origin", "main"], self.seed)
        self.run_command(["git", "clone", "--branch", "main", str(self.bare), str(self.checkout)])
        self.git_config(self.checkout)
        venv_bin = self.checkout / ".venv/bin"
        venv_bin.mkdir(parents=True)
        fake_python = venv_bin / "python"
        fake_python.write_text("#!/bin/sh\nexit 0\n")
        fake_python.chmod(0o755)
        self.state_home = self.home / ".local/state"
        self.result_file = self.state_home / "itlw/last-update.json"
        self.service_process_result = None
        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.state_home),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path={self.runtime}/bus",
            "PATH": str(self.stub_dir) + os.pathsep + os.environ["PATH"],
        })
        self.write_systemctl_stub()
        self.manager = UpdateManager(
            "manual", self.checkout, checker=AvailableChecker(self.checkout),
            service_starter=self.start_update_service, result_file=self.result_file,
        )
        self.manager.start()
        init_fonts()
        self.ui = UpdateUI(Theme(), "manual", self.manager.request_check,
                           self.manager.request_update)

    def tearDown(self):
        self.manager.stop()
        pygame.quit()

    def git_config(self, repo):
        self.run_command(["git", "config", "user.name", "Update Test"], repo)
        self.run_command(["git", "config", "user.email", "update-test@example.invalid"], repo)

    def write_systemctl_stub(self):
        stub = self.stub_dir / "systemctl"
        stub.write_text(
            "#!/bin/bash\n"
            "if [[ \"$2\" == is-active ]] && grep -q '^BROKEN' \"$SIM_REPO/main.py\"; then exit 3; fi\n"
            "exit 0\n"
        )
        stub.chmod(0o755)
        logger = self.stub_dir / "logger"
        logger.write_text("#!/bin/sh\nexit 0\n")
        logger.chmod(0o755)
        self.env["SIM_REPO"] = str(self.checkout)

    def start_update_service(self):
        # The app-facing request remains detached; this test worker emulates
        # the systemd oneshot service and captures its completion diagnostics.
        self.service_process_result = subprocess.run(
            ["bash", str(self.checkout / "scripts/update_from_github.sh")],
            cwd=self.checkout,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def push(self, message, app_text):
        (self.seed / "main.py").write_text(app_text + "\n")
        self.run_command(["git", "add", "main.py"], self.seed)
        self.run_command(["git", "commit", "-m", message], self.seed)
        self.run_command(["git", "push", "origin", "main"], self.seed)

    def wait_for_result(self, expected):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                result = json.loads(self.result_file.read_text())
            except (OSError, ValueError):
                time.sleep(0.02)
                continue
            if result.get("result") == expected:
                return result
            time.sleep(0.02)
        last_state = self.result_file.read_text() if self.result_file.exists() else "(missing)"
        process_output = (self.service_process_result.stdout
                          if self.service_process_result else "(still running)")
        self.fail(f"Updater did not write result {expected}; state={last_state}; "
                  f"updater output={process_output}")

    def wait_for_service_completion(self):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.service_process_result is not None:
                return
            time.sleep(0.02)
        self.fail("simulated systemd updater service did not finish")

    def click_install(self):
        self.service_process_result = None
        surface_size = (1240, 620)
        self.ui.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u),
            UpdateSnapshot("update_available"), surface_size,
        )
        self.ui.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
            UpdateSnapshot("update_available"), surface_size,
        )

    def test_install_and_rollback_result_messages(self):
        self.push("good update", "APP UPDATED")
        self.click_install()
        self.assertEqual(self.manager.state, "updating")
        updated = self.wait_for_result("updated")
        self.assertTrue(updated["from_commit"])
        self.assertTrue(updated["to_commit"])
        self.assertTrue(updated["timestamp"])
        self.manager.poll_result()
        self.ui.show_notice(self.manager.take_notice())
        self.assertEqual(self.ui.notice, "Updated successfully")
        self.wait_for_service_completion()
        self.start_update_service()
        self.assertEqual(
            json.loads(self.result_file.read_text())["result"], "no_change"
        )

        self.push("broken update", "BROKEN startup")
        self.click_install()
        rolled_back = self.wait_for_result("rolled_back")
        self.assertIn("systemctl", rolled_back["reason"])
        self.assertEqual(
            (self.state_home / "itlw/bad-commit").read_text().strip(),
            rolled_back["to_commit"],
        )
        self.assertEqual(
            self.run_command(["git", "rev-parse", "HEAD"], self.checkout),
            rolled_back["from_commit"],
        )
        self.manager.checker.value = UpdateSnapshot("up_to_date", "oldhash", "newhash")
        self.manager.poll_result()
        self.assertEqual(self.manager.state, "failed")
        self.ui.show_notice(self.manager.take_notice())
        self.assertEqual(self.ui.notice, "Update failed - previous version restored")
        self.wait_for_service_completion()
        self.start_update_service()
        self.assertEqual(
            json.loads(self.result_file.read_text())["result"], "skipped"
        )


if __name__ == "__main__":
    unittest.main()
