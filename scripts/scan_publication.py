"""Check all authored files with an external literal-substring policy."""

import argparse
from pathlib import Path

GENERATED = {".git", ".venv", "__pycache__", ".ruff_cache", "build", "dist"}


def scan(root: Path, policy: Path) -> int:
    root, policy = root.resolve(), policy.resolve()
    if policy.is_relative_to(root):
        raise ValueError("Keep publication rules outside the repository")
    terms = [
        line.strip().casefold()
        for line in policy.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not terms:
        raise ValueError("A nonempty external publication policy is required")
    count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(
            part in GENERATED or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        if path.is_symlink():
            raise ValueError("Symlinks need separate publication review")
        if not path.is_file():
            continue
        count += 1
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if any(term in line.casefold() for term in terms):
                raise ValueError(f"Blocked content: {relative}:{number}")
        if any(term in str(relative).casefold() for term in terms):
            raise ValueError("Blocked filename")
    print(f"Publication scan: {count} files, 0 matches")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--blocked-terms", type=Path, required=True)
    args = parser.parse_args()
    scan(args.root, args.blocked_terms)
