# Exception Economics v1.0 — leaderboard

Dataset `exception-economics` version 1.0.0 · seed 20260902 · ground truth sha256 `49af7a5ee30fb3fc` · scorer version 1.0.0 · charter version 1.0.0 · run date 2026-09-02 · ground truth synthetic.

## Status

No system has been run against this dataset. The build environment holds no model interface key and cannot reach a model interface, so every system row below reads `not run` with its reason, per charter 3.1.8.

| System | Automation rate % | Rework min per 1,000 automated | Reviewer min per 1,000 items | Net cost per item | Status |
|---|---|---|---|---|---|
| GPT (latest) | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Claude (latest) | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Gemini (latest) | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Mistral (latest) | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Open model A | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Open model B | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |
| Entailment Labs pipeline | not run | not run | not run | not run | not run — no model interface key and no reachable model interface in the build environment |

That table is the point of the suite and it is empty. What follows is not a substitute for it.

## What this suite scores, and what it does not need

Exception Economics scores a decision policy over labelled items. For each item the policy either completes it without a person or routes it to one, and where it completes an item it is either right or wrong. Automation rate, wrong-automation rework, reviewer minutes and net cost per item all follow from those two facts and from the labour model. Every one of them is arithmetic over ground truth. None of them needs a model to be called.

That is why this suite produces numbers in an environment with no keys and no network, and it is also the limit of what those numbers mean. They describe a policy and a threshold. They describe no vendor's system.

A real system's predictions are dropped in through a documented interface, one JSON object per item with `item_id`, `proposed_outcome` and `confidence`. `score.py --predictions <file>` then produces the same tables for that system, and the system rows above stop reading `not run`.

## Reference decision policy

The figures below come from the dataset's reference decision policy: a synthetic confidence and proposed outcome generated with each item. It is a property of the dataset. It is not a measurement of any model, service or vendor, and no row in it should be read as one.

### Denominators

The tables below score the **baseline population**, being the 1,700 items of the 2,000-item dataset that make up the acceptance set. The remaining 300 items are the shifted population and are used only by the drift simulation in `drift.md`, per charter 4.4.2. `MANIFEST.md` sets out both.

Charter 3.1.2: nothing is silently dropped, and every exclusion is counted beside the figure it was excluded from.

| Line | Items |
|---|---|
| Items received, baseline population | 1,700 |
| Rejected before processing by a named rule | 44 |
| Abandoned, upstream system unavailable | 23 |
| Open at window close, reported as in flight | 24 |
| **Items admitted to processing** | **1,609** |

The scorer asserts the identity in charter 3.5.3 at every threshold: automation rate plus exception rate equals one over items admitted. A run whose counts do not reconcile fails rather than reporting.

### Headline, at three confidence thresholds

Charter 3.14.6: automation rate is never published alone. The wrong-automation figure sits on the same row.

| Confidence threshold | Automation rate % | Wrong automations | Wrong automations as % of automated | Rework min per 1,000 automated | Open exposure items | Reviewer min per 1,000 items | Net cost per item, INR | Net cost per item, USD |
|---|---|---|---|---|---|---|---|---|
| 0.80 | 72.2 | 47 | 4.0 | 899.2 | 3 | 2,842.3 | 61.5474 | 1.2309 |
| 0.90 | 37.4 | 18 | 3.0 | 890.2 | 1 | 5,374.9 | 98.4845 | 1.9697 |
| 0.95 | 14.6 | 3 | 1.3 | 314.9 | 0 | 6,845.1 | 118.2131 | 2.3643 |

Sample size 1,609 items admitted, at every threshold. Money at the placeholder rates below, which are not market rates and are not a measurement.

### The threshold that minimises net cost

Swept from 0.50 to 0.99 in steps of 0.01, 50 points.

| Figure | Value |
|---|---|
| Minimising threshold | 0.68 |
| Automation rate at that threshold, % | 86.9 |
| Net cost per item, INR | 51.3600 |
| Net cost per item, USD | 1.0272 |
| Reviewer min per 1,000 items | 1,638.8 |
| Rework min per 1,000 automated | 1,427.4 |
| Open exposure items | 7 |

The curve, at every fifth point of the sweep.

| Threshold | Automation rate % | Reviewer min per 1,000 items | Rework min per 1,000 automated | Open exposure items | Net cost per item, INR |
|---|---|---|---|---|---|
| 0.50 | 91.1 | 1,260.8 | 2,310.4 | 8 | 59.4592 |
| 0.55 | 90.6 | 1,288.0 | 2,199.6 | 7 | 58.0473 |
| 0.60 | 89.6 | 1,401.6 | 1,868.8 | 7 | 54.6177 |
| 0.65 | 88.4 | 1,515.4 | 1,577.0 | 7 | 51.8623 |
| 0.70 | 85.6 | 1,729.1 | 1,360.7 | 7 | 51.6013 |
| 0.75 | 80.7 | 2,160.4 | 1,057.0 | 4 | 53.5912 |
| 0.80 | 72.2 | 2,842.3 | 899.2 | 3 | 61.5474 |
| 0.85 | 57.8 | 3,886.5 | 925.8 | 1 | 77.0550 |
| 0.90 | 37.4 | 5,374.9 | 890.2 | 1 | 98.4845 |
| 0.95 | 14.6 | 6,845.1 | 314.9 | 0 | 118.2131 |

### Per tier

Charter 4.1.4: every results table is broken out by tier, and the headline moves when the mix moves, so the mix travels with it.

Threshold 0.80.

| Tier | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| T1 | 320 | 83.4 | 1 | 0.4 | 0 | 200.0 | 11.0 |
| T2 | 398 | 82.7 | 1 | 0.3 | 0 | 464.4 | 11.0 |
| T3 | 407 | 71.5 | 4 | 1.4 | 0 | 951.9 | 121.0 |
| T4 | 321 | 57.0 | 22 | 12.0 | 1 | 1,761.8 | 424.0 |
| T5 | 163 | 55.8 | 19 | 20.9 | 2 | 1,195.2 | 477.0 |

Threshold 0.90.

| Tier | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| T1 | 320 | 48.4 | 0 | 0.0 | 0 | 620.0 | 0.0 |
| T2 | 398 | 50.3 | 0 | 0.0 | 0 | 1,115.1 | 0.0 |
| T3 | 407 | 40.8 | 1 | 0.6 | 0 | 1,841.1 | 27.0 |
| T4 | 321 | 15.3 | 9 | 18.4 | 0 | 3,084.8 | 234.0 |
| T5 | 163 | 19.0 | 8 | 25.8 | 1 | 1,987.2 | 274.0 |

Threshold 0.95.

| Tier | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| T1 | 320 | 25.0 | 0 | 0.0 | 0 | 900.0 | 0.0 |
| T2 | 398 | 20.9 | 0 | 0.0 | 0 | 1,676.7 | 0.0 |
| T3 | 407 | 17.0 | 0 | 0.0 | 0 | 2,479.5 | 0.0 |
| T4 | 321 | 0.9 | 3 | 100.0 | 0 | 3,560.0 | 74.0 |
| T5 | 163 | 0.0 | 0 | not run | 0 | 2,397.6 | 0.0 |

### Per work type

Threshold 0.80.

| Work type | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| invoice_po_recon | 564 | 71.6 | 14 | 3.5 | 1 | 1,702.1 | 526.0 |
| kyc_case | 408 | 70.8 | 13 | 4.5 | 1 | 1,874.0 | 309.0 |
| ticket_triage | 637 | 73.5 | 20 | 4.3 | 1 | 997.2 | 209.0 |

Threshold 0.90.

| Work type | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| invoice_po_recon | 564 | 36.5 | 9 | 4.4 | 0 | 3,269.7 | 383.0 |
| kyc_case | 408 | 36.3 | 5 | 3.4 | 1 | 3,506.2 | 108.0 |
| ticket_triage | 637 | 38.8 | 4 | 1.6 | 0 | 1,872.2 | 44.0 |

Threshold 0.95.

| Work type | Items admitted | Automation rate % | Wrong automations | Wrong as % of automated | Open exposure items | Reviewer minutes | Rework minutes |
|---|---|---|---|---|---|---|---|
| invoice_po_recon | 564 | 13.3 | 2 | 2.7 | 0 | 4,225.1 | 63.0 |
| kyc_case | 408 | 16.2 | 0 | 0.0 | 0 | 4,378.9 | 0.0 |
| ticket_triage | 637 | 14.8 | 1 | 1.1 | 0 | 2,409.7 | 11.0 |

### Reviewer minutes per exception, by queue entry code

Charter 3.16.1: reported as the mean and the median, and always broken down by entry code, because a low-confidence check and a processing failure are different pieces of work.

Threshold 0.80.

| Entry code | Exceptions closed | Mean minutes | Median minutes | Total minutes |
|---|---|---|---|---|
| AUDIT | 1 | 16.20 | 16.20 | 16.2 |
| FAIL | 18 | 4.12 | 3.93 | 74.1 |
| FLAG | 26 | 27.50 | 21.60 | 714.9 |
| LOWCONF | 326 | 8.25 | 7.20 | 2,687.9 |
| VALFAIL | 77 | 14.03 | 12.60 | 1,080.1 |
| **All codes** | **448** | **10.21** | **7.60** | **4,573.3** |

Threshold 0.90.

| Entry code | Exceptions closed | Mean minutes | Median minutes | Total minutes |
|---|---|---|---|---|
| FAIL | 18 | 4.12 | 3.93 | 74.1 |
| FLAG | 26 | 27.50 | 21.60 | 714.9 |
| LOWCONF | 887 | 7.64 | 6.00 | 6,779.0 |
| VALFAIL | 77 | 14.03 | 12.60 | 1,080.1 |
| **All codes** | **1,008** | **8.58** | **7.20** | **8,648.1** |

Threshold 0.95.

| Entry code | Exceptions closed | Mean minutes | Median minutes | Total minutes |
|---|---|---|---|---|
| FAIL | 18 | 4.12 | 3.93 | 74.1 |
| FLAG | 26 | 27.50 | 21.60 | 714.9 |
| LOWCONF | 1,253 | 7.30 | 5.40 | 9,144.6 |
| VALFAIL | 77 | 14.03 | 12.60 | 1,080.1 |
| **All codes** | **1,374** | **8.02** | **6.00** | **11,013.7** |

`DRIFT` is zero at every threshold. No drift monitor is modelled in this suite. Whether a deployment's monitoring sees a drift, and how long it takes to say so, is measured by the Day-60 suite in `10-benchmarks/day-60/`, not by this one.

### Wrong-automation rework, by error class

Charter 3.15.3: an error class with no detection route inside the measurement window is reported as an open exposure count with the class named, and is never given an estimated minute figure.

Threshold 0.80. Open exposure items: 3 (kyc_false_pass 1, recon_missed_exception 1, ticket_missed_escalation 1).

| Error class | Items | Detection route | Rework minutes | Treatment |
|---|---|---|---|---|
| kyc_false_pass | 1 | none_within_window | not priced | open exposure |
| kyc_false_reject | 11 | applicant complaint or relationship-manager escalation | 297.0 | priced |
| kyc_wrong_refer_reason | 1 | second-line quality review | 12.0 | priced |
| recon_missed_exception | 1 | none_within_window | not priced | open exposure |
| recon_overpayment | 2 | supplier statement reconciliation | 120.0 | priced |
| recon_underpayment | 2 | supplier chase | 46.0 | priced |
| recon_wrong_match | 9 | period-end reconciliation of open purchase orders | 360.0 | priced |
| ticket_missed_escalation | 1 | none_within_window | not priced | open exposure |
| ticket_wrong_category | 18 | receiving queue rejects the ticket back to triage | 198.0 | priced |
| ticket_wrong_priority | 1 | service-level breach alert on the ticket | 11.0 | priced |

Threshold 0.90. Open exposure items: 1 (kyc_false_pass 1).

| Error class | Items | Detection route | Rework minutes | Treatment |
|---|---|---|---|---|
| kyc_false_pass | 1 | none_within_window | not priced | open exposure |
| kyc_false_reject | 4 | applicant complaint or relationship-manager escalation | 108.0 | priced |
| recon_overpayment | 2 | supplier statement reconciliation | 120.0 | priced |
| recon_underpayment | 1 | supplier chase | 23.0 | priced |
| recon_wrong_match | 6 | period-end reconciliation of open purchase orders | 240.0 | priced |
| ticket_wrong_category | 4 | receiving queue rejects the ticket back to triage | 44.0 | priced |

Threshold 0.95. Open exposure items: 0.

| Error class | Items | Detection route | Rework minutes | Treatment |
|---|---|---|---|---|
| recon_underpayment | 1 | supplier chase | 23.0 | priced |
| recon_wrong_match | 1 | period-end reconciliation of open purchase orders | 40.0 | priced |
| ticket_wrong_category | 1 | receiving queue rejects the ticket back to triage | 11.0 | priced |

### Reported separately, and not inside net cost

| Line | Threshold 0.80 | Threshold 0.90 | Threshold 0.95 | Why |
|---|---|---|---|---|
| Sampled-audit minutes | 56.0 | 22.0 | 10.0 | Charter 3.16.5: an audit is a measurement device, not production work |
| Manual handling minutes after a processing failure | 203.0 | 203.0 | 203.0 | The item still has to be done by hand; the charter's net cost composition does not include it, so it is shown beside it |
| Items drawn into the sampled audit | 20 | 8 | 3 | Audit rate is a scoring parameter, not a result |
| Audits that changed the output | 1 | 0 | 0 | Charter 3.4.2: these are exceptions, not automated items |

## The labour model behind the money

| Input | Value | Status |
|---|---|---|
| Fully loaded reviewer cost, INR per hour | 1,000.00 | placeholder — replace |
| Fully loaded reviewer cost, USD per hour | 20.00 | placeholder — replace |
| Senior reviewer multiplier | 1.60 | placeholder — replace |
| Machine cost per item, INR | 0.00 | placeholder — replace after a run |
| Machine cost per item, USD | 0.00 | placeholder — replace after a run |

The INR and USD rates are two independent placeholders. No exchange rate is applied between them anywhere in the scorer, and none should be inferred from the two figures sitting beside each other. Machine cost is zero because no system has been run, so no measured cost per item exists; every net cost figure in this report is therefore labour only.

Every minute figure in the labour model is a modelling assumption and each one states its basis in `labour-model.yaml`. Not one was measured by a time study, ours or anyone else's. `validate.py` fails the build if a minute figure appears without a basis, or if a money figure appears without the placeholder mark.

