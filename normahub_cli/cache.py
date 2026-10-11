"""
Local SQLite Semantic & Exact-Match Cache Engine for NormaHub CLI.
Eliminates repeat costs and provides 0ms responses for test runs and repetitive prompts.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .models_data import MODELS_BY_ID, USD_TO_RUB_RATE

DEFAULT_CACHE_DIR = Path.home() / ".normahub"
DEFAULT_DB_PATH = DEFAULT_CACHE_DIR / "cache.db"


class LocalCacheManager:
    """Manages SQLite cache for prompt-response pairs and FinOps savings metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    prompt_text TEXT,
                    response_json TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    estimated_rub_cost REAL DEFAULT 0.0,
                    created_at INTEGER NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_requests INTEGER DEFAULT 0,
                    cache_hits INTEGER DEFAULT 0,
                    tokens_saved INTEGER DEFAULT 0,
                    rubles_saved REAL DEFAULT 0.0,
                    updated_at INTEGER NOT NULL
                )
            """)
            # Initialize metrics row if absent
            conn.execute("""
                INSERT OR IGNORE INTO metrics (id, total_requests, cache_hits, tokens_saved, rubles_saved, updated_at)
                VALUES (1, 0, 0, 0, 0.0, ?)
            """, (int(time.time()),))
            conn.commit()

    @staticmethod
    def generate_cache_key(model: str, messages: list, temperature: float = 0.7) -> str:
        """Generates deterministic hash key based on messages content and model."""
        content_repr = json.dumps({"m": model, "msgs": messages, "t": round(temperature, 2)}, sort_keys=True)
        return hashlib.sha256(content_repr.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Look up response from cache. Updates hit statistics if found."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT response_json, model, prompt_tokens, completion_tokens, estimated_rub_cost FROM cache_entries WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if not row:
                # Update total request count
                conn.execute("UPDATE metrics SET total_requests = total_requests + 1, updated_at = ? WHERE id = 1", (int(time.time()),))
                conn.commit()
                return None

            # Update cache entry stats
            now = int(time.time())
            conn.execute(
                "UPDATE cache_entries SET hit_count = hit_count + 1, last_accessed = ? WHERE cache_key = ?",
                (now, cache_key),
            )

            # Update savings metrics
            tokens = (row["prompt_tokens"] or 0) + (row["completion_tokens"] or 0)
            rub = row["estimated_rub_cost"] or 0.0
            conn.execute("""
                UPDATE metrics
                SET total_requests = total_requests + 1,
                    cache_hits = cache_hits + 1,
                    tokens_saved = tokens_saved + ?,
                    rubles_saved = rubles_saved + ?,
                    updated_at = ?
                WHERE id = 1
            """, (tokens, rub, now))
            conn.commit()

            return json.loads(row["response_json"])

    def set(
        self,
        cache_key: str,
        model: str,
        messages: list,
        response_dict: Dict[str, Any],
    ) -> None:
        """Saves a new prompt-response pair to cache."""
        now = int(time.time())
        usage = response_dict.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # Estimate savings cost
        meta = MODELS_BY_ID.get(model, {})
        in_p = meta.get("input_price_1m", 0.3)
        out_p = meta.get("output_price_1m", 1.5)
        cost_usd = (prompt_tokens * in_p + completion_tokens * out_p) / 1_000_000
        cost_rub = cost_usd * USD_TO_RUB_RATE

        prompt_str = str(messages[-1]["content"]) if messages else ""

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries
                (cache_key, model, prompt_hash, prompt_text, response_json, prompt_tokens, completion_tokens, estimated_rub_cost, created_at, hit_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                cache_key,
                model,
                hashlib.md5(prompt_str.encode("utf-8")).hexdigest(),
                prompt_str[:500],
                json.dumps(response_dict),
                prompt_tokens,
                completion_tokens,
                cost_rub,
                now,
                now,
            ))
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate metrics on cache hits and money saved."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT total_requests, cache_hits, tokens_saved, rubles_saved FROM metrics WHERE id = 1")
            m = cursor.fetchone()
            cur_entries = conn.execute("SELECT COUNT(*) as cnt FROM cache_entries").fetchone()
            total_req = m["total_requests"] or 0
            hits = m["cache_hits"] or 0
            hit_rate = round((hits / total_req * 100), 1) if total_req > 0 else 0.0

            return {
                "total_requests": total_req,
                "cache_hits": hits,
                "hit_rate_pct": hit_rate,
                "tokens_saved": m["tokens_saved"] or 0,
                "rubles_saved": round(m["rubles_saved"] or 0.0, 2),
                "total_cached_entries": cur_entries["cnt"] if cur_entries else 0,
            }

    def clear(self) -> int:
        """Clears all cached responses."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM cache_entries")
            conn.commit()
            return cursor.rowcount
