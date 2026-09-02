# Manifest — Exception Economics dataset v1.0.0

Dataset version 1.0.0 · Seed 20260902 · Written 2026-09-02 · Charter version 1.0.0.

The machine-readable form is `manifest.json`, written by `generate.py` and carrying
the ground-truth hash. This file explains the choices in it.

---

## Populations

Two populations inside the 2,000 items. Both are in `ground-truth.jsonl` and both are
labelled on every item.

| Population | Items | Purpose |
|---|---|---|
| `baseline` | 1,700 | The acceptance set. The frozen labelled set the day-0 measurement is taken on, and the population the leaderboard scores |
| `shifted` | 300 | Tier 5 only. Categories, vendor formats and document sources absent from the baseline. Used to build the day-N live samples in the drift simulation |

Charter 4.4.2 makes tier 5 the only tier in which the ninety-day drift simulation is
applied, so every shifted item is tier 5. Charter 4.4 requires tier 5 to contain at
least one category with no labelled example anywhere in the baseline set, and the
shifted population supplies three families of them.

| Shift driver | Work type | Items | Categories introduced |
|---|---|---|---|
| `new_vendor_format` | `invoice_po_recon` | 120 | `consolidated_statement_pdf`, `milestone_billing_xml`, `marketplace_settlement_json` |
| `new_ticket_category` | `ticket_triage` | 110 | `loyalty_points_transfer`, `installer_scheduling`, `regulatory_data_request`, `trade_in_valuation` |
| `new_kyc_source` | `kyc_case` | 70 | `digital_identity_wallet`, `municipal_residence_certificate`, `cross_border_registry_api` |

`validate.py` checks that no baseline item uses any of those categories or formats, and
that every shifted item is tier 5 and carries a driver.

---

## Splits

| Split | Items | Folder | Published |
|---|---|---|---|
| `public_sample` | 100 | `sample/` | Yes, as a release archive |
| `private_holdout` | 300 | Not materialised as a folder | **No. Never** |
| `open` | 1,600 | Not materialised as a split | Regenerable from the seed |

Every item carries its `split` field, so the assignment is part of the ground truth
and does not depend on which folders exist on disk.

### How the splits are drawn

Both are stratified across the fifteen (work type, tier) buckets in proportion to each
bucket's share of the 2,000 items, using the largest-remainder method so the split
sizes are exactly 100 and 300 and no bucket is skipped where its count allows one.
Within each bucket the draw uses a stream seeded from the dataset seed and the split
name, so the assignment is deterministic and reproducible.

The result: the 100-item sample is representative rather than convenient, and a score
on the sample is comparable in kind to a score on the private split.

### Why the private split exists

Charter 5.10. A public benchmark can be tuned against. The private split is how a
divergence is detected: where a system's private-split result differs from its
public-set result by more than the threshold the charter names, the divergence is
reported for that system without inference about its cause. Detection is not
prevention, and charter 9.6 says so.

---

## Lifecycle and exclusions

Charter 3.1.2. Nothing is silently dropped, and every exclusion is counted beside the
figure it was excluded from.

| Lifecycle | Items | Charter rule | Treatment |
|---|---|---|---|
| `admitted` | 1,892 | 3.14.4 | The denominator of every rate |
| `pre_processing_rejected` | 57 | 3.14.4 | Excluded from the denominator; the rejecting rule is named on the item |
| `upstream_failure` | 26 | 3.14.5 | Excluded, counted, reported as an upstream failure |
| `in_flight` | 25 | 3.14.5 | Excluded, counted, reported as in flight |

Both the received count and the admitted count are reported, so the effect of the
admission rule on the rate is visible.

The three named pre-processing rules are `duplicate_intake_within_24h`,
`unsupported_attachment_type` and `sender_not_on_approved_list`. A statement of work
would name its own; these stand in for that clause.

---

## The ninety-day drift steps

Charter 3.17.4 requires the shifted input distribution to be defined in the dataset
manifest rather than in the scorer, so it lives in `manifest.json` and is read from
there by `drift.py`.

Seven steps, 600 items drawn per step.

| Day | Step | Shifted share of the sample | Work-type weights of the rest | What changed |
|---|---|---|---|---|
| 0 | Acceptance baseline | 0 % | ticket 0.40, KYC 0.25, reconciliation 0.35 | Nothing. This is the acceptance measurement |
| 15 | First new vendor formats | 5 % | 0.39 / 0.25 / 0.36 | Two vendors move to a consolidated statement format |
| 30 | New ticket categories appear | 10 % | 0.42 / 0.24 / 0.34 | A product launch introduces ticket categories with no labelled example |
| 45 | Shift established | 16 % | 0.42 / 0.24 / 0.34 | The new formats and categories are now routine traffic |
| 60 | Onboarding season begins | 23 % | 0.36 / 0.32 / 0.32 | Seasonal mix moves towards KYC as onboarding volume rises |
| 75 | Period-end volume | 30 % | 0.33 / 0.29 / 0.38 | Period-end pushes reconciliation volume up |
| 90 | Ninety-day measurement | 38 % | 0.33 / 0.28 / 0.39 | The ninety-day endpoint required by charter 3.17 |

### How a step's sample is drawn

The shifted portion, being `shifted_share` of the 600, is drawn from the shifted
population and allocated across the three drivers in proportion to their size in that
population. The rest is drawn from the baseline population and allocated across work
types by the step's weights. Both draws are seeded from the dataset seed and the step
day, so the whole curve is reproducible and identical on any machine.

The shares and the weights are design decisions of the charter, recorded here so a
reader can change one and re-run rather than argue about it. They are not measurements
of any real drift.

### Two drift figures, one of which is zero

Charter 3.17.1 requires frozen-set drift and live-distribution drift, and treats
neither as complete without the other.

Frozen-set drift is zero at every step of this simulation, by construction: the
simulation changes the input distribution and nothing else, so the same decision
policy scores the same frozen items identically at every step. That zero is a property
of the simulation. It is not a finding about any system's stability. A real frozen-set
drift figure needs a real system measured twice, ninety days apart, and none has been.

---

## Reference decision policy parameters

The parameters that shape the synthetic confidence signal are recorded in
`manifest.json` under `reference_policy_parameters` so that they can be inspected
without reading the generator. They are parameters of the dataset. They are not a
claim about how any model behaves.

| Parameter | Value |
|---|---|
| Probability the policy is correct, by tier | T1 0.985, T2 0.960, T3 0.900, T4 0.780, T5 0.620 |
| Multiplier applied on shifted items | 0.70 |
| Share carrying a hard validation failure, by tier | 0.010, 0.025, 0.045, 0.075, 0.110 |
| Share carrying a policy flag, by tier | 0.005, 0.010, 0.020, 0.040, 0.070 |
| Share the policy could not process | 0.015 |
| Share rejected before processing | 0.030 |
| Share abandoned on an upstream failure | 0.010 |
| Share open at window close | 0.012 |

Confidence is drawn from a beta distribution conditioned on whether the policy is
right, with a deliberate overconfidence tail at tiers 4 and 5 and a wider one on
shifted items. A system that is confidently wrong on inputs it has not seen is the
behaviour the drift simulation exists to make visible, so the dataset contains it on
purpose and says so here.

---

## Integrity

`manifest.json` carries the sha256 of `ground-truth.jsonl`. `validate.py` checks the
file on disk against it, and separately regenerates the whole dataset from the seed
and checks that the result is byte-identical. A dataset that does not reproduce from
its seed is not a dataset a result can be traced through, so the check is a build
failure rather than a warning.
