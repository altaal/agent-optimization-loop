"""Final measurement has no optimizer argument or feedback return path."""

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .engine import SEEDS, Target, paired
from .records import Case, Ledger, case_hashes, digest, save
from .scripted import from_files


def summarize(rows: list[dict[str, Any]], seed: int = 7331) -> dict[str, Any]:
    """Bootstrap whole families, keeping both arms and repeats together."""
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = grouped.setdefault(
            row["case"],
            {
                "family": row["family"],
                "before": {},
                "after": {},
            },
        )
        arm = item[row["condition"]]
        if row["seed"] in arm:
            raise ValueError("Duplicate attempt in final report")
        arm[row["seed"]] = bool(row["passed"])
    if not grouped:
        raise ValueError("No final attempts")
    families: dict[str, list[float]] = defaultdict(list)
    per_case = []
    for name, item in sorted(grouped.items()):
        if any(set(item[arm]) != set(SEEDS) for arm in ("before", "after")):
            raise ValueError("Incomplete final matrix")
        before, after = (sum(item[arm].values()) for arm in ("before", "after"))
        difference = (after - before) / len(SEEDS)
        families[item["family"]].append(difference)
        per_case.append(
            {
                "case": name,
                "before_passes": before,
                "after_passes": after,
                "attempts_per_arm": len(SEEDS),
                "difference": difference,
            }
        )
    groups = list(families.values())
    rng = random.Random(seed)
    draws = []
    for _ in range(10000):
        sample = [
            value
            for group in rng.choices(groups, k=len(groups))
            for value in group
        ]
        draws.append(sum(sample) / len(sample))
    draws.sort()
    return {
        "per_case": per_case,
        "before_passes": sum(row["before_passes"] for row in per_case),
        "after_passes": sum(row["after_passes"] for row in per_case),
        "attempts_per_arm": len(grouped) * len(SEEDS),
        "case_count": len(grouped),
        "family_count": len(groups),
        "difference": sum(row["difference"] for row in per_case)
        / len(per_case),
        "interval_95": [draws[249], draws[9749]],
        "bootstrap_resamples": 10000,
        "bootstrap_seed": seed,
    }


def evaluate(
    run: Path,
    development: tuple[Case, ...],
    heldout: tuple[Case, ...],
    target: Target,
) -> dict[str, Any]:
    """Write one final matrix only after checking the frozen record."""
    frozen = json.loads((run / "frozen.json").read_text())
    settings = json.loads((run / "settings.json").read_text())
    if digest(frozen["instructions"]) != frozen["instruction_hash"]:
        raise ValueError("Frozen instructions changed")
    if case_hashes(development) != frozen["development_hashes"]:
        raise ValueError("Development fixtures changed")
    if not heldout or len({c.id for c in heldout}) != len(heldout):
        raise ValueError("Unique final cases are required")
    if {c.id for c in development} & {c.id for c in heldout} or set(
        frozen["families"]
    ) & {c.family for c in heldout}:
        raise ValueError("Final cases or families overlap development")
    # Exclusive creation makes repeated peeking an explicit new experiment.
    save(
        run / "evaluation-lock.json",
        {
            "instruction_hash": frozen["instruction_hash"],
            "heldout_hashes": case_hashes(heldout),
            "attempts": [
                {
                    "split": split,
                    "case": case.id,
                    "family": case.family,
                    "condition": condition,
                    "seed": seed,
                }
                for split, cases in (
                    ("development", development),
                    ("heldout", heldout),
                )
                for case in cases
                for seed in SEEDS
                for condition in ("before", "after")
            ],
        },
    )
    ledger = Ledger(run / "ledger.jsonl", resume=True)
    before = from_files(settings["initial"])
    after = from_files(frozen["instructions"])
    for split, cases in (("development", development), ("heldout", heldout)):
        paired(target, cases, before, after, ledger, phase="final", split=split)
    return rebuild_report(run)


def rebuild_report(run: Path) -> dict[str, Any]:
    """Rebuild tables and count absent declared attempts as failures."""
    lock = json.loads((run / "evaluation-lock.json").read_text())
    frozen = json.loads((run / "frozen.json").read_text())
    events = [
        json.loads(line)
        for line in (run / "ledger.jsonl").read_text().splitlines()
    ]

    def identity(row: dict[str, Any]) -> tuple:
        return tuple(row[k] for k in ("split", "case", "condition", "seed"))

    observed = {}
    for row in events:
        if row["kind"] == "attempt" and row.get("phase") == "final":
            key = identity(row)
            if key in observed:
                raise ValueError("Duplicate final attempt")
            observed[key] = row
    expected = {identity(row) for row in lock["attempts"]}
    if observed.keys() - expected:
        raise ValueError("Unexpected final attempt")
    rows = [
        observed.get(
            identity(row),
            {
                **row,
                "passed": False,
                "status": "missing",
            },
        )
        for row in lock["attempts"]
    ]
    reports = {
        split: summarize([r for r in rows if r["split"] == split])
        for split in ("development", "heldout")
    }
    report = {
        "mode": frozen["mode"],
        "splits": reports,
        "missing_attempts": sum(r["status"] == "missing" for r in rows),
        "infrastructure_errors": sum(
            r["status"] == "infrastructure_error" for r in rows
        ),
        "note": "Scripted fixture results, not measured model ability.",
    }
    (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
