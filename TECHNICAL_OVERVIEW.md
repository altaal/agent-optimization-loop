# Weeks 7 and 8: instruction search and separate evaluation

An optimizer can select an edit that helps familiar examples but fails on new cases.
The lesson builds a small experiment that can expose that difference.
This checkpoint uses a scripted model. It does not measure model skill.

Here is the first concrete example.
[The development input](data/development.json) contains the `merge-intervals` issue and source.
The original fixture result is `{"submitted": false}`.
The accepted fixture result is `{"submitted": true}`.
[The ledger](results/offline-verified/ledger.jsonl) saves both exact inputs and outputs.
[The patch](results/offline-verified/patch-01.diff) adds this real instruction text:

```text
Check every issue requirement, then submit the completed repair.
```

The code below deliberately assigns fixture outcomes. It does not call a language model.

Source: [agent_optimization/scripted.py:49](agent_optimization/scripted.py#L49). Exact excerpt:

```python
        failures = {"merge-intervals", "parse-bool"}
        if case.id in failures:
            passed = stage >= 2 or (stage == 1 and case.id == "merge-intervals")
        elif case.id == "normalize-method":
            passed = stage != 2
        elif case.id in {"chunked", "unique-stable"}:
            passed = True
        else:
```

## Week 7: 1. Goal, expectation, and value

Build a loop that learns from development failures. Keep its evaluator fixed.
The research question asks whether accepted instruction edits help reserved cases.
The prediction is a smaller gain on reserved cases, possibly zero.
The lesson separates the search procedure from evidence of improvement.
A working pipeline alone does not answer the research question.

## Week 7: 2. Difference from the previous week

The previous exercise proposes preference training of model weights.
This exercise changes instruction text and keeps the target model and tools fixed.
Its controlled comparison is original versus selected instructions within one run.
The model and task changes across weeks prevent direct score comparisons.
[PLAN.md](PLAN.md) records the complete comparison table and proposed live settings.

## Week 7: 3. Exact commands and their effects

Run these commands from the repository root with Python 3.11 or later.
They use no service, model key, Docker process, or changed model weights.

```sh
python3 -m agent_optimization demo --output runs/lesson
python3 -m agent_optimization report runs/lesson
python3 -m unittest discover -s tests -v
python3 scripts/estimate_cost.py
```

The first command writes a new run directory and refuses an existing directory.
The second reconstructs tables from records. It does not rerun attempts.
The third tests offline control flow and edit restrictions.
The last prints proposed costs from saved rates, without a network request.

## Week 7: 4. Source version and directory map

The ACI dependency is `bc00468557a2af932ddc11ca2983714eb59c5845`.
[The target record](data/target.json) hashes its runtime files.
The initial prompt, tool descriptions, and task text came from that commit.
The source checkout's uncommitted edits did not enter these snapshots.

| Location | Responsibility |
| --- | --- |
| `agent_optimization/cli.py` | Parse offline commands |
| `agent_optimization/engine.py` | Discovery, proposals, reviews, and gates |
| `agent_optimization/records.py` | Data records, edit boundary, and ledger |
| `agent_optimization/scripted.py` | Deterministic model substitutes |
| `agent_optimization/aci.py` | Optional pinned target adapter |
| `agent_optimization/evaluation.py` | Final pairs and report calculations |
| `instructions/` | Initial system prompt and tool descriptions |
| `data/` | Cases, target pin, and price snapshot |
| `tests/` | Focused offline checks |
| `scripts/` | Publication scan and cost estimate |
| `runs/` | Untracked local experiments |
| `results/` | Retained evidence |

The current run's settings contain hashes of all package source files.
The older offline run predates this source-hash record.
Neither run uses the optional paid provider client.

## Week 7: 5. Exact code flow with snippets

```text
module entry -> cli.main -> load development -> optimize
  -> discovery attempts -> observed failure groups -> optimizer.propose
  -> review_plan -> Instructions.changed -> paired gates
  -> accepted diff -> frozen.json
```

Source: [agent_optimization/engine.py:220](agent_optimization/engine.py#L220). Exact excerpt:

```python
        for number in range(1, proposals_per_cluster + 1):
            context = {
                "symptom": symptom,
                "cases": [asdict(case) for case in inside],
                "instructions": current.files(),
                "evidence": evidence,
                "feedback": feedback,
                "proposal_number": number,
            }
```

`optimize` supplies development cases, current instructions, trace evidence, and prior failures.
The proposal counter includes the initial proposal.
The model substitute returns a reason, cited event identifiers, and text replacements.
The plan check rejects absent or unknown trace references.
The edit check accepts only the two instruction files and preserves tool names.

Source: [agent_optimization/engine.py:260](agent_optimization/engine.py#L260). Exact excerpt:

```python
            groups = (
                ("representative", inside[:1], True),
                ("cluster", inside[1:], True),
                ("regression", outside, False),
            )
```

The gate runner gives each case to `target.run` with an instruction bundle and seed.
It runs both conditions again for each gate. Their order alternates.
The target returns a pass flag, status, and trace.
The gate checks complete pairs and per-case score changes.

A failed gate returns its attempt records to the next proposal.
An accepted candidate replaces the current instruction bundle in memory.
The model cannot write files directly.

Source: [agent_optimization/records.py:119](agent_optimization/records.py#L119). Exact excerpt:

```python
        event = {"sequence": self.sequence, "kind": kind, **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
        return event

```

The ledger appends a JSON line after each event.
Each attempt has a start record before target execution.
A target exception becomes an infrastructure failure with its exception type.
Raw exception messages do not enter the record.
`write_patch` saves one instruction diff per accepted group.
`save` uses exclusive file creation for settings and the final instruction record.

## Week 7: 6. Follow one example to disk

Use the saved current run, not an imagined model conversation.
Its first proposal adds a reminder to inspect source before submission.
The representative case gains three passes from three attempts.
The other case gains zero passes from three attempts, so event 62 rejects the edit.

The next proposal helps both cases but hurts a regression case.
Event 130 rejects that proposal. Event 198 accepts the third proposal.

All inputs, synthetic responses, plans, critic results, and gates remain in
[ledger.jsonl](results/offline-verified/ledger.jsonl).
The accepted instruction text and its hash appear in
[frozen.json](results/offline-verified/frozen.json).
The patch changes only `instructions/system.txt`.
No executable repair or evaluator code changes.

## Week 7: 7. Tests and reproduction

The core tests need no optional package.
The ACI integration test skips when its pinned dependency is absent.
The completed verification also ran that test against the exact pinned package.
Its scripted client submits twice because the real ACI loop requires a review first.
Its scripted grader reports success. This checks protocol wiring, not Python behavior.

To install the optional dependency, use this command with network access:

```sh
python3 -m pip install -e '.[aci,dev]'
python3 -m unittest discover -s tests -v
ruff check agent_optimization tests scripts
```

Installation downloads public dependencies. It makes no paid model calls.
[VERIFIED.md](VERIFIED.md) records actual results and the publication checks.

## Week 7: 8. Observed results and interpretation

The current run accepts one of three candidate proposals.
It retains 15 discovery attempts and 72 gate attempts.
The ledger provides the numerator, denominator, and underlying records.
These outcomes demonstrate the acceptance and retry mechanics only.
There is no measured prompt-search result until the live pilot runs.

## Week 8: 1. Goal, expectation, and value

Measure the frozen candidate on cases that supplied no optimizer feedback.
The question and prediction remain those from Week 7.
The additional lesson keeps paired comparisons and the failure denominator intact.
A paired comparison keeps the same task and repeat identity in both conditions.

The real scripted final output includes this line:

```text
heldout: 20/30 -> 20/30; paired interval [0.0, 0.0]
```

[report.json](results/offline-verified/report.json) supplies both counts and the interval.
The result demonstrates a zero gain outside the search fixtures.

## Week 8: 2. Difference from Week 7

The optimizer stops before final evaluation begins.
Week 8 changes only which cases supply the final measurement.
The experiment compares original and selected instructions with the same settings.
It permits no further prompt edits based on the final result.

## Week 8: 3. Exact commands and their effects

The demo command above also runs the separate final evaluator.
To rebuild the published table without target calls:

```sh
python3 -m agent_optimization report results/offline-verified
```

This only replaces the derived `report.json` file.
It preserves the ledger and the declaration of required attempts.

## Week 8: 4. Source version and directory map

The evaluator reuses the same pinned target and candidate from Week 7.
It checks instruction hashes and rejects overlapping case or family identifiers.
`evaluation-lock.json` declares every final attempt before execution.
The exclusive lock rejects a second final evaluation in the same run directory.
This is a procedural boundary, not encryption or a filesystem sandbox.

## Week 8: 5. Exact code flow with snippets

```text
frozen instructions -> evaluate -> check splits and hashes
  -> declare every final attempt -> paired -> append to the same ledger
  -> rebuild_report -> per-task means -> family bootstrap -> report.json
```

Source: [agent_optimization/cli.py:37](agent_optimization/cli.py#L37). Exact excerpt:

```python
    heldout = load_cases(args.inputs / "data/heldout.json")
    result = evaluate(args.output, development, heldout, target)
```

The CLI loads reserved case text after `optimize` returns.
The evaluator receives no optimizer argument.
Tests inspect every optimizer input and search record for reserved identifiers.
They also check that final evaluation triggers no further proposal.

Source: [agent_optimization/evaluation.py:52](agent_optimization/evaluation.py#L52). Exact excerpt:

```python
    for _ in range(10000):
        sample = [
            value
            for group in rng.choices(groups, k=len(groups))
            for value in group
        ]
        draws.append(sum(sample) / len(sample))
```

A bootstrap interval resamples the observed task families to describe sample variation.
Both arms and all repeats remain together in each sampled family.
The report first averages each task's paired repeat differences.
It includes missing declared attempts as failures and reports their count.
Repeated attempts do not become independent tasks.

## Week 8: 6. Follow one example to disk

The `clamp` case exists only in the reserved input file.
It never appears in a proposal context or search gate.
The final evaluator runs both instruction versions on each of the three seeds.

The fixture passes two of three attempts in each condition.
The ledger holds all six records. The report shows a paired difference of zero.
No optimizer callback receives those results.

## Week 8: 7. Tests and reproduction

Tests reject case overlap and family overlap.
They also reject altered frozen text and repeated final evaluation.
They check interleaving, missing attempts, infrastructure failures, and duplicate records.
The report reproduction test compares the entire reconstructed report.
It does not call a live model or independently grade a saved repair.

## Week 8: 8. Observed results and limits

Development rises from 9/15 to 15/15 scripted passes.
Reserved cases remain at 20/30 in both conditions.
The intervals are [0.00, 0.80] and [0.00, 0.00], respectively.
[The report](results/offline-verified/report.json) includes every per-case count.

The scripts determine the outcomes, so these are not empirical capability estimates.
The intended live experiment remains pending.
A live result can be inconclusive because the task set is small or too easy.
Keep that outcome and its traces. Do not tune the candidate on final cases.
