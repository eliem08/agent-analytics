"""Hosted endpoint for the live feed: POST /ingest with access-log lines as the body (text/plain).

Uses the same API keys, rate limit and monthly quota as the rest of the API (one call per batch).
Lines are stored for the `live-report` command; see live.py.
"""

from __future__ import annotations

import json
import time

from .core import classify, parse_line
from .live import append

INGEST_DIR = "agent-analytics-ingest"  # the folder `live-report --store` is pinned to on the server


def ingest(handler, body: bytes):
    caller = handler.api_caller("ingest")
    if caller is None:
        return None
    started = time.monotonic()
    text = body.decode("utf-8", errors="replace")
    kept = append(handler.data_dir / INGEST_DIR, text)
    agents = 0
    for line in text.splitlines():
        hit = parse_line(line)
        if hit and classify(hit.ua):
            agents += 1
    handler.gate.record(caller, "ingest", 200, int((time.monotonic() - started) * 1000))
    out = {
        "accepted": kept,
        "agent_lines": agents,
        "dropped": len([ln for ln in text.splitlines() if ln.strip()]) - kept,
    }
    return 200, "application/json; charset=utf-8", json.dumps(out).encode()


ROUTES = {"/ingest": ingest}
