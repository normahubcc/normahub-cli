import unittest
from normahub_cli.router import ParetoRouter


class TestParetoRouter(unittest.TestCase):
    def test_simple_greeting_routes_to_flash(self):
        messages = [{"role": "user", "content": "Привет, как дела?"}]
        model, rationale = ParetoRouter.resolve_model("normahub/auto", messages)
        self.assertEqual(model, "deepseek-v4.1-flash")
        self.assertIn("Ultra-flash", rationale)

    def test_code_snippet_routes_to_sonnet_flagship(self):
        messages = [{"role": "user", "content": "def calculate_hash(data):\n    import hashlib\n    return hashlib.sha256(data).hexdigest()"}]
        model, rationale = ParetoRouter.resolve_model("normahub/auto", messages)
        self.assertEqual(model, "claude-sonnet-5-5")
        self.assertIn("Flagship reasoning", rationale)

    def test_math_reasoning_routes_to_gpt6(self):
        messages = [{"role": "user", "content": "Please prove that the square root of 2 is irrational step by step."}]
        model, rationale = ParetoRouter.resolve_model("normahub/auto", messages)
        self.assertEqual(model, "gpt-6-sol")
        self.assertIn("reasoning", rationale)

    def test_direct_alias_routes(self):
        self.assertEqual(ParetoRouter.resolve_model("normahub/cheapest", [])[0], "deepseek-v4.1-flash")
        self.assertEqual(ParetoRouter.resolve_model("normahub/reasoning", [])[0], "claude-sonnet-5-5")
        self.assertEqual(ParetoRouter.resolve_model("claude-opus-5", [])[0], "claude-opus-5")


if __name__ == "__main__":
    unittest.main()
