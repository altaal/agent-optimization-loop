"""Explicit test doubles. These outcomes are not model measurements."""

import json
from copy import deepcopy
from typing import Any

from .engine import SEEDS
from .records import Case, Instructions, Outcome, Proposal


class ScriptedOptimizer:
    """Exercise a cluster failure, a regression, and then an accepted edit."""

    def __init__(self):
        self.inputs: list[dict[str, Any]] = []

    def propose(self, context: dict[str, Any]) -> Proposal:
        self.inputs.append(deepcopy(context))
        scripts = (
            "After each edit, inspect the current source before submitting.",
            "Submit after all example checks pass.",
            "Check every issue requirement, then submit the completed repair.",
        )
        number = min(context["proposal_number"], len(scripts))
        return Proposal(
            reason="Missing submissions suggest unclear completion guidance.",
            evidence=(str(context["evidence"][0]["sequence"]),),
            edits={
                "instructions/system.txt": context["instructions"][
                    "instructions/system.txt"
                ]
                + scripts[number - 1]
                + "\n"
            },
        )


class ScriptedTarget:
    """Choose fixed fixture outcomes from candidate text and repeat identity."""

    def run(self, case: Case, text: Instructions, seed: int) -> Outcome:
        stage = 0
        if text.system.endswith("before submitting."):
            stage = 1
        elif text.system.endswith("example checks pass."):
            stage = 2
        elif text.system.endswith("the completed repair."):
            stage = 3
        failures = {"merge-intervals", "parse-bool"}
        if case.id in failures:
            passed = stage >= 2 or (stage == 1 and case.id == "merge-intervals")
        elif case.id == "normalize-method":
            passed = stage != 2
        elif case.id in {"chunked", "unique-stable"}:
            passed = True
        else:
            # Final fixtures have repeat variation but no treatment effect.
            passed = seed != SEEDS[-1]
        return Outcome(
            passed,
            "passed" if passed else "not_submitted",
            (
                {
                    "kind": "scripted_fixture",
                    "input": {
                        "issue": case.issue,
                        "source": case.source,
                        "system": text.system,
                        "tools": dict(text.tools),
                        "seed": seed,
                    },
                    "output": {"submitted": passed},
                    "note": "No model call or code execution occurred.",
                },
            ),
        )


def from_files(files: dict[str, str]) -> Instructions:
    return Instructions(
        files["instructions/system.txt"].rstrip("\n"),
        tuple(sorted(json.loads(files["instructions/tools.json"]).items())),
    )
