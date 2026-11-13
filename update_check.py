"""Background GitHub update checks and user-service update requests.

The checker contacts only the public GitHub commits API. Installing updates is
delegated to the existing systemd updater service; this module never runs Git
update commands or launches the updater script itself.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from typing import Callable
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


GITHUB_API_URL = "https://api.github.com/repos/itsmeKnots/itlw/commits/main"
CHECK_INTERVAL_SECONDS = 60 * 60
REQUEST_TIMEOUT_SECONDS = 5


def update_state_dir() -> Path:
    """Return the per-user state directory, outside the Git checkout."""
    base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))
    return Path(base) / "itlw"


@dataclass(frozen=True)
class UpdateSnapshot:
    state: str
    local_hash: str = ""
    remote_hash: str = ""
    remote_message: str = ""
    checked_at: float | None = None


class UpdateChecker:
    """Check the local checkout against public GitHub without blocking UI."""

    def __init__(
        self,
        repo_dir: str | Path,
        *,
        api_url: str = GITHUB_API_URL,
        interval: float = CHECK_INTERVAL_SECONDS,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        opener: Callable = urlopen,
        local_commit_reader: Callable[[Path], str] | None = None,
        bad_commit_file: str | Path | None = None,
    ):
        self.repo_dir = Path(repo_dir)
        self.api_url = api_url
        self.interval = interval
        self.timeout = timeout
        self.opener = opener
        self.local_commit_reader = local_commit_reader or self._read_local_commit
        self.bad_commit_file = Path(bad_commit_file or update_state_dir() / "bad-commit")
        self._snapshot = UpdateSnapshot("offline")
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _read_local_commit(repo_dir: Path) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip()

    def start(self) -> None:
        """Start the daemon worker and immediately schedule a check."""
        self._stop.clear()
        self.request_check()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run, name="itlw-update-check", daemon=True
            )
            self._thread.start()

    def request_check(self) -> None:
        with self._lock:
            self._snapshot = UpdateSnapshot(
                "checking",
                local_hash=self._snapshot.local_hash,
                remote_hash=self._snapshot.remote_hash,
                remote_message=self._snapshot.remote_message,
                checked_at=self._snapshot.checked_at,
            )
        self._wake.set()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run, name="itlw-update-check", daemon=True
            )
            self._thread.start()

    def get_snapshot(self) -> UpdateSnapshot:
        with self._lock:
            return self._snapshot

    def stop(self, timeout: float = 0.2) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._wake.wait(self.interval):
                pass
            self._wake.clear()
            if self._stop.is_set():
                break
            with self._lock:
                current = self._snapshot
                self._snapshot = UpdateSnapshot(
                    "checking", current.local_hash, current.remote_hash,
                    current.remote_message, current.checked_at,
                )
            self._check_once()

    def _check_once(self) -> None:
        local_hash = ""
        try:
            local_commit = self.local_commit_reader(self.repo_dir)
            local_hash = local_commit[:7]
            api_url = self.api_url
            if api_url == GITHUB_API_URL:
                try:
                    branch = subprocess.run(
                        ["git", "branch", "--show-current"], cwd=self.repo_dir,
                        check=True, capture_output=True, text=True, timeout=2,
                    ).stdout.strip()
                except subprocess.CalledProcessError:
                    # A custom commit reader may be used without a Git checkout.
                    branch = "main"
                if not branch:
                    raise RuntimeError("Cannot check updates from detached HEAD")
                branch_path = quote(branch, safe="/")
                api_url = (
                    "https://api.github.com/repos/itsmeKnots/itlw/commits/"
                    f"{branch_path}"
                )
            request = Request(
                api_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ITLW-Transformer-Workbench",
                },
            )
            with self.opener(request, timeout=self.timeout) as response:
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining == "0":
                    raise RuntimeError("GitHub API rate limit reached")
                payload = json.loads(response.read().decode("utf-8"))

            remote_commit = payload["sha"]
            message = payload["commit"]["message"].splitlines()[0].strip()
            if not isinstance(remote_commit, str) or len(remote_commit) < 7:
                raise ValueError("Invalid commit hash")

            try:
                bad_commit = self.bad_commit_file.read_text(encoding="utf-8").strip()
            except OSError:
                bad_commit = ""
            remote_hash = remote_commit[:7]
            if local_commit == remote_commit or remote_commit == bad_commit:
                state = "up_to_date"
            else:
                state = "update_available"
            snapshot = UpdateSnapshot(
                state, local_hash, remote_hash, message[:160], time.time()
            )
        except HTTPError as exc:
            # Rate-limit and other HTTP failures are intentionally quiet.
            snapshot = UpdateSnapshot("offline", local_hash, checked_at=time.time())
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, RuntimeError):
            snapshot = UpdateSnapshot("offline", local_hash, checked_at=time.time())
        except Exception:
            # A custom opener or unusual response must never take down the UI.
            snapshot = UpdateSnapshot("offline", local_hash, checked_at=time.time())
        with self._lock:
            self._snapshot = snapshot


def read_update_result(*, consume: bool = False, path: str | Path | None = None) -> dict | None:
    """Read the updater's small result file, optionally marking a notice shown."""
    result_path = Path(path or update_state_dir() / "last-update.json")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(result, dict):
        return None
    if consume and result.get("result") in {"updated", "rolled_back"} and not result.get("shown"):
        result["shown"] = True
        try:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=result_path.parent,
                prefix=result_path.name + ".", delete=False,
            ) as handle:
                json.dump(result, handle)
                handle.write("\n")
                temporary = handle.name
            os.replace(temporary, result_path)
        except OSError:
            pass
    return result


class UpdateManager:
    """Coordinate the checker, non-blocking service request, and result notice."""

    def __init__(self, mode: str, repo_dir: str | Path, *, checker: UpdateChecker | None = None,
                 service_starter: Callable[[], None] | None = None,
                 result_file: str | Path | None = None):
        self.mode = mode if mode in {"manual", "auto", "off"} else "manual"
        self.result_file = Path(result_file or update_state_dir() / "last-update.json")
        self.checker = checker or UpdateChecker(repo_dir)
        self.service_starter = service_starter or self._start_service
        self._lock = threading.Lock()
        self._starting_update = False
        self._failure = False
        self._notice: str | None = None
        self._result_mtime = 0.0
        self._local_hash = ""

    @staticmethod
    def _start_service() -> None:
        subprocess.run(
            ["systemctl", "--user", "start", "--no-block", "itlw-update.service"],
            check=True,
            capture_output=True,
            text=True,
            timeout=4,
        )

    def start(self) -> None:
        if self.mode == "manual":
            self.checker.start()
        elif self.mode == "auto":
            threading.Thread(target=self._read_local_version,
                             name="itlw-local-version", daemon=True).start()
        if self.mode != "off":
            self._read_notice(consume=True)

    def _read_local_version(self) -> None:
        try:
            self._local_hash = self.checker.local_commit_reader(self.checker.repo_dir)[:7]
        except Exception:
            self._local_hash = ""

    def stop(self) -> None:
        self.checker.stop()

    def request_check(self) -> None:
        if self.mode == "manual":
            self.checker.request_check()

    def request_update(self) -> bool:
        if self.mode != "manual" or self.state != "update_available":
            return False
        with self._lock:
            if self._starting_update:
                return True
            self._starting_update = True
            self._failure = False

        def start_service() -> None:
            try:
                self.service_starter()
            except Exception as exc:
                logger.exception("Could not start the update service")
                with self._lock:
                    self._starting_update = False
                    self._failure = True
                    reason = str(exc).strip()
                    self._notice = "Could not start update service"
                    if reason:
                        self._notice += f": {reason[:100]}"

        threading.Thread(target=start_service, name="itlw-update-request", daemon=True).start()
        return True

    @property
    def state(self) -> str:
        self.poll_result()
        with self._lock:
            if self._starting_update:
                return "updating"
            if self._failure:
                checker_state = self.checker.get_snapshot().state
                if checker_state == "update_available":
                    self._failure = False
                else:
                    return "failed"
        result = read_update_result(path=self.result_file)
        if result and result.get("result") == "updating":
            return "updating"
        if self.mode == "manual":
            return self.checker.get_snapshot().state
        return "up_to_date"

    @property
    def snapshot(self) -> UpdateSnapshot:
        if self.mode == "manual":
            current = self.checker.get_snapshot()
            return UpdateSnapshot(
                self.state, current.local_hash, current.remote_hash,
                current.remote_message, current.checked_at,
            )
        result = read_update_result(path=self.result_file)
        return UpdateSnapshot(self.state, local_hash=self._local_hash or
                              str((result or {}).get("to_commit") or "")[:7])

    def poll_result(self) -> None:
        if self.mode == "off":
            return
        self._read_notice(consume=True)
        result = read_update_result(path=self.result_file)
        if result and result.get("result") in {"updated", "rolled_back"}:
            try:
                mtime = self.result_file.stat().st_mtime
            except OSError:
                mtime = 0
            with self._lock:
                if mtime != self._result_mtime:
                    self._result_mtime = mtime
                    self._starting_update = False
                    self._failure = result.get("result") == "rolled_back"

    def _read_notice(self, *, consume: bool) -> None:
        result = read_update_result(path=self.result_file)
        if not result:
            return
        if result.get("shown"):
            return
        text = None
        if result.get("result") == "updated":
            text = "Updated successfully"
        elif result.get("result") == "rolled_back":
            text = "Update failed - previous version restored"
        elif result.get("result") == "skipped" and result.get("reason"):
            reason = str(result["reason"]).strip()
            text = f"Update not applied: {reason[:100]}" if reason else None
        elif result.get("result") == "updating":
            return
        if text:
            if consume:
                read_update_result(consume=True, path=self.result_file)
            with self._lock:
                self._notice = text
                self._starting_update = False
                self._failure = result.get("result") == "rolled_back"
                try:
                    self._result_mtime = self.result_file.stat().st_mtime
                except OSError:
                    pass

    def take_notice(self) -> str | None:
        with self._lock:
            notice, self._notice = self._notice, None
            return notice
