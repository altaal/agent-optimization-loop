# Experiment record

A development gain does not imply a gain on reserved cases.
The current saved run uses scripted outcomes to test that distinction.
Its real command was:

```sh
python3 -m agent_optimization demo --output results/offline-verified
```

## Observed offline counts

The [ledger](results/offline-verified/ledger.jsonl) contains 177 target attempts.
It records 15 discovery attempts, 72 gate attempts, and 90 final attempts.
Each completed attempt has a preceding start record.
The run used three candidate proposals and accepted one.
It retained both rejected proposals and every failed target attempt.

| Split | Tasks | Repeats per arm | Before | After | Difference | 95% interval |
| --- | --- | --- | --- | --- | --- | --- |
| Development | 5 | 3 | 9/15 | 15/15 | 0.40 | [0.00, 0.80] |
| Held out | 10 | 3 | 20/30 | 20/30 | 0.00 | [0.00, 0.00] |

Source: [report.json](results/offline-verified/report.json).
Each numerator counts passes. Each denominator counts attempts in one condition.
The report includes every task and all paired repeats.
Its intervals resample task families, not individual repeated attempts.

The zero-width held-out interval follows identical scripted differences for all tasks.
It does not establish certainty about future model behavior.

## Live experiment

Not run. The proposed hypothesis and budgets are in [PLAN.md](PLAN.md).
The next paid step is the development pilot after approval.
The final reserved cases must not guide prompt edits or pilot redesign.
Do not replace the offline labels with live claims.

## Earlier offline run

[offline-demo](results/offline-demo/report.json) preserves the initial complete run.
It has the same attempt counts and results, before the source-hash record was added.
