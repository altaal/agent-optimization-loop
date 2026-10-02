# Agent Optimization Loop

An instruction edit can help familiar cases and fail to help new ones.
This project builds the experiment that measures that difference.
It is the proposed weeks 7 and 8 exercise in the agent project series.

Here is a real saved example from the **scripted offline demo**.
The input case is `merge-intervals`, with this source from the pinned ACI task:

```python
def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start < result[-1][1]:
            result[-1][1] = end
        else:
            result.append([start, end])
    return result
```

The scripted target returns `submitted: false` with the original instructions.
It returns `submitted: true` with the accepted instruction edit.
Both records are in [the saved ledger](results/offline-verified/ledger.jsonl).
These are test-double outputs. They are not model responses or tested repairs.

## Run offline

Use Python 3.11 or later from this repository's root.
The demo uses the standard library. It needs no account, API key, or Docker.

```sh
python3 -m agent_optimization demo --output runs/example
python3 -m agent_optimization report runs/example
python3 -m unittest discover -s tests -v
```

Choose a new output directory for each run. Existing runs cannot be replaced.
The report command rebuilds tables from saved attempts. It makes no model calls.

## What the loop does

It groups observed development failures, asks for a text edit, and checks the edit.
A gate is a check that an edit must pass before the loop accepts it.
Each gate compares the current accepted and proposed instructions with repeated attempts.

```text
development attempts -> observed failure groups -> proposed text edit
    -> plan check -> edit boundary -> one case -> related cases
    -> other development cases -> accepted patch -> frozen instructions

frozen instructions -> separate final evaluation -> per-case report
```

The optimizer can change the system prompt and tool descriptions only.
It cannot change tool schemas, tests, scores, case selection, or the ledger.
The final evaluator receives no optimizer object and sends it no results.

## Saved result and scope

The [scripted report](results/offline-verified/report.json) shows:

| Split       | Before                  | After                   | Paired difference |
| ----------- | ----------------------- | ----------------------- | ----------------- |
| Development | 9 passes / 15 attempts  | 15 passes / 15 attempts | +0.40             |
| Held out    | 20 passes / 30 attempts | 20 passes / 30 attempts | 0.00              |

The fixture scripts define these scores. They demonstrate the measurement code.
The project reports no measured model improvement. It made no paid call.

The default live target is [ACI Patch Agent](https://github.com/altaal/aci-patch-agent).
[The pin](data/target.json) records its source version and file hashes.
The optional adapter passes an offline integration test against that version.

Read [PLAN.md](PLAN.md) for the question, pilot gates, sources, and proposed costs.
Read [TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md) for the complete technical document.
It includes the worked lessons, source contracts, event trace, calculations, tests, and pending live
work.
[FAILURES.md](FAILURES.md) retains rejected edits and limits.
[VERIFIED.md](VERIFIED.md) contains the actual checks.
The paid runner and final live experiment remain future work after approval.

License: [MIT](LICENSE).
