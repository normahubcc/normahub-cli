import json
import tempfile
import unittest
from pathlib import Path
from normahub_cli.patcher import IDEPatcher


class TestIDEPatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_home = Path(self.temp_dir.name)
        IDEPatcher.get_home = lambda: self.mock_home

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_patch_cursor(self):
        ok, msg = IDEPatcher.patch_cursor("nr_hub_test_123", local_port=8000)
        self.assertTrue(ok)
        mcp_path = self.mock_home / ".cursor" / "mcp.json"
        self.assertTrue(mcp_path.exists())
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        self.assertIn("normahub", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["normahub"]["env"]["NORMAHUB_API_KEY"], "nr_hub_test_123")

    def test_patch_claude(self):
        ok, msg = IDEPatcher.patch_claude_desktop("nr_hub_claude_key", local_port=8000)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
