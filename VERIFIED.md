# Verification record

The offline checkpoint runs without a paid model call.
The pinned ACI integration check also uses a scripted client and grader.
It does not execute a model-generated repair.

## Environment and commands

The checked environment used Python 3.12.12 and Ruff 0.14.14.
The core package requires Python 3.11 or later.
Run commands from the repository root.
The optional integration check used the exact ACI commit in `data/target.json`.

```sh
python3 -m unittest discover -s tests -v
ruff check agent_optimization tests scripts
ruff format --check agent_optimization tests scripts
python3 scripts/scan_publication.py --blocked-terms "$PUBLICATION_POLICY"
gitleaks detect --source . --no-git --no-banner
vale --config "$PROSE_CONFIG" --output=line *.md
python3 "$STE_CHECK" *.md
```

The three environment variables name external publication and prose-check files.
They keep private policy contents and machine paths outside this repository.
The publication scanner uses case-insensitive literal substring checks.
It scans every authored file and excludes Git metadata and generated caches.
It rejects symlinks and unreadable binary content.

The series notes refer to a past Ruff appendix without its exact rule list.
This project records `E,F,W,I,UP,B,SIM,RUF` explicitly in `pyproject.toml`.
The check covers the package, tests, and scripts.

## Actual outputs

The complete command outputs and exit codes are in [checks.json](results/checks.json).
The test run passed all 20 tests with the pinned optional dependency present.
Without that dependency, 19 tests pass and the integration test skips.
Ruff, the publication scan, gitleaks, and Vale pass.

The prose checker reports filename warnings about the word in this file's name.
The same word occurs in a saved run directory name.
These warnings concern file references, not prose instructions.
Its report contains zero prose errors.

The exact offline demo output was:

```text
SCRIPTED DEMO: no model calls or code execution
Accepted clusters: 1
development: 9/15 -> 15/15; paired interval [0.0, 0.8]
heldout: 20/30 -> 20/30; paired interval [0.0, 0.0]
Saved ledger.jsonl, frozen.json, evaluation-lock.json, report.json
```

The saved ledger contains 177 completed attempts out of 177 started attempts.
The final report includes all 90 declared final attempts.
The report command reconstructs the same per-case data from that ledger.
It does not independently rerun or grade a repair.

## What remains

After approval, implement the live provider wrapper and spending guard.
Also implement transport retry records and the paired sensitivity analysis.
The pilot and full experiment then require separate paid-run decisions.
No public remote, repository, tag, or push is part of this checkpoint.
The existing series guide and earlier repositories remain unchanged by this work.

The public-source choices and proposed costs are in [PLAN.md](PLAN.md).
The project uses only the pinned public target and original authored code.
The private publication policy stays outside the repository.

## Documentation and publication checks

The preceding record describes the initial offline checkpoint.
The later publication request authorizes the project artifacts on GitHub.
It does not authorize paid model calls.
The complete technical document adds source contracts, exact calculations, and implementation
limits.
The package source and saved experiment records remain unchanged.

The additional command outputs are in [publication-checks.json](results/publication-checks.json).

The document checks use the STE checker, Vale, and mdsmith.
The retained STE warnings match technical filenames and directory names.
Those identifiers remain exact so that links still identify the saved evidence.
The mdsmith length and token limits conflict with the requested complete document.
Those two size warnings remain intentional.

The checks found no sentence, paragraph, or table errors.
A checker cannot prove correct use of every word in the STE dictionary.

The fresh run passed all 20 tests, including the pinned ACI integration test.
All six fresh demo files matched the saved run byte for byte.
The source excerpts, event references, calculations, and local document links passed their checks.
The file index accounts for all 43 project artifacts.
The publication scan and secret scans found no matches.

The file access policy blocked the first Ruff cache writes.
The repeated commands used `--no-cache` and passed.
This change affected the check command only.
