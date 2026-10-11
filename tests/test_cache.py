import tempfile
import unittest
from pathlib import Path
from normahub_cli.cache import LocalCacheManager


class TestLocalCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_cache.db"
        self.cache = LocalCacheManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cache_miss_and_set(self):
        key = self.cache.generate_cache_key("claude-sonnet-5-5", [{"role": "user", "content": "Hello"}])
        self.assertIsNone(self.cache.get(key))

        mock_resp = {
            "id": "chatcmpl-123",
            "choices": [{"message": {"role": "assistant", "content": "Hi there!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        self.cache.set(key, "claude-sonnet-5-5", [{"role": "user", "content": "Hello"}], mock_resp)

        # Cache HIT
        cached = self.cache.get(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["id"], "chatcmpl-123")
        self.assertEqual(cached["choices"][0]["message"]["content"], "Hi there!")

    def test_metrics_savings(self):
        key = self.cache.generate_cache_key("gpt-6-sol", [{"role": "user", "content": "Repeat prompt"}])
        mock_resp = {
            "id": "c1",
            "choices": [{"message": {"role": "assistant", "content": "Reply"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        }
        self.cache.set(key, "gpt-6-sol", [{"role": "user", "content": "Repeat prompt"}], mock_resp)

        # Trigger 2 hits
        self.cache.get(key)
        self.cache.get(key)

        stats = self.cache.get_stats()
        self.assertEqual(stats["cache_hits"], 2)
        self.assertEqual(stats["tokens_saved"], 600)
        self.assertGreater(stats["rubles_saved"], 0.0)


if __name__ == "__main__":
    unittest.main()
