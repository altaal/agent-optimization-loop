# Rejected edits and limits

The demo keeps failed attempts beside successful attempts.
Its first candidate helps the representative case but leaves the other case unchanged.
[The ledger](results/offline-verified/ledger.jsonl) records that rejection at event 62.

| Proposal | Failure | Evidence |
| --- | --- | --- |
| 1 | The second development case has no gain | Event 62, cluster gate |
| 2 | Another development case loses passes | Event 130, regression gate |
| 3 | All three gates pass | Event 198, accepted patch |

All three proposals remain in the ledger. Two rejections consume two of three slots.
The accepted patch is [patch-01.diff](results/offline-verified/patch-01.diff).
The scripted model defines these behaviors deliberately.
The events do not establish a causal explanation for a real agent.

## Limits of this checkpoint

There are no live results, paid calls, or executed repair tests in the demo.
The optional ACI integration check uses a scripted client and a scripted grader.
It checks connection to the real loop, not repair correctness or container isolation.
The full ACI Docker grader still needs a live-phase smoke check.

The reserved tasks are public historical fixtures.
Their separation protects this search, not model training contamination.
The task set is small and some concepts overlap between tasks.
Three repeats reduce dependence on one draw but do not remove sampling noise.

The optimizer API receives only serialized development evidence.
It has no file or shell tool. This is not a sandbox for arbitrary Python plugins.
Local critics check structure and scope. They cannot prove semantic correctness.
The loop leaves small groups unresolved when the three gate sets cannot exist.

## Build record

The first unit run passed 19 tests and skipped the optional ACI integration test.
The first lint run reported 11 issues across code format and a test fixture.
The fixture used a shared mutable dictionary value. It now uses separate values.

Code format and import repairs removed the remaining lint findings.
The pinned runtime check later passed all 20 tests without a paid call.
[VERIFIED.md](VERIFIED.md) contains the final outputs.

The earlier [offline-demo](results/offline-demo/report.json) predates code hashes in run settings.
The current [offline-verified](results/offline-verified/report.json) includes those hashes.
Both runs retain their complete attempts and produce the same score totals.
