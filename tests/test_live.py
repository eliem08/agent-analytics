"""Live feed: /ingest over real HTTP, live-report over stored days, and the log shipper."""

import contextlib
import io
import json
import os
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from unittest import mock

from agent_analytics import live
from agent_analytics.__main__ import main
from agent_analytics.web import make_server

GPT = '1.2.3.4 - - [18/Nov/2026:10:00:00 +0000] "GET /pricing HTTP/1.1" 200 512 "-" "Mozilla/5.0; GPTBot/1.1"'
CLAUDE = '5.6.7.8 - - [18/Nov/2026:10:00:01 +0000] "GET /docs HTTP/1.1" 404 0 "-" "ClaudeBot/1.0"'
HUMAN = '9.9.9.9 - - [18/Nov/2026:10:00:02 +0000] "GET / HTTP/1.1" 200 900 "-" "Mozilla/5.0 (Windows NT 10.0)"'


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = pathlib.Path(self.tmp.name)
        self.srv = make_server("127.0.0.1", 0, self.data, "sk_live_test")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def post(self, text, key="sk_live_test"):
        req = urllib.request.Request(
            self.url + "/ingest", data=text.encode(), headers={"Authorization": f"Bearer {key}"} if key else {}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_ingest_needs_a_key_and_stores_lines(self):
        self.assertEqual(self.post(GPT, key=None)[0], 401)
        self.assertEqual(self.post(GPT, key="sk_wrong")[0], 401)
        status, res = self.post("\n".join([GPT, CLAUDE, HUMAN, "x" * 20000]))
        self.assertEqual(status, 200)
        self.assertEqual(res, {"accepted": 3, "agent_lines": 2, "dropped": 1})
        _, out = run("live-report", "--store", str(self.data / "agent-analytics-ingest"), "--json")
        rep = json.loads(out)
        self.assertEqual((rep["total_hits"], rep["agent_hits"]), (3, 2))
        usage = json.loads(json.dumps(self.srv.RequestHandlerClass.gate.usage()))
        self.assertIn("ingest", json.dumps(usage))  # metered like any other call

    def test_shipper_sends_a_file_to_the_server(self):
        log = self.data / "access.log"
        log.write_text("\n".join([GPT, HUMAN, CLAUDE]) + "\n", encoding="utf-8")
        sent = live.ship(str(log), self.url, "sk_live_test", once=True, log=lambda *_: None)
        self.assertEqual(sent, 3)
        _, out = run("live-report", "--store", str(self.data / "agent-analytics-ingest"))
        self.assertIn("GPTBot", out)


class StoreAndShipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_days_window_and_retention(self):
        folder = self.dir / "ingest"
        folder.mkdir()
        old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        (folder / f"{old}.log").write_text(CLAUDE + "\n", encoding="utf-8")
        live.append(folder, GPT, retain_days=30)
        self.assertEqual(len(list(live.lines_since(folder, 7))), 1)
        self.assertEqual(len(list(live.lines_since(folder, 30))), 2)
        live.append(folder, HUMAN, retain_days=5)
        self.assertFalse((folder / f"{old}.log").exists())

    def test_follow_rotation_and_retry_after_failure(self):
        log = self.dir / "access.log"
        log.write_text(GPT + "\n", encoding="utf-8")
        batches, calls = [], {"n": 0}

        def post(url, key, text):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.URLError("network down")  # first send fails, nothing may be lost
            batches.append(text.splitlines())
            if len(batches) == 1:  # after the first good send, the log rotates
                os.replace(log, self.dir / "access.log.1")
                log.write_text(CLAUDE + "\n" + HUMAN + "\n", encoding="utf-8")
            return {"accepted": len(text.splitlines())}

        with mock.patch.object(live.time, "sleep"):
            sent = live.ship(
                str(log), "https://aa.example.com", "k", post=post, log=lambda *_: None, stop=lambda: len(batches) >= 2
            )
        self.assertEqual(batches, [[GPT], [CLAUDE, HUMAN]])
        self.assertEqual(sent, 3)

    def test_once_sends_a_last_line_without_newline(self):
        log = self.dir / "b.log"
        log.write_text(GPT + "\n" + CLAUDE, encoding="utf-8")
        got = []

        def post(url, key, text):
            got.append(text)
            return {"accepted": len(text.splitlines())}

        sent = live.ship(str(log), "https://aa.example.com", "k", once=True, post=post)
        self.assertEqual((sent, got), (2, [GPT + "\n" + CLAUDE]))

    def test_ship_refuses_plain_http_and_cli_needs_a_key(self):
        log = self.dir / "a.log"
        log.write_text(GPT + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            live.ship(str(log), "http://aa.example.com", "k", once=True)
        with mock.patch.dict(os.environ, {"AGENT_ANALYTICS_KEY": ""}):
            self.assertEqual(run("ship", str(log), "--url", "https://aa.example.com")[0], 2)


if __name__ == "__main__":
    unittest.main()
