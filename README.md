<!-- sell-kit:start -->
# Agent Analytics

[![CI](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-analytics/actions/workflows/ci.yml)

> **See which AI agents visit your site, what they read and where they fail.**

**Who it's for:** Growth, SEO and content teams whose traffic is shifting to AI assistants.

**The problem:** AI crawlers and assistant browsers now read your site, but normal analytics lumps them in with bots or misses them entirely.

**What you get:** Feed in your access logs and get every AI agent identified by operator and intent, the pages they fetch, the errors they hit and whether they read llms.txt, from uploaded logs or a live feed your servers stream in.

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

Endpoints: `POST /api/report`, `POST /api/agents`, `POST /api/live-report`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Deploy and sell

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/eliem08/agent-analytics)

`render.yaml` (one click, above) and `fly.toml` (`fly launch --copy-config`) both run the Dockerfile with a persistent `/data` volume and a `/healthz` check.
To sell self-serve, set four variables and point a Stripe webhook at `https://<your-host>/billing/webhook` (events `checkout.session.completed` and `customer.subscription.deleted`):

| Variable | Example |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_PRICES` | `team=price_123,business=price_456` |
| `PUBLIC_URL` | `https://agent-analytics.example.com` |
| `PLAN_QUOTAS` (optional) | `team=10000,business=250000` successful calls per key per month |

Buyers pick a plan on `/pricing`, pay on Stripe Checkout and see their API key once on the success page. Cancelling the subscription revokes the key. A selling server always requires a key.

## Pricing

Monthly plans start with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Starter** | $29 per month | 1 site; Log reports on demand; Live log feed; Agent and intent breakdown |
| **Pro** | $99 per month | 10 sites; Spoofing detection; Error-path and llms.txt reports; JSON export |
| **Business** | $399 per month | Unlimited sites; Hosted API; Priority support |

To start a trial or buy a plan, [request access](https://github.com/eliem08/agent-analytics/issues/new?title=Agent%20Analytics%20trial&labels=sales).

Plan note: every plan runs the same software, and every API key unlocks all of it. Monthly call volumes are
enforced when `PLAN_QUOTAS` is set (see Deploy and sell); seat and agent limits are licence terms the code does
not enforce. Support, SLA and done-for-you items are services.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

- Parses **Combined / Common Log Format** access logs (nginx, Apache, most CDNs)
- Classifies hits against a catalogue of 38 known AI agents with
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

## Live feed

Instead of uploading log files, stream them to the hosted server and report on any recent window:

```bash
# on your web server: follow the access log and send new lines every 5 seconds
AGENT_ANALYTICS_KEY=sk_... agent-analytics ship /var/log/nginx/access.log --url https://aa.example.com
# anywhere: the last 7 days of what was streamed in (also POST /api/live-report)
agent-analytics live-report --days 7
```

- `POST /ingest` takes access-log lines as a plain-text body, with the same API keys, rate limit and monthly
  quota as the rest of the API (one call per batch). It answers with how many lines it accepted and how many came
  from AI agents.
- Lines are kept as received, one file per UTC day, for `INGEST_RETAIN_DAYS` (default 90).
- `ship` behaves like `tail -F`: it follows rotation and truncation and resends a batch after a network failure,
  so nothing is lost. It opens the log only to read, so the web server can still rotate it, on Windows too.
  `--once` sends the current file and stops.
- Any program can post to `/ingest` directly: `curl -H "Authorization: Bearer sk_..." --data-binary @access.log
  https://aa.example.com/ingest`.

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
