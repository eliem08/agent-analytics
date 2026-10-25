import unittest

from agent_analytics import analyze, classify, parse_line

LOG = [
    '1.1.1.1 - - [24/Oct/2026:10:00:00 +0000] "GET /pricing HTTP/1.1" 200 5120 "-" "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"',
    '1.1.1.1 - - [24/Oct/2026:10:00:01 +0000] "GET /robots.txt HTTP/1.1" 200 120 "-" "Mozilla/5.0 (compatible; GPTBot/1.2)"',
    '2.2.2.2 - - [24/Oct/2026:10:01:00 +0000] "GET /docs/api?x=1 HTTP/1.1" 404 0 "-" "Mozilla/5.0 Claude-User/1.0"',
    '3.3.3.3 - - [24/Oct/2026:10:02:00 +0000] "GET / HTTP/1.1" 200 9000 "-" "Mozilla/5.0 (Windows NT 10.0) Chrome/130"',
    '4.4.4.4 - - [24/Oct/2026:10:03:00 +0000] "GET /llms.txt HTTP/1.1" 200 300 "-" "python-requests/2.32"',
    "garbage line",
]


class Tests(unittest.TestCase):
    def test_parse(self):
        h = parse_line(LOG[0])
        self.assertEqual((h.path, h.status, h.bytes), ("/pricing", 200, 5120))

    def test_classify(self):
        self.assertEqual(classify("x ClaudeBot/1.0"), ("ClaudeBot", "Anthropic", "training"))
        self.assertEqual(classify("python-requests/2")[0], "unknown-automation")
        self.assertIsNone(classify("Mozilla/5.0 Safari"))

    def test_analyze(self):
        r = analyze(LOG)
        self.assertEqual(r["total_hits"], 5)
        self.assertEqual(r["human_hits"], 1)
        self.assertEqual(r["unparsed_lines"], 1)
        names = {a["name"]: a for a in r["agents"]}
        self.assertEqual(names["GPTBot"]["hits"], 2)
        self.assertEqual(names["GPTBot"]["special_files"], {"robots.txt": 1})
        self.assertEqual(names["Claude-User"]["error_paths"], [("/docs/api", 1)])
        self.assertEqual(r["by_intent"]["user"], 1)
        self.assertEqual(r["spoof_suspects"], {})

    def test_one_ip_wearing_several_vendor_bot_names_is_flagged(self):
        spoof = [
            '9.9.9.9 - - [24/Oct/2026:11:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "GPTBot/1.2"',
            '9.9.9.9 - - [24/Oct/2026:11:00:01 +0000] "GET / HTTP/1.1" 200 1 "-" "ClaudeBot/1.0"',
            '9.9.9.9 - - [24/Oct/2026:11:00:02 +0000] "GET / HTTP/1.1" 200 1 "-" "PerplexityBot/1.0"',
        ]
        r = analyze(LOG + spoof)
        self.assertEqual(r["spoof_suspects"], {"9.9.9.9": ["ClaudeBot", "GPTBot", "PerplexityBot"]})


if __name__ == "__main__":
    unittest.main()
