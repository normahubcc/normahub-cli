"""
Upstream HTTP Client communicating directly with https://api.normahub.cc/v1.
Zero external dependencies (uses standard urllib).
Supports resilient streaming and transient retry logic.
"""

import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Generator, Optional


class NormaHubUpstreamClient:
    """Communicates directly with the cloud gateway."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        self.api_key = api_key or os.getenv("NORMAHUB_API_KEY", "")
        self.base_url = (base_url or os.getenv("NORMAHUB_BASE_URL", "https://api.normahub.cc/v1")).rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NormaHub-CLI-Engine/1.0.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Sends a JSON POST request with automatic retries for transient 502/503/524 errors."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, retries + 1):
            req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                # Retry on transient gateway errors
                if e.code in (502, 503, 504, 524) and attempt < retries:
                    delay = (1.5 ** attempt) + random.uniform(0.1, 0.5)
                    time.sleep(delay)
                    continue

                error_body = e.read().decode("utf-8", errors="ignore")
                try:
                    err_json = json.loads(error_body)
                    msg = err_json.get("error", {}).get("message") or error_body
                except Exception:
                    msg = error_body or str(e)
                raise RuntimeError(f"NormaHub API Error ({e.code}): {msg}") from e
            except urllib.error.URLError as e:
                if attempt < retries:
                    time.sleep(1.0)
                    continue
                raise RuntimeError(f"Network error connecting to NormaHub: {e.reason}") from e

        raise RuntimeError("Request failed after maximum retries.")

    def get(
        self,
        endpoint: str,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Sends a JSON GET request with automatic retries for transient errors."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(1, retries + 1):
            req = urllib.request.Request(url, headers=self._headers(), method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code in (502, 503, 504, 524) and attempt < retries:
                    delay = (1.5 ** attempt) + random.uniform(0.1, 0.5)
                    time.sleep(delay)
                    continue
                error_body = e.read().decode("utf-8", errors="ignore")
                try:
                    err_json = json.loads(error_body)
                    msg = err_json.get("error", {}).get("message") or error_body
                except Exception:
                    msg = error_body or str(e)
                raise RuntimeError(f"NormaHub API Error ({e.code}): {msg}") from e
            except urllib.error.URLError as e:
                if attempt < retries:
                    time.sleep(1.0)
                    continue
                raise RuntimeError(f"Network error connecting to NormaHub: {e.reason}") from e

        raise RuntimeError("Request failed after maximum retries.")

    def stream_chat(
        self,
        payload: Dict[str, Any],
    ) -> Generator[bytes, None, None]:
        """Streams Server-Sent Events (SSE) chunks from upstream."""
        url = f"{self.base_url}/chat/completions"
        payload_copy = dict(payload)
        payload_copy["stream"] = True
        data = json.dumps(payload_copy).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                while chunk := resp.read(1024):
                    yield chunk
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            error_event = f"data: {json.dumps({'error': {'message': err, 'code': e.code}})}\n\n".encode("utf-8")
            yield error_event
            yield b"data: [DONE]\n\n"

    def stream_responses(
        self,
        payload: Dict[str, Any],
    ) -> Generator[bytes, None, None]:
        """Streams Server-Sent Events (SSE) from official POST /v1/responses endpoint."""
        url = f"{self.base_url}/responses"
        payload_copy = dict(payload)
        payload_copy["stream"] = True
        data = json.dumps(payload_copy).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                while chunk := resp.read(1024):
                    yield chunk
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            error_event = f"data: {json.dumps({'error': {'message': err, 'code': e.code}})}\n\n".encode("utf-8")
            yield error_event
            yield b"data: [DONE]\n\n"

    def get_models(self) -> Dict[str, Any]:
        """Fetches dynamic model list from upstream."""
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            # Fallback to local catalog if offline or demo key
            from .models_data import MODELS_CATALOG
            return {
                "object": "list",
                "data": [{"id": m["id"], "object": "model", "owned_by": m["vendor"]} for m in MODELS_CATALOG],
            }

    def check_ping(self) -> Dict[str, Any]:
        """Measure upstream network latency (RTT) and connection status."""
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                data = json.loads(resp.read().decode("utf-8"))
                models_count = len(data.get("data", []))
                return {
                    "status": "connected",
                    "latency_ms": round(elapsed_ms, 2),
                    "base_url": self.base_url,
                    "models_count": models_count,
                }
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return {
                "status": f"HTTP {e.code}",
                "latency_ms": round(elapsed_ms, 2),
                "base_url": self.base_url,
                "error": str(e),
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return {
                "status": "unreachable",
                "latency_ms": round(elapsed_ms, 2),
                "base_url": self.base_url,
                "error": str(e),
            }

    def get_balance(self) -> Dict[str, Any]:
        """Fetches account balance and subscription info."""
        url = f"{self.base_url}/balance"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "balance": None, "currency": "RUB"}
        except Exception as e:
            return {"error": str(e), "balance": None, "currency": "RUB"}
