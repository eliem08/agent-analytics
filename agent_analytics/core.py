"""Access-log parsing and AI-agent classification."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

__all__ = ["AGENTS", "Hit", "parse_line", "classify", "analyze"]

# (substring in UA, display name, operator, intent)
AGENTS = [
    ("GPTBot", "GPTBot", "OpenAI", "training"),
    ("OAI-SearchBot", "OAI-SearchBot", "OpenAI", "search"),
    ("ChatGPT-User", "ChatGPT-User", "OpenAI", "user"),
    ("ClaudeBot", "ClaudeBot", "Anthropic", "training"),
    ("Claude-SearchBot", "Claude-SearchBot", "Anthropic", "search"),
    ("Claude-User", "Claude-User", "Anthropic", "user"),
    ("anthropic-ai", "anthropic-ai", "Anthropic", "training"),
    ("PerplexityBot", "PerplexityBot", "Perplexity", "search"),
    ("Perplexity-User", "Perplexity-User", "Perplexity", "user"),
    ("Google-Extended", "Google-Extended", "Google", "training"),
    ("GoogleOther", "GoogleOther", "Google", "training"),
    ("Gemini", "Gemini", "Google", "user"),
    ("Applebot-Extended", "Applebot-Extended", "Apple", "training"),
    ("Meta-ExternalAgent", "Meta-ExternalAgent", "Meta", "training"),
    ("Meta-ExternalFetcher", "Meta-ExternalFetcher", "Meta", "user"),
    ("Amazonbot", "Amazonbot", "Amazon", "search"),
    ("Bytespider", "Bytespider", "ByteDance", "training"),
    ("CCBot", "CCBot", "Common Crawl", "training"),
    ("cohere-ai", "cohere-ai", "Cohere", "training"),
    ("MistralAI-User", "MistralAI-User", "Mistral", "user"),
    ("YouBot", "YouBot", "You.com", "search"),
    ("DuckAssistBot", "DuckAssistBot", "DuckDuckGo", "search"),
    ("Diffbot", "Diffbot", "Diffbot", "training"),
    ("FirecrawlAgent", "FirecrawlAgent", "Firecrawl", "user"),
    ("bingbot", "bingbot", "Microsoft", "search"),
]

GENERIC_AUTOMATION = re.compile(
    r"bot|crawl|spider|agent|headless|python-requests|httpx|curl|wget|playwright|puppeteer", re.I
)

LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)[^"]*" '
    r'(?P<status>\d{3}) (?P<bytes>\d+|-)(?: "(?P<ref>[^"]*)" "(?P<ua>[^"]*)")?'
)

SPECIAL_PATHS = {
    "/robots.txt": "robots.txt",
    "/llms.txt": "llms.txt",
    "/llms-full.txt": "llms.txt",
    "/sitemap.xml": "sitemap",
}


@dataclass
class Hit:
    ip: str
    time: str
    method: str
    path: str
    status: int
    bytes: int
    ua: str


def parse_line(line: str) -> Hit | None:
    m = LOG_RE.match(line)
    if not m:
        return None
    b = m.group("bytes")
    return Hit(m["ip"], m["time"], m["method"], m["path"], int(m["status"]), 0 if b == "-" else int(b), m["ua"] or "")


def classify(ua: str) -> tuple[str, str, str] | None:
    """Return (name, operator, intent) for an AI agent UA, ('unknown-automation', '?', '?') for generic bots, else None."""
    low = ua.lower()
    for needle, name, op, intent in AGENTS:
        if needle.lower() in low:
            return name, op, intent
    if GENERIC_AUTOMATION.search(ua):
        return "unknown-automation", "?", "?"
    return None


@dataclass
class AgentStats:
    name: str
    operator: str
    intent: str
    hits: int = 0
    bytes: int = 0
    paths: Counter = field(default_factory=Counter)
    statuses: Counter = field(default_factory=Counter)
    errors: Counter = field(default_factory=Counter)
    special: Counter = field(default_factory=Counter)
    first_seen: str = ""
    last_seen: str = ""

    def to_dict(self, top=10):
        return {
            "name": self.name,
            "operator": self.operator,
            "intent": self.intent,
            "hits": self.hits,
            "bytes": self.bytes,
            "top_paths": self.paths.most_common(top),
            "statuses": dict(self.statuses),
            "error_paths": self.errors.most_common(top),
            "special_files": dict(self.special),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


def analyze(lines) -> dict:
    total = human = unparsed = 0
    agents: dict[str, AgentStats] = {}
    by_intent: Counter = Counter()
    claims: dict[str, set] = {}  # ip -> named agents it claimed to be
    for line in lines:
        hit = parse_line(line.rstrip("\n"))
        if not hit:
            unparsed += 1
            continue
        total += 1
        c = classify(hit.ua)
        if not c:
            human += 1
            continue
        name, op, intent = c
        if name != "unknown-automation":
            claims.setdefault(hit.ip, set()).add(name)
        st = agents.get(name) or agents.setdefault(name, AgentStats(name, op, intent, first_seen=hit.time))
        st.hits += 1
        st.bytes += hit.bytes
        path = hit.path.split("?")[0]
        st.paths[path] += 1
        st.statuses[hit.status] += 1
        if hit.status >= 400:
            st.errors[path] += 1
        if path in SPECIAL_PATHS:
            st.special[SPECIAL_PATHS[path]] += 1
        st.last_seen = hit.time
        by_intent[intent] += 1
    agent_hits = sum(a.hits for a in agents.values())
    return {
        "total_hits": total,
        "human_hits": human,
        "agent_hits": agent_hits,
        "agent_share": agent_hits / total if total else 0.0,
        "unparsed_lines": unparsed,
        "by_intent": dict(by_intent),
        "agents": sorted((a.to_dict() for a in agents.values()), key=lambda d: -d["hits"]),
        # user agents are self-declared; one IP wearing several vendors' bot names is almost certainly spoofing
        "spoof_suspects": {ip: sorted(names) for ip, names in sorted(claims.items()) if len(names) > 1},
    }
