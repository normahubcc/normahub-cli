import json
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from normahub_cli.server import NormaHubGatewayServer


class TestGatewayServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_cache.db"
        self.port = 18099  # Isolated test port
        self.server = NormaHubGatewayServer(port=self.port, cache_db_path=self.db_path)
        self.server.start_background()
        time.sleep(0.4)

    def tearDown(self):
        self.server.stop()
        self.temp_dir.cleanup()

    def test_models_endpoint(self):
        url = f"http://localhost:{self.port}/v1/models"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("data", data)
            model_ids = [m["id"] for m in data["data"]]
            self.assertIn("claude-sonnet-5-5", model_ids)
            self.assertIn("normahub/auto", model_ids)

    def test_cache_stats_endpoint(self):
        url = f"http://localhost:{self.port}/v1/cache/stats"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("total_requests", data)

    def test_ui_index_endpoint(self):
        url = f"http://localhost:{self.port}/ui"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("NormaHub Engine", html)

    def test_ollama_tags_endpoint(self):
        url = f"http://localhost:{self.port}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("models", data)

    def test_video_endpoint_handling(self):
        url = f"http://localhost:{self.port}/v1/videos"
        req = urllib.request.Request(
            url,
            data=json.dumps({"prompt": "Cyberpunk city", "model": "seedance-2.5"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        self.server.upstream_client.post = lambda ep, payload: {"id": "mock_task_789", "status": "pending"}
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["id"], "mock_task_789")

    def test_responses_endpoint_handling(self):
        url = f"http://localhost:{self.port}/v1/responses"
        req = urllib.request.Request(
            url,
            data=json.dumps({"input": "Hello", "model": "gpt-6-sol"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        self.server.upstream_client.post = lambda ep, payload: {"id": "resp_123", "output": ["Hello!"]}
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["id"], "resp_123")


if __name__ == "__main__":
    unittest.main()
