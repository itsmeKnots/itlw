import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

from update_check import UpdateChecker


LOCAL = "a" * 40
REMOTE = "b" * 40


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.buffer = io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.buffer.read()


def payload(sha=REMOTE, message="Test update\nDetails"):
    return {"sha": sha, "commit": {"message": message}}


class UpdateCheckerTests(unittest.TestCase):
    def make_checker(self, opener, *, bad_hash=""):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        bad_file = Path(temp_dir.name) / "bad-commit"
        if bad_hash:
            bad_file.write_text(bad_hash)
        checker = UpdateChecker(
            temp_dir.name,
            opener=opener,
            local_commit_reader=lambda _path: LOCAL,
            bad_commit_file=bad_file,
            interval=3600,
            timeout=0.1,
        )
        return checker

    def finish_check(self, checker):
        checker.start()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            snapshot = checker.get_snapshot()
            if snapshot.state != "checking":
                return snapshot
            time.sleep(0.005)
        self.fail("background check did not finish")

    def test_up_to_date_and_update_available(self):
        checker = self.make_checker(lambda *_a, **_kw: FakeResponse(payload(LOCAL)))
        self.addCleanup(checker.stop)
        self.assertEqual(self.finish_check(checker).state, "up_to_date")

        checker = self.make_checker(lambda *_a, **_kw: FakeResponse(payload()))
        self.addCleanup(checker.stop)
        snapshot = self.finish_check(checker)
        self.assertEqual(snapshot.state, "update_available")
        self.assertEqual(snapshot.local_hash, LOCAL[:7])
        self.assertEqual(snapshot.remote_hash, REMOTE[:7])
        self.assertEqual(snapshot.remote_message, "Test update")

    def test_exact_bad_commit_is_not_offered(self):
        checker = self.make_checker(lambda *_a, **_kw: FakeResponse(payload()), bad_hash=REMOTE)
        self.addCleanup(checker.stop)
        self.assertEqual(self.finish_check(checker).state, "up_to_date")

    def test_offline_rate_limit_malformed_and_timeout_are_quiet(self):
        failures = (
            lambda *_a, **_kw: (_ for _ in ()).throw(URLError("offline")),
            lambda *_a, **_kw: (_ for _ in ()).throw(
                HTTPError("https://api.github.com", 403, "rate limit", {}, io.BytesIO())
            ),
            lambda *_a, **_kw: FakeResponse(b"not-json"),
            lambda *_a, **_kw: (_ for _ in ()).throw(TimeoutError("slow")),
            lambda *_a, **_kw: FakeResponse(payload(), {"X-RateLimit-Remaining": "0"}),
        )
        for opener in failures:
            with self.subTest(opener=opener):
                checker = self.make_checker(opener)
                self.addCleanup(checker.stop)
                self.assertEqual(self.finish_check(checker).state, "offline")


if __name__ == "__main__":
    unittest.main()
