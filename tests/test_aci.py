"""Check the text boundary and optional integration with the pinned runtime."""

import importlib.util
import json
import unittest
from pathlib import Path

from agent_optimization.aci import AciTarget, InstructionClient
from agent_optimization.records import Instructions, load_cases

ROOT = Path(__file__).resolve().parents[1]


class TextTest(unittest.TestCase):
    def test_override_preserves_recovery_and_original_messages(self):
        class Echo:
            def complete(self, messages):
                return messages

        text = Instructions("new", (("view", "Read"),))
        client = InstructionClient(Echo(), "original", text)
        messages = [{"role": "system", "content": "original\nrecovery"}]
        result = client.complete(messages)
        self.assertEqual(result[0]["content"], "new\nrecovery")
        self.assertEqual(messages[0]["content"], "original\nrecovery")

    def test_unknown_upstream_prompt_fails_closed(self):
        text = Instructions("new", (("view", "Read"),))
        with self.assertRaises(ValueError):
            InstructionClient(None, "original", text).complete(
                [{"role": "system", "content": "other"}]
            )


@unittest.skipUnless(
    importlib.util.find_spec("aci_patch_agent"),
    "Install the pinned optional ACI dependency",
)
class AciIntegrationTest(unittest.TestCase):
    def test_real_loop_with_scripted_client_and_grader(self):
        captured = []

        class Client:
            def complete(self, messages):
                return {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "fixture-call",
                                "type": "function",
                                "function": {
                                    "name": "submit",
                                    "arguments": json.dumps({}),
                                },
                            }
                        ],
                    }
                }

        class Grader:
            def check(self, *_args, **_kwargs):
                return {"passed": True, "fixture": True}

        def factory(tools, seed):
            captured.append((tools, seed))
            return Client()

        target = AciTarget(ROOT / "data/target.json", factory, Grader())
        text = Instructions.load(ROOT / "instructions")
        case = load_cases(ROOT / "data/development.json")[0]
        result = target.run(case, text, 1701)
        self.assertTrue(result.passed)
        self.assertEqual(result.trace[0]["result"]["actions"], 2)
        self.assertEqual(captured[0][1], 1701)
        self.assertEqual(
            result.trace[0]["requests"][0][0]["content"], text.system
        )


if __name__ == "__main__":
    unittest.main()
