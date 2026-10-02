"""Offline commands. This release has no paid-call command."""

import argparse
import json
from pathlib import Path

from .engine import optimize
from .evaluation import evaluate, rebuild_report
from .records import Instructions, load_cases
from .scripted import ScriptedOptimizer, ScriptedTarget


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run scripted fixtures offline")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--inputs", type=Path, default=Path("."))
    report = commands.add_parser(
        "report", help="Rebuild tables from the ledger"
    )
    report.add_argument("run", type=Path)
    args = parser.parse_args()
    if args.command == "report":
        print(json.dumps(rebuild_report(args.run), indent=2))
        return
    development = load_cases(args.inputs / "data/development.json")
    target = ScriptedTarget()
    frozen = optimize(
        development,
        Instructions.load(args.inputs / "instructions"),
        target,
        ScriptedOptimizer(),
        args.output,
    )
    # Load final cases only after the optimizer has returned its frozen result.
    heldout = load_cases(args.inputs / "data/heldout.json")
    result = evaluate(args.output, development, heldout, target)
    print("SCRIPTED DEMO: no model calls or code execution")
    print(f"Accepted clusters: {len(frozen['solved'])}")
    for split, data in result["splits"].items():
        total = data["attempts_per_arm"]
        print(
            f"{split}: {data['before_passes']}/{total} -> "
            f"{data['after_passes']}/{total}; "
            f"paired interval {data['interval_95']}"
        )
    print("Saved ledger.jsonl, frozen.json, evaluation-lock.json, report.json")
