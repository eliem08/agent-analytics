import argparse
import csv
import json
import os
import sys

from .core import AGENTS, analyze


def _run(argv=None):
    ap = argparse.ArgumentParser(prog="agent-analytics", description="AI agent traffic report from access logs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("logfile", help="access log path, or - for stdin")
    r.add_argument("--json", action="store_true")
    sub.add_parser("agents")
    a = ap.parse_args(argv)

    if a.cmd == "agents":
        for _, name, op, intent in AGENTS:
            print(f"{name:<22} {op:<14} {intent}")
        return 0

    if a.logfile == "-":
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
