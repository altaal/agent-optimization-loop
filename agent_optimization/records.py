"""Small records and a text-only edit boundary."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def digest(value: Any) -> str:
    """Hash a JSON value in a stable representation."""
    content = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def save(path: Path, value: Any) -> None:
    """Refuse to replace an existing record."""
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


@dataclass(frozen=True)
class Case:
    id: str
    family: str
    issue: str
    source: str


def load_cases(path: Path) -> tuple[Case, ...]:
    cases = tuple(Case(**row) for row in json.loads(path.read_text()))
    if not cases or len({c.id for c in cases}) != len(cases):
        raise ValueError("Cases must be nonempty with unique identifiers")
    return cases


@dataclass(frozen=True)
class Instructions:
    system: str
    tools: tuple[tuple[str, str], ...]

    @classmethod
    def load(cls, directory: Path) -> "Instructions":
        tools = json.loads((directory / "tools.json").read_text())
        return cls(
            (directory / "system.txt").read_text().rstrip("\n"),
            tuple(sorted(tools.items())),
        )

    def files(self) -> dict[str, str]:
        return {
            "instructions/system.txt": self.system + "\n",
            "instructions/tools.json": json.dumps(dict(self.tools), indent=2)
            + "\n",
        }

    def changed(self, edits: dict[str, str]) -> "Instructions":
        """Accept complete text replacements for exactly two known files."""
        current = self.files()
        if not edits or edits.keys() - current.keys():
            raise ValueError("Edit outside the instruction boundary")
        for text in edits.values():
            if not isinstance(text, str) or not 0 < len(text.encode()) <= 16384:
                raise ValueError("Instruction text must fit 16 KiB")
        current.update(edits)
        descriptions = json.loads(current["instructions/tools.json"])
        if not isinstance(descriptions, dict) or set(descriptions) != {
            name for name, _ in self.tools
        }:
            raise ValueError("Tool names and schemas cannot change")
        if any(
            not isinstance(text, str) or not text.strip()
            for text in descriptions.values()
        ):
            raise ValueError("Each description must be nonempty text")
        system = current["instructions/system.txt"].rstrip("\n")
        if not system.strip():
            raise ValueError("System instructions cannot be empty")
        result = Instructions(system, tuple(sorted(descriptions.items())))
        if result == self:
            raise ValueError("The proposal makes no change")
        return result


@dataclass(frozen=True)
class Outcome:
    passed: bool
    status: str
    trace: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Proposal:
    reason: str
    evidence: tuple[str, ...]
    edits: dict[str, str]


class Ledger:
    """Append one JSON record per event and flush before continuing."""

    def __init__(self, path: Path, *, resume: bool = False):
        self.path = path
        self.sequence = 0
        if resume:
            events = [
                json.loads(line) for line in path.read_text().splitlines()
            ]
            if [e["sequence"] for e in events] != list(
                range(1, len(events) + 1)
            ):
                raise ValueError("Ledger sequence is incomplete")
            self.sequence = len(events)
        else:
            path.touch(exist_ok=False)

    def add(self, kind: str, **fields: Any) -> dict[str, Any]:
        self.sequence += 1
        event = {"sequence": self.sequence, "kind": kind, **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
        return event


def case_hashes(cases: tuple[Case, ...]) -> dict[str, str]:
    return {case.id: digest(asdict(case)) for case in cases}
