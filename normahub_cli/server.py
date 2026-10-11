"""
Unified Local HTTP Gateway Server for NormaHub.
Provides dual OpenAI and Ollama API emulation, local SQLite caching,
Pareto routing, and serves the embedded Model Arena Web UI.

Zero external dependencies (uses standard library ThreadingHTTPServer).
"""

import http.server
import json
import mimetypes
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from .cache import LocalCacheManager
from .client import NormaHubUpstreamClient
from .models_data import MODELS_CATALOG
from .router import ParetoRouter

UI_DIR = Path(__file__).parent / "ui"


class NormaHubHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Handles OpenAI, Ollama, and Web UI requests."""

    cache_manager: LocalCacheManager
    upstream_client: NormaHubUpstreamClient

    def log_message(self, format: str, *args: Any) -> None:
        # Clean logging format
        print(f"[NormaHub Gateway] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _send_json(self, status_code: int, data: Any, extra_headers: Optional[Dict[str, str]] = None) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    # ---------------- GET ROUTING ----------------
    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/ui")
            self.end_headers()
            return

        # Serve Web UI
        if path == "/ui" or path.startswith("/ui/"):
            self._serve_ui(path)
            return

        # OpenAI Models List
        if path == "/v1/models":
            self._handle_get_models()
            return

        # Ollama Tags List
        if path == "/api/tags":
            self._handle_ollama_tags()
            return

        # Cache Stats
        if path == "/v1/cache/stats":
            stats = self.cache_manager.get_stats()
            self._send_json(200, stats)
            return

        # Video Task Polling: /v1/videos/status/{id} (official) or /v1/videos/tasks/{id} (legacy)
        if path.startswith("/v1/videos/status/") or path.startswith("/v1/videos/tasks/"):
            task_id = path.split("/")[-1]
            try:
                try:
                    res = self.upstream_client.get(f"videos/status/{task_id}")
                except Exception:
                    res = self.upstream_client.get(f"videos/tasks/{task_id}")
                self._send_json(200, res)
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    # ---------------- POST ROUTING ----------------
    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_json_body()

        # 1. OpenAI Chat Completions: /v1/chat/completions
        if path == "/v1/chat/completions":
            self._handle_chat_completions(body)
            return

        # 2. Ollama Chat: /api/chat
        if path == "/api/chat":
            self._handle_ollama_chat(body)
            return

        # 3. Ollama Generate: /api/generate
        if path == "/api/generate":
            self._handle_ollama_generate(body)
            return

        # 4. Video Generations: /v1/videos (official) or /v1/videos/generations
        if path in ("/v1/videos", "/v1/videos/generations"):
            try:
                try:
                    res = self.upstream_client.post("videos", payload=body)
                except Exception:
                    res = self.upstream_client.post("videos/generations", payload=body)
                self._send_json(200, res)
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        # 5. Responses API: /v1/responses (official NormaHub SSE streaming route)
        if path == "/v1/responses":
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self._send_cors_headers()
                self.end_headers()
                for chunk in self.upstream_client.stream_responses(body):
                    self.wfile.write(chunk)
                    self.wfile.flush()
                return
            try:
                res = self.upstream_client.post("responses", payload=body)
                self._send_json(200, res)
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        # 5. Clear Cache
        if path == "/v1/cache/clear":
            cleared = self.cache_manager.clear()
            self._send_json(200, {"status": "ok", "cleared_entries": cleared})
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    # ---------------- HANDLERS ----------------
    def _serve_ui(self, path: str) -> None:
        rel_path = path[len("/ui"):].lstrip("/") or "index.html"
        target_file = (UI_DIR / rel_path).resolve()

        if not target_file.is_relative_to(UI_DIR) or not target_file.exists():
            target_file = UI_DIR / "index.html"

        mime_type, _ = mimetypes.guess_type(str(target_file))
        mime_type = mime_type or "application/octet-stream"

        content = target_file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_get_models(self) -> None:
        data = [
            {"id": m["id"], "object": "model", "owned_by": m["vendor"], "pricing_1m_in": m["input_price_1m"]}
            for m in MODELS_CATALOG
        ]
        # Include virtual alias models
        data.extend([
            {"id": "normahub/auto", "object": "model", "owned_by": "NormaHub-Pareto-Router"},
            {"id": "normahub/fast", "object": "model", "owned_by": "NormaHub-Pareto-Router"},
            {"id": "normahub/reasoning", "object": "model", "owned_by": "NormaHub-Pareto-Router"},
        ])
        self._send_json(200, {"object": "list", "data": data})

    def _handle_ollama_tags(self) -> None:
        models = [
            {
                "name": m["id"],
                "model": m["id"],
                "modified_at": "2026-10-11T00:00:00Z",
                "size": 4_000_000_000,
                "digest": "sha256:normahub",
                "details": {"format": "gguf", "family": m["vendor"].lower(), "parameter_size": "70B"},
            }
            for m in MODELS_CATALOG if "image" not in m["id"] and "video" not in m["id"]
        ]
        self._send_json(200, {"models": models})

    def _handle_chat_completions(self, body: Dict[str, Any]) -> None:
        raw_model = body.get("model", "normahub/auto")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        temperature = body.get("temperature", 0.7)

        # 1. Resolve model via Pareto Router
        target_model, rationale = ParetoRouter.resolve_model(raw_model, messages)

        # 2. Check Local Cache (if not streaming)
        cache_key = self.cache_manager.generate_cache_key(target_model, messages, temperature)
        if not stream:
            cached_resp = self.cache_manager.get(cache_key)
            if cached_resp:
                self._send_json(200, cached_resp, extra_headers={"X-NormaHub-Cache": "HIT", "X-NormaHub-Router": rationale})
                return

        # 3. Handle Streaming
        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-NormaHub-Cache", "MISS")
            self.send_header("X-NormaHub-Router", rationale)
            self._send_cors_headers()
            self.end_headers()

            body_with_resolved = dict(body)
            body_with_resolved["model"] = target_model
            for chunk in self.upstream_client.stream_chat(body_with_resolved):
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
            return

        # 4. Handle Non-Streaming (Request upstream & store in cache)
        body_with_resolved = dict(body)
        body_with_resolved["model"] = target_model
        try:
            upstream_resp = self.upstream_client.post("chat/completions", payload=body_with_resolved)
            # Save to SQLite Cache
            self.cache_manager.set(cache_key, target_model, messages, upstream_resp)
            self._send_json(200, upstream_resp, extra_headers={"X-NormaHub-Cache": "MISS", "X-NormaHub-Router": rationale})
        except Exception as e:
            self._send_json(500, {"error": {"message": str(e)}})

    def _handle_ollama_chat(self, body: Dict[str, Any]) -> None:
        model = body.get("model", "claude-sonnet-5-5")
        ollama_messages = body.get("messages", [])
        stream = body.get("stream", False)

        openai_payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": stream,
        }

        if stream:
            # Simple streaming adapter
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self._send_cors_headers()
            self.end_headers()

            for chunk in self.upstream_client.stream_chat(openai_payload):
                text_chunk = chunk.decode("utf-8", errors="ignore")
                for line in text_chunk.split("\n"):
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        try:
                            d = json.loads(line[6:])
                            delta = d["choices"][0].get("delta", {}).get("content", "")
                            ollama_line = json.dumps({
                                "model": model,
                                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "message": {"role": "assistant", "content": delta},
                                "done": False,
                            }) + "\n"
                            self.wfile.write(ollama_line.encode("utf-8"))
                            self.wfile.flush()
                        except Exception:
                            pass
            self.wfile.write(json.dumps({"model": model, "done": True}).encode("utf-8") + b"\n")
            return

        resp = self.upstream_client.post("chat/completions", payload=openai_payload)
        content = resp["choices"][0]["message"]["content"]
        ollama_resp = {
            "model": model,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "message": {"role": "assistant", "content": content},
            "done": True,
            "total_duration": 400_000_000,
        }
        self._send_json(200, ollama_resp)

    def _handle_ollama_generate(self, body: Dict[str, Any]) -> None:
        prompt = body.get("prompt", "")
        body["messages"] = [{"role": "user", "content": prompt}]
        self._handle_ollama_chat(body)


class NormaHubGatewayServer:
    """Manages the lifecycle of the local gateway server."""

    def __init__(
        self,
        port: int = 8000,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache_db_path: Optional[Path] = None,
    ):
        self.port = port
        self.cache_manager = LocalCacheManager(db_path=cache_db_path)
        self.upstream_client = NormaHubUpstreamClient(api_key=api_key, base_url=base_url)
        self.httpd: Optional[http.server.ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        NormaHubHTTPHandler.cache_manager = self.cache_manager
        NormaHubHTTPHandler.upstream_client = self.upstream_client

        self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", self.port), NormaHubHTTPHandler)
        print(f"NormaHub Gateway running on: http://localhost:{self.port}")
        print(f"Local Web UI:                 http://localhost:{self.port}/ui")
        print(f"Cache database:               {self.cache_manager.db_path}")

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def start_background(self) -> None:
        self.thread = threading.Thread(target=self.start, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("\n[-] Gateway stopped.")
