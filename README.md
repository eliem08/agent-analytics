# agent-analytics

[![CI](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml)

> **Google Analytics for agents** — see which AI agents visit your site and what they want.

Classic analytics drops bots on the floor. But a growing share of your
"visitors" are AI agents: training crawlers, AI search indexers and
user-triggered assistants fetching a page on someone's behalf. That traffic
decides whether you show up in ChatGPT / Claude / Perplexity answers.
`agent-analytics` turns raw access logs into an agent traffic report.

## What the MVP does

- Parses **Combined / Common Log Format** access logs (nginx, Apache, most CDNs)
- Classifies hits against a catalogue of ~25 known AI agents with
  **operator** and **intent** (`training`, `search`, `user` = live assistant fetch)
- Flags unknown automation (`bot`, `agent`, `headless`, `python-requests`, …)
- Reports per agent: hits, top paths, status codes, bytes, first/last seen
- Tracks `robots.txt`, `llms.txt` and sitemap fetches, and 4xx/5xx served to agents
  ("agents are hitting broken pages")
- Text or JSON output

## Quickstart

```bash
pip install -e .
agent-analytics report /var/log/nginx/access.log
agent-analytics report access.log --json > agents.json
agent-analytics agents          # list the signature catalogue
```

## Roadmap

- JS snippet + edge middleware for real-time collection (no log access needed)
- Reverse-DNS / IP-range verification of claimed agents (spoof detection)
- "What agents asked for that you don't have" — 404 demand mining
- Per-agent content recommendations (llms.txt, markdown mirrors, structured data)

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
agent_analytics/core.py       domain logic (pure, importable, fully tested)
agent_analytics/__main__.py   CLI (`agent-analytics ...` / `python -m agent_analytics ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #2).
