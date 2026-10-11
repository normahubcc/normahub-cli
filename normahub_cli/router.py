"""
Pareto Model Router & Heuristic Complexity Evaluator.
Routes requests dynamically to optimize LLM token costs.
"""

import re
from typing import List, Tuple

CODE_MARKERS = [
    r"\bdef\s+\w+\(",
    r"\bclass\s+\w+",
    r"\bfunction\s+\w+",
    r"\bimport\s+[\w\.]+",
    r"\bSELECT\s+.+\s+FROM\b",
    r"\basync\s+def\b",
    r"```[a-zA-Z]*",
    r"\binterface\s+\w+",
    r"\btype\s+\w+\s*=",
    r"\bstruct\s+\w+",
    r"\bimpl\s+\w+",
    r"\breplace_file_content\b",
    r"\brecreate\s+architecture\b",
    r"\brefactor\b",
]

REASONING_MARKERS = [
    r"\bprove\s+that\b",
    r"\bcalculate\s+the\b",
    r"\bexplain\s+step\s+by\s+step\b",
    r"\bderivation\b",
    r"\bmathematical\b",
    r"\balgorithm\s+complexity\b",
    r"\bbig-o\b",
    r"\bsecurity\s+audit\b",
]


class ParetoRouter:
    """Evaluates request requirements and assigns the optimal model."""

    @classmethod
    def evaluate_complexity(cls, messages: List[dict]) -> Tuple[str, str]:
        """Analyzes messages and returns (selected_model_id, rationale)."""
        full_text = " ".join(str(m.get("content", "")) for m in messages)
        char_len = len(full_text)

        # 1. Check for Code or Architecture Complexity
        code_hits = sum(1 for pattern in CODE_MARKERS if re.search(pattern, full_text, re.IGNORECASE))
        if code_hits >= 2 or "```" in full_text:
            return (
                "claude-sonnet-5-5",
                f"Flagship reasoning selected (Detected {code_hits} code/architecture markers).",
            )

        # 2. Check for Deep Reasoning or Math
        reasoning_hits = sum(1 for pattern in REASONING_MARKERS if re.search(pattern, full_text, re.IGNORECASE))
        if reasoning_hits >= 1:
            return (
                "gpt-6-sol",
                f"High-complexity reasoning selected (Detected {reasoning_hits} analytical markers).",
            )

        # 3. Long context prompt (> 4000 characters)
        if char_len > 4000:
            return (
                "claude-sonnet-5",
                f"Balanced tier selected (Large context window of {char_len} characters).",
            )

        # 4. Fast, conversational, or micro-queries
        return (
            "deepseek-v4.1-flash",
            "Ultra-flash cost tier selected ($0.018 / 1M tokens - 95% savings).",
        )

    @classmethod
    def resolve_model(cls, requested_model: str, messages: List[dict]) -> Tuple[str, str]:
        """Resolves virtual aliases or direct models."""
        alias = requested_model.lower().strip()

        if alias in ("normahub/auto", "auto", "default"):
            return cls.evaluate_complexity(messages)
        elif alias in ("normahub/cheapest", "normahub/fast", "cheapest", "fast"):
            return ("deepseek-v4.1-flash", "Directly routed to cheapest ultra-flash model ($0.018/1M).")
        elif alias in ("normahub/reasoning", "reasoning", "flagship"):
            return ("claude-sonnet-5-5", "Directly routed to flagship reasoning tier.")
        elif alias in ("normahub/creative", "creative"):
            return ("muse-spark-1.3", "Routed to creative storytelling tier.")
        else:
            return (requested_model, "Direct model passthrough.")
