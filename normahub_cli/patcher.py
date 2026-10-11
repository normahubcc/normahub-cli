"""
IDE auto-configuration for NormaHub.
Configures Cursor, Cline, OpenCode, and Claude Desktop
to use NormaHub's local gateway and Model Context Protocol servers.
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple


class IDEPatcher:
    """Detects installed IDE environments and injects NormaHub settings."""

    @staticmethod
    def get_home() -> Path:
        return Path.home()

    @classmethod
    def patch_cursor(cls, api_key: str, local_port: int = 8000) -> Tuple[bool, str]:
        """Configures Cursor MCP and settings."""
        home = cls.get_home()
        cursor_dir = home / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        mcp_file = cursor_dir / "mcp.json"

        data = {}
        if mcp_file.exists():
            try:
                data = json.loads(mcp_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        mcp_servers = data.setdefault("mcpServers", {})
        mcp_servers["normahub"] = {
            "command": "npx",
            "args": ["-y", "@normahub/mcp-server"],
            "env": {
                "NORMAHUB_API_KEY": api_key,
                "NORMAHUB_BASE_URL": f"http://localhost:{local_port}/v1",
            },
        }

        mcp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True, f"Configured Cursor MCP in: {mcp_file}"

    @classmethod
    def patch_cline(cls, api_key: str, local_port: int = 8000) -> Tuple[bool, str]:
        """Configures VS Code Cline extension settings."""
        home = cls.get_home()
        # Search for possible Cline config locations
        candidates = [
            home / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
            home / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
            home / "AppData" / "Roaming" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
        ]

        target_file = None
        for path in candidates:
            if path.parent.exists():
                target_file = path
                break

        if not target_file:
            # Default to linux/standard path
            target_file = candidates[0]
            target_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if target_file.exists():
            try:
                data = json.loads(target_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        mcp_servers = data.setdefault("mcpServers", {})
        mcp_servers["normahub"] = {
            "command": "npx",
            "args": ["-y", "@normahub/mcp-server"],
            "env": {
                "NORMAHUB_API_KEY": api_key,
                "NORMAHUB_BASE_URL": f"http://localhost:{local_port}/v1",
            },
            "disabled": False,
            "autoApprove": ["normahub_list_models"],
        }

        target_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True, f"Configured Cline MCP in: {target_file}"

    @classmethod
    def patch_claude_desktop(cls, api_key: str, local_port: int = 8000) -> Tuple[bool, str]:
        """Configures Claude Desktop official app."""
        home = cls.get_home()
        candidates = [
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
            home / ".config" / "claude" / "claude_desktop_config.json",
        ]

        target_file = candidates[0] if sys.platform == "darwin" else (candidates[1] if sys.platform == "win32" else candidates[2])
        target_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if target_file.exists():
            try:
                data = json.loads(target_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        mcp_servers = data.setdefault("mcpServers", {})
        mcp_servers["normahub"] = {
            "command": "npx",
            "args": ["-y", "@normahub/mcp-server"],
            "env": {
                "NORMAHUB_API_KEY": api_key,
                "NORMAHUB_BASE_URL": f"http://localhost:{local_port}/v1",
            },
        }

        target_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Also patch Claude Code CLI (~/.claude/settings.json) per official NormaHub guide:
        # Note: Anthropic client automatically appends /v1/messages, so base URL MUST NOT end in /v1!
        claude_cli_file = home / ".claude" / "settings.json"
        claude_cli_file.parent.mkdir(parents=True, exist_ok=True)
        cli_data = {}
        if claude_cli_file.exists():
            try:
                cli_data = json.loads(claude_cli_file.read_text(encoding="utf-8"))
            except Exception:
                cli_data = {}
        env_map = cli_data.setdefault("env", {})
        env_map["ANTHROPIC_BASE_URL"] = f"http://localhost:{local_port}"
        env_map["ANTHROPIC_AUTH_TOKEN"] = api_key or "nr_hub_local"
        env_map["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"
        env_map["CLAUDE_CODE_DISABLE_1M_CONTEXT"] = "1"
        cli_data.setdefault("model", "claude-sonnet-5")
        claude_cli_file.write_text(json.dumps(cli_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return True, f"Configured Claude Desktop & Claude Code in: {target_file} and {claude_cli_file}"

    @classmethod
    def patch_opencode(cls, api_key: str, local_port: int = 8000) -> Tuple[bool, str]:
        """Configures OpenCode assistant conforming to https://normahub.cc/guides/opencode."""
        home = cls.get_home()
        target_file = home / ".config" / "opencode" / "opencode.json"
        target_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if target_file.exists():
            try:
                data = json.loads(target_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        data["$schema"] = "https://opencode.ai/config.json"
        data.setdefault("model", "normahub/gpt-5.6-sol")
        provider = data.setdefault("provider", {})
        provider["normahub"] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": "NormaHub",
            "options": {
                "baseURL": f"http://localhost:{local_port}/v1",
                "apiKey": api_key or "nr_hub_local",
            },
            "models": {
                "gpt-5.6-sol": {
                    "name": "GPT 5.6 Sol",
                    "limit": {"context": 1000000, "output": 1000000},
                },
                "claude-sonnet-5-5": {
                    "name": "Claude Sonnet 5.5",
                    "limit": {"context": 1000000, "output": 1000000},
                },
            },
        }

        target_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True, f"Configured OpenCode endpoint in: {target_file}"

    @classmethod
    def patch_all(cls, api_key: str, local_port: int = 8000) -> List[Tuple[str, bool, str]]:
        """Patches all supported IDEs."""
        results = []
        for name, patch_fn in [
            ("Cursor", cls.patch_cursor),
            ("Cline", cls.patch_cline),
            ("Claude Desktop", cls.patch_claude_desktop),
            ("OpenCode", cls.patch_opencode),
        ]:
            ok, msg = patch_fn(api_key, local_port)
            results.append((name, ok, msg))
        return results
