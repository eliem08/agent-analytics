"""Live feed: servers stream access-log lines in; reports run over the last N days.

Storage: one file per UTC day (YYYY-MM-DD.log) in the ingest folder, plain access-log lines exactly as
received, so any day can be re-analysed or handed to another tool. Days older than the retention are deleted
on the next write (INGEST_RETAIN_DAYS, default 90).

Shipping: `ship` follows a log file the way `tail -F` does (new lines, rotation, truncation) and POSTs batches
to the hosted /ingest endpoint with an API key. `--once` sends the file's current contents and stops.
"""

from __future__ import annotations

import os
import pathlib
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

MAX_LINE = 16_384
_lock = threading.Lock()


def _today() -> datetime:
    return datetime.now(timezone.utc)


def append(folder: pathlib.Path, text: str, retain_days: int | None = None) -> int:
    """Store the lines of one ingest request; returns how many were kept. Over-long lines are dropped."""
    lines = [ln for ln in text.splitlines() if ln.strip() and len(ln) <= MAX_LINE]
    if not lines:
        return 0
    retain = retain_days if retain_days is not None else int(os.environ.get("INGEST_RETAIN_DAYS", "90"))
    folder.mkdir(parents=True, exist_ok=True)
    now = _today()
    with _lock:
        with open(folder / f"{now:%Y-%m-%d}.log", "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        cutoff = (now - timedelta(days=retain)).strftime("%Y-%m-%d")
        for old in folder.glob("*.log"):
            if old.stem < cutoff:
                old.unlink(missing_ok=True)
    return len(lines)


def lines_since(folder: pathlib.Path, days: int):
    """Yield stored lines from the last `days` UTC days, oldest first."""
    if not folder.is_dir():
        return
    first = (_today() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    for f in sorted(folder.glob("*.log")):
        if f.stem >= first:
            with open(f, encoding="utf-8", errors="replace") as fh:
                yield from fh


def _post(url: str, key: str, text: str) -> dict:
    import json

    req = urllib.request.Request(
        url.rstrip("/") + "/ingest",
        data=text.encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def ship(
    path: str,
    url: str,
    key: str,
    once: bool = False,
    interval: float = 5.0,
    batch: int = 2000,
    post=_post,
    log=print,
    stop=None,
):
    """Send a log file's lines to the hosted ingest endpoint. Follows the file unless once=True.

    A failed send keeps the batch and retries after the next interval, so a network blip loses nothing.
    stop: optional callable returning True to end the loop (used by tests).
    """
    if not url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise ValueError("--url must be https:// (plain http only for localhost testing)")
    pending: list[str] = []
    sent, offset, ident = 0, 0, None
    while True:
        # The file is opened for each read and closed again: holding it open would stop the web server from
        # rotating its own log on Windows. Rotation shows as a new file identity, copytruncate as a smaller size.
        try:
            st = os.stat(path)
        except FileNotFoundError:
            st = None
        if st is not None:
            if ident is not None and ((st.st_ino, st.st_dev) != ident or st.st_size < offset):
                log("log rotated; following the new file")
                offset = 0
            ident = (st.st_ino, st.st_dev)
            if st.st_size > offset and len(pending) < batch:
                with open(path, "rb") as fh:
                    fh.seek(offset)
                    chunk = fh.read(8 * 1024 * 1024)
                end = chunk.rfind(b"\n") + 1  # only whole lines; a half-written last line waits for next time
                if once and offset + len(chunk) >= st.st_size:
                    end = len(chunk)  # a one-off send takes the file as it is, last line included
                offset += end
                for raw in chunk[:end].decode("utf-8", errors="replace").splitlines():
                    if raw.strip():
                        pending.append(raw)
        while pending:
            part, rest = pending[:batch], pending[batch:]
            try:
                res = post(url, key, "\n".join(part))
            except (urllib.error.URLError, OSError, ValueError) as e:
                log(f"send failed, will retry: {e}")
                if once:
                    raise
                break
            sent += int(res.get("accepted", len(part)))
            pending = rest
        if once and not pending:
            st = os.stat(path)
            if st.st_size <= offset:
                return sent
            continue
        if stop and stop():
            return sent
        time.sleep(interval)
