import argparse
import csv
import json
import os
import pathlib
import sys

from .core import AGENTS, analyze
from .live import lines_since, ship


def build_parser():
    ap = argparse.ArgumentParser(prog="agent-analytics", description="AI agent traffic report from access logs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("logfile", help="access log path, or - for stdin")
    r.add_argument("--json", action="store_true")
    sub.add_parser("agents")
    lr = sub.add_parser("live-report", help="report over the lines streamed in to the hosted /ingest endpoint")
    lr.add_argument("--days", type=int, default=7, help="how many recent days (UTC) to include")
    lr.add_argument("--store", default="ingest", help="the ingest folder (the hosted server pins its own)")
    lr.add_argument("--json", action="store_true")
    sh = sub.add_parser("ship", help="stream a server's access log to the hosted /ingest endpoint")
    sh.add_argument("logfile")
    sh.add_argument("--url", required=True, help="the hosted agent-analytics address, e.g. https://aa.example.com")
    sh.add_argument("--key", default=os.environ.get("AGENT_ANALYTICS_KEY", ""), help="API key (or AGENT_ANALYTICS_KEY)")
    sh.add_argument("--once", action="store_true", help="send what is in the file now, then stop")
    sh.add_argument("--interval", type=float, default=5.0, help="seconds between sends while following")
    sh.set_defaults(web=False)  # runs on the customer's server, not through the hosted API
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)

    if a.cmd == "agents":
        for _, name, op, intent in AGENTS:
            print(f"{name:<22} {op:<14} {intent}")
        return 0

    if a.cmd == "ship":
        if not a.key:
            raise ValueError("an API key is needed: --key or AGENT_ANALYTICS_KEY")
        print(f"shipping {a.logfile} to {a.url}" + (" (once)" if a.once else ", following; Ctrl+C to stop"))
        try:
            n = ship(a.logfile, a.url, a.key, once=a.once, interval=max(1.0, a.interval))
        except KeyboardInterrupt:
            return 0
        print(f"sent {n:,} lines")
        return 0
    if a.cmd == "live-report":
        if not 1 <= a.days <= 366:
            raise ValueError("--days must be between 1 and 366")
        rep = analyze(lines_since(pathlib.Path(a.store), a.days))
        if not a.json:
            print(f"last {a.days} day(s) of streamed logs")
    elif a.logfile == "-":
        rep = analyze(sys.stdin)
    else:
        with open(a.logfile, encoding="utf-8", errors="replace") as fh:
            rep = analyze(fh)
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(
        f"Total hits {rep['total_hits']:,} | agents {rep['agent_hits']:,} ({rep['agent_share']:.1%}) | humans {rep['human_hits']:,}"
    )
    print("By intent: " + ", ".join(f"{k}={v}" for k, v in rep["by_intent"].items()))
    for ip, names in rep["spoof_suspects"].items():
        print(f"WARNING: {ip} claimed to be {len(names)} different agents ({', '.join(names)}) - likely spoofed")
    print()
    for ag in rep["agents"]:
        print(f"{ag['name']} ({ag['operator']}, {ag['intent']}): {ag['hits']} hits, {ag['bytes'] / 1e3:.1f} KB")
        for path, n in ag["top_paths"][:5]:
            print(f"    {n:>6}  {path}")
        if ag["error_paths"]:
            print("    errors: " + ", ".join(f"{p} x{n}" for p, n in ag["error_paths"][:3]))
        if ag["special_files"]:
            print("    fetched: " + ", ".join(f"{k} x{v}" for k, v in ag["special_files"].items()))
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
