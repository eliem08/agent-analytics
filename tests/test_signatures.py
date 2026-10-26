import unittest

from agent_analytics.core import AGENTS, classify


class SignatureTests(unittest.TestCase):
    def test_prefix_names_never_swallow_longer_ones(self):
        cases = {
            "Mozilla/5.0 (compatible; Applebot-Extended/0.1)": ("Applebot-Extended", "training"),
            "Mozilla/5.0 (compatible; Applebot/0.1; +http://www.apple.com/go/applebot)": ("Applebot", "search"),
            "cohere-training-data-crawler/1.0": ("cohere-training-data-crawler", "training"),
            "Mozilla/5.0 (compatible) Ai2Bot-Dolma (+https://www.allenai.org/crawler)": ("Ai2Bot-Dolma", "training"),
            "Mozilla/5.0 (compatible; PetalBot;+https://webmaster.petalsearch.com/site/petalbot)": (
                "PetalBot",
                "search",
            ),
        }
        for ua, (name, intent) in cases.items():
            with self.subTest(ua=ua):
                got = classify(ua)
                self.assertEqual((got[0], got[2]), (name, intent))

    def test_every_signature_is_reachable(self):
        for needle, name, _op, _intent in AGENTS:
            with self.subTest(name=name):
                self.assertEqual(classify(f"Mozilla/5.0 (compatible; {needle}/1.0)")[0], name)

    def test_browsers_are_not_agents(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
        self.assertIsNone(classify(ua))


if __name__ == "__main__":
    unittest.main()
