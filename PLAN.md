# Weeks 7 and 8 plan

The experiment asks whether an accepted instruction edit helps cases outside search.
The offline fixture already demonstrates why these are different measurements.
Its accepted edit changes development passes from 9/15 to 15/15.
The held-out result stays at 20/30 in both conditions.
[The report](results/offline-verified/report.json) contains these scripted counts.
They establish no model gain.

Status: the offline checkpoint is complete. Paid work requires approval.

## Week 7: 1. Goal, expectation, and value

**Goal:** build a bounded loop that proposes instruction edits from failure records.
**Question:** do edits that pass development gates also help held-out cases?
**Prediction:** development gains exceed held-out gains, which can be zero.
**Value:** learn how to separate search success from generalization.
Generalization means success on cases that did not guide the search.
This is an engineering exercise, not a claim of a new optimization method.

Completion requires a runnable loop, complete records, a patch, and checked boundaries.
Live completion also requires the approved pilot. A failed pilot remains a result.

The controlled variable is the instruction bundle: system prompt plus tool descriptions.
The model weights, tool schemas, grader, tasks, and execution budgets stay fixed.
Individual prompt and description effects cannot be separated in this design.

## Week 7: 2. Difference from the previous week

| Aspect         | Previous exercise                  | This exercise                                   |
| -------------- | ---------------------------------- | ----------------------------------------------- |
| Question       | Transfer after preference training | Transfer after instruction search               |
| Changed object | A model adapter                    | Text instructions                               |
| Reused code    | Bounded repair protocol            | Pinned ACI loop and original tasks              |
| Model          | A local coding model               | Proposed hosted Qwen model                      |
| Feedback       | Preferred and rejected edits       | Development traces and gate results             |
| Budget         | Training and evaluation            | Bounded candidate proposals and paired attempts |
| Outputs        | Adapter and repair results         | Instruction patches and one event ledger        |

This is a new mechanism. Scores from different weeks are not a controlled comparison.
The previous series plan contains proposals, not evidence that its revised runs occurred.

## Week 8: 1. Goal, expectation, and value

**Goal:** freeze the selected instructions and measure both conditions separately.
**Question:** does the gain survive on the reserved cases with repeated attempts?
**Prediction:** any held-out gain is smaller than the development gain.
**Value:** practice paired measurement and honest uncertainty with a small sample.
Completion requires every declared attempt, per-case results, and a paired interval.
A zero or negative result completes the experiment.

A held-out case supplies no optimizer feedback.
Here, held out means reserved from this search only.
The fixtures were already public and appeared in earlier experiments.
They do not establish freedom from model training contamination.

## Week 8: 2. Difference from the previous week

| Aspect            | Week 7                          | Week 8                                  |
| ----------------- | ------------------------------- | --------------------------------------- |
| Work              | Propose and accept edits        | Measure a frozen candidate              |
| Inputs            | Development cases only          | Development and reserved cases          |
| Model and tools   | Proposed fixed settings         | The same approved settings              |
| Instruction edits | Up to three proposals per group | None                                    |
| Attempts          | Discovery and three gates       | Both conditions on each case            |
| Output            | Candidate and ledger            | Per-case table and uncertainty interval |

Week 8 changes the measurement scope. It introduces no second optimizer.

## Cases, attempts, and pilot

Use [five development cases](data/development.json) and
[ten reserved cases](data/heldout.json) from the pinned public target.
Each task has its own family label. Any new related variants must share that label.
Semantic similarity can remain across different tasks in this small set.

| Step                  | Declared calculation                                        | Maximum target attempts |
| --------------------- | ----------------------------------------------------------- | ----------------------- |
| Pilot discovery       | 5 cases × 3 repeats                                         | 15                      |
| Pilot candidate gates | 5 cases × 2 conditions × 3 repeats                          | 30                      |
| Full discovery        | 5 cases × 3 repeats                                         | 15                      |
| Full search           | 2 groups × 3 proposals × 5 cases × 2 conditions × 3 repeats | 180                     |
| Final development     | 5 cases × 2 conditions × 3 repeats                          | 30                      |
| Final held out        | 10 cases × 2 conditions × 3 repeats                         | 60                      |

The pilot uses at most one optimizer call and 45 target attempts.
The full run uses at most six optimizer calls and 285 target attempts.
These are proposed budgets, not observed usage.
The local critics make no model calls.

Require a pilot baseline of 30% to 70% completed repairs.
At least two development cases must share an observed failure label.
At least one other development case must remain for the regression gate.
Check that both conditions receive their exact instruction bundle on every request.

If these checks fail, stop for a revised design. Keep the failed pilot.
Earlier ACI scores suggest a ceiling is possible. Do not relax the gate silently.
Use no held-out case to choose replacement tasks or revise the prompt.

## Gates and bounded search

Use the fixed seeds in `engine.SEEDS` for three attempts per condition and case.
The first gate requires a gain on the representative case.
The second requires a total gain on other cases with the same observed failure.
It also requires no per-case loss.
The third requires no per-case loss on the remaining development cases.

An infrastructure error fails a gate. Empty gate sets cannot pass.

A failure returns the measured evidence to the next proposal.
The budget includes the initial proposal and permits at most two further proposals.
After three failures, retain the previous instructions and record the unresolved group.
The loop searches at most two groups in deterministic order.
An accepted patch becomes the starting point for the next group.
Its regression gate therefore covers earlier solved cases too.

The critics check trace references and the edit boundary.
They do not establish that a proposed causal explanation is correct.
The behavioral gates decide acceptance. This project chooses their thresholds.
They are not statistical significance tests.

## Frozen live settings and analysis

Propose `qwen/qwen3-next-80b-a3b-instruct` for target and optimizer.
Use target temperature 0.6, a 1,200 output-token limit, and 15 actions.
Retain the ACI cumulative token stop of 32,000 reported tokens.
Use a 12,000 input-token ceiling per request in the future live wrapper.
The optimizer gets at most 12,000 input tokens and 2,000 output tokens.

Stop on oversized input. Do not silently remove evidence to fit the limit.

Before the full run, commit task hashes, splits, instructions, and decoder settings.
Also commit the model identifier, provider route, code hashes, attempt matrix, budgets, and
analysis.
Record the provider's returned model and usage on every call.
Provider support for a seed does not guarantee identical random choices across arms.
The public endpoint has no immutable model-weight revision. Record this limit.

Alternate the condition order within paired repeats.
Keep failures and exhausted retries in the primary denominator.
Retry only transport errors, rate limits, and server errors, at most twice.
Use the same retry policy in both conditions and respect server retry guidance.
Save each retry. Do not retry model mistakes as transport errors.

Average paired differences within each task.
Resample whole task families with both arms and all repeats intact.
Use 10,000 resamples, seed 7331, and a 95% percentile interval.
Also report an infrastructure-clean analysis that removes affected pairs together.
Unbalanced outages prevent attributing a small difference to the instructions.

The offline reporter implements the primary analysis.
The live wrapper, retry ledger, and sensitivity analysis remain pending.

## Cost estimate

The [saved public rates](data/pricing.json) came from the
[OpenRouter model catalog](https://openrouter.ai/api/v1/models).
The snapshot date is October 2, 2026.
They quote $0.10 per million input tokens and $1.10 per million output tokens.
Cached-input discounts are excluded from the estimate.

The typical assumption is 12,000 input tokens and 2,000 output tokens per target attempt.
The conservative estimate uses all 15 calls, each with the proposed per-call limits.
It also counts two possible transport retries for every call.
These assumptions guide the budget. No live usage was measured.

| Paid step | Typical assumption | Conservative estimate | Proposed spend cap |
| --------- | ------------------ | --------------------- | ------------------ |
| Pilot     | $0.1564            | $5.1132               | $6                 |
| Full run  | $0.9894            | $32.3802              | $35                |

[The cost script](scripts/estimate_cost.py) calculates every value.
The estimate excludes taxes and future price changes.
Recheck rates and implement the spend guard before any paid execution.
Approval of a pilot does not approve the full run or publication.

## Public grounding

| Choice                                    | Public source                                                      | Application here                         |
| ----------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------- |
| Edit instructions from execution evidence | [GEPA §3.2](https://arxiv.org/pdf/2507.19457v1)                    | Change only text                         |
| Keep test feedback outside search         | [GEPA §4](https://arxiv.org/pdf/2507.19457v1)                      | Separate final evaluator                 |
| Diagnose, patch, compare, retain outcomes | [AutoSaddler §4](https://arxiv.org/html/2608.23041v1#S4)           | Small serial search with an event ledger |
| Repeat runs and report reserved cases     | [AutoSaddler §3](https://arxiv.org/html/2608.23041v1#S3)           | Repeated paired attempts                 |
| Protect evaluation and records            | [Harness tampering, taxonomy](https://arxiv.org/html/2609.00069v1) | Text-only update boundary                |

These papers supplied design ideas, not copied implementations or expected scores.
The three-stage gates, exact sample sizes, thresholds, and cost caps are project choices.
The family bootstrap follows the existing series comparison rule.
This project does not implement evolutionary archives or optimize its own optimizer.

## Decisions still open

Unless the pilot exposes a ceiling, use the default question and pinned target.
Start with the $6 pilot cap after approval and completion of its live-call wrapper.
Keep publication separate until the live evidence and lesson are ready.

## Documentation and publication update

On October 2, 2026, the project owner requested complete technical documentation and GitHub
publication.
This request replaces the earlier publication hold for the offline checkpoint.
The earlier plan remains above as the decision record.
Paid model execution remains outside this publication task.
The complete reference is [TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md).
