"""Adapter for the pinned ACI runtime. Callers supply client and sandbox."""

import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .records import Case, Instructions, Outcome


class InstructionClient:
    """Replace prompt text while preserving the ACI recovery suffix."""

    def __init__(self, client: Any, original: str, text: Instructions):
        self.client, self.original, self.text = client, original, text
        self.model = getattr(client, "model", "scripted-aci")
        self.requests: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]]) -> Any:
        messages = deepcopy(messages)
        system = messages[0]["content"]
        if not system.startswith(self.original):
            raise ValueError("Unexpected upstream system prompt")
        messages[0]["content"] = self.text.system + system[len(self.original) :]
        self.requests.append(deepcopy(messages))
        return self.client.complete(messages)


class AciTarget:
    """Run immutable upstream code with text overrides and supplied services."""

    def __init__(self, pin: Path, client_factory: Any, sandbox: Any):
        spec = importlib.util.find_spec("aci_patch_agent")
        if spec is None or spec.origin is None:
            raise ValueError("Install the pinned ACI dependency")
        root = Path(spec.origin).parent
        for name, expected in json.loads(pin.read_text())["sha256"].items():
            if (
                hashlib.sha256((root / name).read_bytes()).hexdigest()
                != expected
            ):
                raise ValueError("Installed ACI code does not match its pin")
        self.agent = importlib.import_module("aci_patch_agent.agent")
        self.tools = importlib.import_module("aci_patch_agent.tools")
        self.tasks = importlib.import_module("aci_patch_agent.tasks")
        self.eval_tasks = importlib.import_module("aci_patch_agent.eval_tasks")
        self.client_factory, self.sandbox = client_factory, sandbox

    def run(self, case: Case, text: Instructions, seed: int) -> Outcome:
        tasks = (*self.tasks.TASKS, *self.eval_tasks.EVAL_TASKS)
        task = next(t for t in tasks if t.id == case.id)
        if (case.issue, case.source) != (task.issue, task.source):
            raise ValueError("Case does not match the pinned task")
        schemas = deepcopy(self.tools.TOOLS)
        for schema in schemas:
            function = schema["function"]
            function["description"] = dict(text.tools)[function["name"]]
        client = InstructionClient(
            self.client_factory(schemas, seed), self.agent.SYSTEM_PROMPT, text
        )
        result = self.agent.run_task(
            task, client, self.sandbox, max_actions=15, max_total_tokens=32000
        )
        status = result["status"]
        if status in {"api_error", "evaluation_error"}:
            status = "infrastructure_error"
        elif not result["passed"] and not result["submitted"]:
            status = "not_submitted"
        return Outcome(
            result["passed"],
            status,
            (
                {
                    "requests": client.requests,
                    "tools": schemas,
                    "result": result,
                },
            ),
        )
