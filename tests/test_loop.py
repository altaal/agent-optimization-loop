"""Exercise experiment boundaries and each rejection path without a model."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agent_optimization.engine import SEEDS, gate, optimize, paired
from agent_optimization.evaluation import evaluate, rebuild_report, summarize
from agent_optimization.records import (
    Instructions,
    Ledger,
    Proposal,
    load_cases,
)
from agent_optimization.scripted import ScriptedOptimizer, ScriptedTarget

ROOT = Path(__file__).resolve().parents[1]


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "run"
        self.development = load_cases(ROOT / "data/development.json")
        self.heldout = load_cases(ROOT / "data/heldout.json")
        self.initial = Instructions.load(ROOT / "instructions")
        self.optimizer = ScriptedOptimizer()

    def run_search(self, optimizer=None, budget=3):
        return optimize(
            self.development,
            self.initial,
            ScriptedTarget(),
            optimizer or self.optimizer,
            self.output,
            proposals_per_cluster=budget,
        )

    def events(self):
        return [
            json.loads(line)
            for line in (self.output / "ledger.jsonl").read_text().splitlines()
        ]

    def test_demo_retains_rejections_and_one_patch(self):
        frozen = self.run_search()
        self.assertEqual(frozen["solved"], ["not_submitted"])
        events = self.events()
        rejections = [e["stage"] for e in events if e["kind"] == "rejected"]
        self.assertEqual(rejections, ["cluster", "regression"])
        self.assertEqual(len(list(self.output.glob("*.diff"))), 1)
        self.assertEqual(len([e for e in events if e["kind"] == "proposal"]), 3)
        self.assertEqual(
            self.optimizer.inputs[1]["feedback"][0]["stage"], "cluster"
        )

    def test_representative_failure_blocks_later_gates(self):
        class Ineffective(ScriptedOptimizer):
            def propose(inner, context):
                proposal = super().propose(context)
                return replace(
                    proposal,
                    edits={
                        "instructions/system.txt": self.initial.system
                        + "\nRead carefully.\n"
                    },
                )

        frozen = self.run_search(Ineffective(), budget=1)
        self.assertFalse(frozen["solved"])
        gates = [e for e in self.events() if e["kind"] == "gate"]
        self.assertEqual([g["gate"] for g in gates], ["representative"])
        self.assertFalse(gates[0]["passed"])

    def test_retry_budget_counts_initial_proposal(self):
        frozen = self.run_search(budget=2)
        self.assertFalse(frozen["solved"])
        self.assertEqual(frozen["instructions"], self.initial.files())
        self.assertEqual(len(self.optimizer.inputs), 2)
        self.assertFalse(list(self.output.glob("*.diff")))

    def test_zero_budget_rejected_before_output(self):
        with self.assertRaises(ValueError):
            self.run_search(budget=0)
        self.assertFalse(self.output.exists())

    def test_heldout_never_enters_optimizer_or_search_ledger(self):
        self.run_search()
        before = len(self.optimizer.inputs)
        search = (self.output / "ledger.jsonl").read_text()
        inputs = json.dumps(self.optimizer.inputs)
        for case in self.heldout:
            self.assertNotIn('"' + case.id + '"', inputs)
            self.assertNotIn('"' + case.id + '"', search)
        evaluate(self.output, self.development, self.heldout, ScriptedTarget())
        self.assertEqual(before, len(self.optimizer.inputs))

    def test_final_overlap_rejected_before_any_attempt(self):
        self.run_search()
        with self.assertRaises(ValueError):
            evaluate(
                self.output,
                self.development,
                self.development[:1],
                ScriptedTarget(),
            )
        self.assertFalse((self.output / "evaluation-lock.json").exists())

    def test_family_overlap_rejected(self):
        self.run_search()
        cases = (replace(self.heldout[0], family=self.development[0].family),)
        with self.assertRaises(ValueError):
            evaluate(self.output, self.development, cases, ScriptedTarget())

    def test_frozen_edit_rejected(self):
        self.run_search()
        path = self.output / "frozen.json"
        frozen = json.loads(path.read_text())
        frozen["instructions"]["instructions/system.txt"] += "Changed."
        path.write_text(json.dumps(frozen))
        with self.assertRaises(ValueError):
            evaluate(
                self.output, self.development, self.heldout, ScriptedTarget()
            )

    def test_final_is_once_only_and_rebuild_is_equal(self):
        self.run_search()
        result = evaluate(
            self.output, self.development, self.heldout, ScriptedTarget()
        )
        self.assertEqual(result, rebuild_report(self.output))
        with self.assertRaises(FileExistsError):
            evaluate(
                self.output, self.development, self.heldout, ScriptedTarget()
            )
        self.assertEqual(result["splits"]["heldout"]["difference"], 0)

    def test_missing_attempt_stays_in_denominator(self):
        self.run_search()
        evaluate(self.output, self.development, self.heldout, ScriptedTarget())
        events = self.events()
        dropped = next(
            e
            for e in events
            if e["kind"] == "attempt"
            and e.get("phase") == "final"
            and e["passed"]
        )
        events.remove(dropped)
        (self.output / "ledger.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )
        result = rebuild_report(self.output)
        self.assertEqual(result["missing_attempts"], 1)
        self.assertEqual(
            result["splits"]["development"]["attempts_per_arm"], 15
        )

    def test_error_attempts_preserved_and_gate_fails(self):
        class Broken:
            def run(self, *_args):
                raise OSError("Do not store transport messages")

        ledger = Ledger(Path(self.directory.name) / "errors.jsonl")
        rows = paired(
            Broken(), self.development[:1], self.initial, self.initial, ledger
        )
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(not row["passed"] for row in rows))
        self.assertFalse(gate(rows, improve=False))
        self.assertNotIn("Do not store", ledger.path.read_text())

    def test_every_pair_is_interleaved(self):
        ledger = Ledger(Path(self.directory.name) / "pairs.jsonl")
        rows = paired(
            ScriptedTarget(),
            self.development[:1],
            self.initial,
            self.initial,
            ledger,
        )
        self.assertEqual(
            [r["condition"] for r in rows],
            ["before", "after", "after", "before", "before", "after"],
        )
        self.assertEqual(
            [r["seed"] for r in rows], [s for s in SEEDS for _ in range(2)]
        )

    def test_empty_incomplete_duplicate_gates_fail(self):
        self.assertFalse(gate([], improve=False))
        ledger = Ledger(Path(self.directory.name) / "pairs.jsonl")
        rows = paired(
            ScriptedTarget(),
            self.development[:1],
            self.initial,
            self.initial,
            ledger,
        )
        self.assertFalse(gate(rows[:-1], improve=False))
        self.assertFalse(gate(rows + rows[:1], improve=False))
        self.assertTrue(gate(rows, improve=False))
        self.assertFalse(gate(rows, improve=True))

    def test_edit_boundary_covers_paths_schema_and_empty_text(self):
        invalid = [
            {"../system.txt": "text"},
            {"tests/test.py": "pass"},
            {"instructions/system.txt": " "},
            {"instructions/tools.json": '{"test": "pass"}'},
            {
                "instructions/tools.json": json.dumps(
                    {name: {} for name, _ in self.initial.tools}
                )
            },
            self.initial.files(),
        ]
        for edits in invalid:
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                self.initial.changed(edits)

    def test_scope_rejection_uses_budget_and_keeps_original(self):
        class Bad:
            def propose(self, context):
                return Proposal(
                    "Change grader",
                    (str(context["evidence"][0]["sequence"]),),
                    {"grader.py": "pass"},
                )

        frozen = self.run_search(Bad(), budget=2)
        self.assertEqual(frozen["instructions"], self.initial.files())
        self.assertEqual(
            len([e for e in self.events() if e["kind"] == "rejected"]), 2
        )

    def test_bootstrap_keeps_paired_repeats(self):
        ledger = Ledger(Path(self.directory.name) / "pairs.jsonl")
        rows = paired(
            ScriptedTarget(),
            self.development[:1],
            self.initial,
            self.initial,
            ledger,
        )
        report = summarize(rows)
        self.assertEqual(report["interval_95"], [0, 0])
        self.assertEqual(report["bootstrap_resamples"], 10000)
        with self.assertRaises(ValueError):
            summarize(rows[:-1])

    def test_existing_run_is_never_replaced(self):
        self.run_search()
        content = (self.output / "ledger.jsonl").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_search()
        self.assertEqual(content, (self.output / "ledger.jsonl").read_bytes())


if __name__ == "__main__":
    unittest.main()
