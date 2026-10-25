<!-- sell-kit:start -->
# Agent Analytics

[![CI](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml)

> **See which AI agents visit your site, what they read and where they fail.**

**Who it's for:** Growth, SEO and content teams whose traffic is shifting to AI assistants.

**The problem:** AI crawlers and assistant browsers now read your site, but normal analytics lumps them in with bots or misses them entirely.

**What you get:** Feed in your access logs and get every AI agent identified by operator and intent, the pages they fetch, the errors they hit and whether they read llms.txt.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install agent_analytics-0.1.0-py3-none-any.whl
agent-analytics agents
agent-analytics report examples/access.log
agent-analytics report examples/access.log --json
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
agent-analytics-web --port 8000          # then open http://127.0.0.1:8000
agent-analytics-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t agent-analytics . && docker run -p 8000:8000 -e API_KEYS=sk_... -v agent-analytics-data:/data agent-analytics
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `agent-analytics-web usage` prints calls per key for billing.

Endpoints: `POST /api/report`, `POST /api/agents`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Starter** | $29 per month | 1 site; Daily log reports; Agent and intent breakdown |
| **Pro** | $99 per month | 10 sites; Spoofing alerts; Error-path and llms.txt reports; CSV and JSON export |
| **Business** | $399 per month | Unlimited sites; Custom agent signatures; Priority support |

To start a trial or buy a plan, [request access](https://github.com/eliem08/agent-analytics/issues/new?title=Agent%20Analytics%20trial&labels=sales).

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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
