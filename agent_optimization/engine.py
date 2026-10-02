"""Optimize on development records only. No final cases enter this module."""

import difflib
import hashlib
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

from .records import (
    Case,
    Instructions,
    Ledger,
    Outcome,
    Proposal,
    case_hashes,
    digest,
    save,
)

SEEDS = (1701, 2903, 4109)


class Target(Protocol):
    def run(self, case: Case, text: Instructions, seed: int) -> Outcome: ...


class Optimizer(Protocol):
    def propose(self, context: dict[str, Any]) -> Proposal: ...


def attempt(
    target: Target,
    case: Case,
    text: Instructions,
    seed: int,
    ledger: Ledger,
    **labels: Any,
) -> dict[str, Any]:
    """Record intent first to preserve interrupted attempts."""
    intent = ledger.add(
        "attempt_started",
        case=case.id,
        family=case.family,
        seed=seed,
        instructions=digest(text.files()),
        **labels,
    )
    try:
        result = target.run(case, text, seed)
        if type(result.passed) is not bool:
            raise ValueError("Target pass result is not boolean")
    except Exception as error:  # Keep failed target calls in the denominator.
        result = Outcome(
            False,
            "infrastructure_error",
            ({"error_type": type(error).__name__},),
        )
    return ledger.add(
        "attempt",
        attempt_id=intent["sequence"],
        case=case.id,
        family=case.family,
        seed=seed,
        **asdict(result),
        **labels,
    )


def paired(
    target: Target,
    cases: tuple[Case, ...],
    before: Instructions,
    after: Instructions,
    ledger: Ledger,
    **labels: Any,
) -> list[dict[str, Any]]:
    """Alternate condition order and pair repeats by case and seed."""
    rows = []
    for index, seed in enumerate(SEEDS):
        arms = (("before", before), ("after", after))
        if index % 2:
            arms = arms[::-1]
        for case in cases:
            for condition, text in arms:
                rows.append(
                    attempt(
                        target,
                        case,
                        text,
                        seed,
                        ledger,
                        condition=condition,
                        **labels,
                    )
                )
    return rows


def gate(rows: list[dict[str, Any]], *, improve: bool) -> bool:
    """Require complete pairs, no per-case loss, and a gain for repair gates."""
    grouped: dict[str, dict[str, dict[int, bool]]] = defaultdict(
        lambda: {"before": {}, "after": {}}
    )
    if not rows:
        return False
    for row in rows:
        arm = grouped[row["case"]][row["condition"]]
        if row["seed"] in arm or row["status"] == "infrastructure_error":
            return False
        arm[row["seed"]] = row["passed"]
    gains = []
    for arms in grouped.values():
        if any(set(arm) != set(SEEDS) for arm in arms.values()):
            return False
        gains.append(sum(arms["after"].values()) - sum(arms["before"].values()))
    return all(gain >= 0 for gain in gains) and (not improve or sum(gains) > 0)


def review_plan(proposal: Proposal, context: dict[str, Any]) -> bool:
    """The local plan critic requires a reason and valid trace references."""
    available = {str(row["sequence"]) for row in context["evidence"]}
    return bool(
        proposal.reason.strip()
        and proposal.evidence
        and set(proposal.evidence) <= available
    )


def write_patch(
    output: Path, index: int, before: Instructions, after: Instructions
) -> str:
    name = f"patch-{index:02d}.diff"
    sections = []
    for path, content in before.files().items():
        sections.extend(
            difflib.unified_diff(
                content.splitlines(True),
                after.files()[path].splitlines(True),
                fromfile="a/" + path,
                tofile="b/" + path,
            )
        )
    with (output / name).open("x") as stream:
        stream.writelines(sections)
    return name


def optimize(
    development: tuple[Case, ...],
    initial: Instructions,
    target: Target,
    optimizer: Optimizer,
    output: Path,
    *,
    proposals_per_cluster: int = 3,
    max_clusters: int = 2,
) -> dict[str, Any]:
    """Return a frozen candidate after bounded, serial development search."""
    if type(proposals_per_cluster) is not int or proposals_per_cluster < 1:
        raise ValueError("A positive proposal budget is required")
    if type(max_clusters) is not int or max_clusters < 1:
        raise ValueError("A positive cluster budget is required")
    if not development or len({c.id for c in development}) != len(development):
        raise ValueError("Unique development cases are required")
    output.mkdir(parents=True, exist_ok=False)
    ledger = Ledger(output / "ledger.jsonl")
    save(
        output / "settings.json",
        {
            "mode": "scripted",
            "seeds": SEEDS,
            "proposals_per_cluster": proposals_per_cluster,
            "max_clusters": max_clusters,
            "code_sha256": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(Path(__file__).parent.glob("*.py"))
            },
            "case_hashes": case_hashes(development),
            "initial": initial.files(),
        },
    )
    baseline = [
        attempt(target, case, initial, seed, ledger, phase="discovery")
        for case in development
        for seed in SEEDS
    ]
    # These labels describe observations, not established causal explanations.
    clusters: dict[str, set[str]] = defaultdict(set)
    for row in baseline:
        if not row["passed"] and row["status"] != "infrastructure_error":
            clusters[row["status"]].add(row["case"])
    current = initial
    solved = []
    for cluster_index, (symptom, ids) in enumerate(sorted(clusters.items()), 1):
        if cluster_index > max_clusters:
            ledger.add(
                "unresolved", cluster=symptom, reason="Cluster budget exhausted"
            )
            continue
        inside = tuple(c for c in development if c.id in ids)
        outside = tuple(c for c in development if c.id not in ids)
        severity = "high" if symptom == "failed_tests" else "medium"
        ledger.add(
            "cluster",
            symptom=symptom,
            cases=sorted(ids),
            severity=severity,
            causal_status="hypothesis_required",
        )
        if len(inside) < 2 or not outside:
            ledger.add(
                "unresolved",
                cluster=symptom,
                reason="Not enough cases for three distinct gates",
            )
            continue
        feedback = []
        evidence = [row for row in baseline if row["case"] in ids]
        for number in range(1, proposals_per_cluster + 1):
            context = {
                "symptom": symptom,
                "cases": [asdict(case) for case in inside],
                "instructions": current.files(),
                "evidence": evidence,
                "feedback": feedback,
                "proposal_number": number,
            }
            ledger.add("optimizer_input", cluster=symptom, context=context)
            try:
                proposal = optimizer.propose(context)
                ledger.add(
                    "proposal",
                    cluster=symptom,
                    number=number,
                    proposal=asdict(proposal),
                )
                plan_ok = review_plan(proposal, context)
                ledger.add("plan_review", cluster=symptom, passed=plan_ok)
                if not plan_ok:
                    raise ValueError("Plan needs a reason and trace evidence")
                candidate = current.changed(proposal.edits)
                ledger.add(
                    "diff_review",
                    cluster=symptom,
                    passed=True,
                    candidate=digest(candidate.files()),
                )
            except Exception as error:
                failure = {
                    "stage": "proposal_review",
                    "error_type": type(error).__name__,
                }
                ledger.add(
                    "rejected", cluster=symptom, number=number, **failure
                )
                feedback.append(failure)
                continue
            accepted = True
            groups = (
                ("representative", inside[:1], True),
                ("cluster", inside[1:], True),
                ("regression", outside, False),
            )
            for name, cases, improve in groups:
                rows = paired(
                    target,
                    cases,
                    current,
                    candidate,
                    ledger,
                    phase="gate",
                    gate=name,
                    proposal=number,
                    cluster=symptom,
                )
                passed = gate(rows, improve=improve)
                ledger.add(
                    "gate",
                    cluster=symptom,
                    proposal=number,
                    gate=name,
                    passed=passed,
                )
                if not passed:
                    failure = {"stage": name, "attempts": rows}
                    feedback.append(failure)
                    ledger.add(
                        "rejected", cluster=symptom, number=number, stage=name
                    )
                    accepted = False
                    break
            if accepted:
                patch = write_patch(output, cluster_index, current, candidate)
                current = candidate
                solved.append(symptom)
                ledger.add(
                    "accepted", cluster=symptom, number=number, patch=patch
                )
                break
        else:
            ledger.add(
                "unresolved",
                cluster=symptom,
                reason="Proposal budget exhausted",
            )
    frozen = {
        "instructions": current.files(),
        "instruction_hash": digest(current.files()),
        "development_hashes": case_hashes(development),
        "families": sorted({case.family for case in development}),
        "solved": solved,
        "mode": "scripted",
    }
    save(output / "frozen.json", frozen)
    ledger.add("frozen", instruction_hash=frozen["instruction_hash"])
    return frozen
