# Exception Economics v1.0 — ninety-day drift simulation

Dataset `exception-economics` version 1.0.0 · seed 20260902 · ground truth sha256 `49af7a5ee30fb3fc` · scorer version 1.0.0 · charter version 1.0.0 · run date 2026-09-02 · ground truth synthetic.

## What this is

A simulation. Charter 3.17.4 requires it to be labelled one in the table, the chart and the prose, so it is labelled one here and in every file that quotes it. Every number on this page is a simulation output over synthetic ground truth, produced by scoring the dataset's synthetic reference decision policy against a shifted input distribution. No system was run. Nothing here is a record of what happened to a deployment.

What it is evidence about is sensitivity: how much a fixed decision policy and a fixed threshold cost when the input moves underneath them. That is a question a partner can ask before signing, and this is one way to answer it.

## The shift

Seven steps across ninety days, 600 items drawn per step. The steps are defined in the dataset manifest, not in the scorer, per charter 3.17.4.

| Day | Step | Shifted share of the sample % | Work-type weights | What changed |
|---|---|---|---|---|
| 0 | acceptance baseline | 0 | invoice_po_recon 0.35, kyc_case 0.25, ticket_triage 0.40 | The acceptance measurement. No shifted items, baseline work mix. |
| 15 | first new vendor formats | 5 | invoice_po_recon 0.36, kyc_case 0.25, ticket_triage 0.39 | Two vendors move to a consolidated statement format. |
| 30 | new ticket categories appear | 10 | invoice_po_recon 0.34, kyc_case 0.24, ticket_triage 0.42 | A product launch introduces ticket categories with no labelled example. |
| 45 | shift established | 16 | invoice_po_recon 0.34, kyc_case 0.24, ticket_triage 0.42 | The new formats and categories are now routine traffic. |
| 60 | onboarding season begins | 23 | invoice_po_recon 0.32, kyc_case 0.32, ticket_triage 0.36 | Seasonal mix moves towards KYC as onboarding volume rises. |
| 75 | period-end volume | 30 | invoice_po_recon 0.38, kyc_case 0.29, ticket_triage 0.33 | Period-end pushes reconciliation volume up. |
| 90 | ninety-day measurement | 38 | invoice_po_recon 0.39, kyc_case 0.28, ticket_triage 0.33 | The ninety-day endpoint required by charter 3.17. |

The shifted population is 300 items, every one of them tier 5, because charter 4.4.2 makes tier 5 the only tier in which the drift simulation is applied. It carries three drivers: new vendor formats on reconciliation, new ticket categories with no labelled example anywhere in the baseline, and a new KYC source format. The seasonal weights move the work-type mix of the rest of the sample. Both draws are seeded from the dataset seed and the step day, so the whole curve reproduces exactly.

## Frozen-set drift

Charter 3.17.1 requires two figures and treats neither as complete without the other. Frozen-set drift is zero at every step of this simulation, by construction: the simulation changes the input distribution and nothing else, so the same decision policy scores the same frozen items identically at every step.

That zero is a property of the simulation. It is not a finding about any system's stability, and quoting it as one would be a misuse of this page. A real frozen-set drift figure needs a real system measured twice, ninety days apart, and none has been.

## Live-distribution drift

### At confidence threshold 0.80

Simulation output over synthetic ground truth.

| Day | Step | Shifted share % | Sample size | Automation rate % | Wrong automations | Wrong as % of automated | Rework min per 1,000 automated | Open exposure items | Reviewer min per 1,000 items | Net cost per item, INR | Net cost per item, USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | acceptance baseline | 0 | 600 | 72.3 | 17 | 4.2 | 1,049.0 | 0 | 2,651.0 | 58.9849 | 1.1797 |
| 15 | first new vendor formats | 5 | 600 | 72.0 | 26 | 6.4 | 1,317.8 | 3 | 3,279.0 | 74.3788 | 1.4876 |
| 30 | new ticket categories appear | 10 | 600 | 69.6 | 40 | 10.1 | 2,584.4 | 2 | 3,669.0 | 99.0611 | 1.9812 |
| 45 | shift established | 16 | 600 | 70.5 | 48 | 11.9 | 2,583.1 | 4 | 3,887.4 | 107.3000 | 2.1460 |
| 60 | onboarding season begins | 23 | 600 | 68.5 | 60 | 15.4 | 3,435.9 | 3 | 4,189.4 | 115.6371 | 2.3127 |
| 75 | period-end volume | 30 | 600 | 66.1 | 68 | 18.0 | 4,298.9 | 5 | 5,129.9 | 146.9454 | 2.9389 |
| 90 | ninety-day measurement | 38 | 600 | 64.3 | 83 | 23.0 | 4,778.4 | 8 | 5,511.4 | 156.9655 | 3.1393 |

Acceptance to day 90. Charter 3.17.2: both endpoints are shown, rates in percentage points and costs in percent of baseline.

| Measure | At acceptance | At day 90 | Change |
|---|---|---|---|
| Automation rate, % | 72.3 | 64.3 | -8.0 pp |
| Wrong automations as % of automated | 4.2 | 23.0 | +18.8 pp |
| Rework minutes per 1,000 automated | 1,049.0 | 4,778.4 | +355.5 % |
| Reviewer minutes per 1,000 items | 2,651.0 | 5,511.4 | +107.9 % |
| Net cost per item, INR | 58.9849 | 156.9655 | +166.1 % |
| Net cost per item, USD | 1.1797 | 3.1393 | +166.1 % |
| Open exposure items | 0 | 8 | +8 items |

### At confidence threshold 0.90

Simulation output over synthetic ground truth.

| Day | Step | Shifted share % | Sample size | Automation rate % | Wrong automations | Wrong as % of automated | Rework min per 1,000 automated | Open exposure items | Reviewer min per 1,000 items | Net cost per item, INR | Net cost per item, USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | acceptance baseline | 0 | 600 | 37.1 | 6 | 2.9 | 1,043.1 | 0 | 5,326.2 | 97.3655 | 1.9473 |
| 15 | first new vendor formats | 5 | 600 | 35.6 | 13 | 6.4 | 1,509.9 | 2 | 5,838.3 | 110.1681 | 2.2034 |
| 30 | new ticket categories appear | 10 | 600 | 34.7 | 13 | 6.6 | 2,257.6 | 0 | 6,332.5 | 126.5231 | 2.5305 |
| 45 | shift established | 16 | 600 | 34.1 | 18 | 9.2 | 1,984.6 | 3 | 6,905.2 | 138.5412 | 2.7708 |
| 60 | onboarding season begins | 23 | 600 | 31.5 | 25 | 14.0 | 3,206.7 | 1 | 7,463.2 | 147.7636 | 2.9553 |
| 75 | period-end volume | 30 | 600 | 30.9 | 29 | 16.4 | 4,271.2 | 4 | 8,417.0 | 176.4092 | 3.5282 |
| 90 | ninety-day measurement | 38 | 600 | 28.2 | 36 | 22.8 | 4,708.9 | 5 | 9,075.4 | 187.2210 | 3.7444 |

Acceptance to day 90. Charter 3.17.2: both endpoints are shown, rates in percentage points and costs in percent of baseline.

| Measure | At acceptance | At day 90 | Change |
|---|---|---|---|
| Automation rate, % | 37.1 | 28.2 | -8.9 pp |
| Wrong automations as % of automated | 2.9 | 22.8 | +19.9 pp |
| Rework minutes per 1,000 automated | 1,043.1 | 4,708.9 | +351.4 % |
| Reviewer minutes per 1,000 items | 5,326.2 | 9,075.4 | +70.4 % |
| Net cost per item, INR | 97.3655 | 187.2210 | +92.3 % |
| Net cost per item, USD | 1.9473 | 3.7444 | +92.3 % |
| Open exposure items | 0 | 5 | +5 items |

### At confidence threshold 0.95

Simulation output over synthetic ground truth.

| Day | Step | Shifted share % | Sample size | Automation rate % | Wrong automations | Wrong as % of automated | Rework min per 1,000 automated | Open exposure items | Reviewer min per 1,000 items | Net cost per item, INR | Net cost per item, USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | acceptance baseline | 0 | 600 | 14.5 | 2 | 2.4 | 622.0 | 0 | 6,808.6 | 117.1380 | 2.3428 |
| 15 | first new vendor formats | 5 | 600 | 14.4 | 4 | 4.9 | 1,036.6 | 0 | 7,203.4 | 126.4651 | 2.5293 |
| 30 | new ticket categories appear | 10 | 600 | 14.6 | 2 | 2.4 | 614.5 | 0 | 7,777.5 | 139.0260 | 2.7805 |
| 45 | shift established | 16 | 600 | 14.9 | 7 | 8.2 | 1,305.9 | 1 | 8,205.7 | 152.1747 | 3.0435 |
| 60 | onboarding season begins | 23 | 600 | 13.7 | 10 | 12.8 | 2,153.8 | 0 | 8,789.5 | 157.9774 | 3.1595 |
| 75 | period-end volume | 30 | 600 | 12.2 | 9 | 12.9 | 2,314.3 | 1 | 9,842.0 | 182.8515 | 3.6570 |
| 90 | ninety-day measurement | 38 | 600 | 9.8 | 11 | 20.0 | 2,309.1 | 2 | 10,628.5 | 194.7760 | 3.8955 |

Acceptance to day 90. Charter 3.17.2: both endpoints are shown, rates in percentage points and costs in percent of baseline.

| Measure | At acceptance | At day 90 | Change |
|---|---|---|---|
| Automation rate, % | 14.5 | 9.8 | -4.7 pp |
| Wrong automations as % of automated | 2.4 | 20.0 | +17.6 pp |
| Rework minutes per 1,000 automated | 622.0 | 2,309.1 | +271.2 % |
| Reviewer minutes per 1,000 items | 6,808.6 | 10,628.5 | +56.1 % |
| Net cost per item, INR | 117.1380 | 194.7760 | +66.3 % |
| Net cost per item, USD | 2.3428 | 3.8955 | +66.3 % |
| Open exposure items | 0 | 2 | +2 items |

## How to read the curve

The automation rate is the number a vendor deck quotes, and it is the number that moves least. Everything that decides whether the automation is worth having moves several times as far. Charter 3.14.6 exists for this reason: an automation rate published without the wrong-automation figure on the same row does not say whether the system got better or worse.

## Reproducing this page

```bash
python3 generate.py --seed 20260902
python3 drift.py --out ../../results/exception-economics-v1.0/drift.json
```

Deterministic from the seed. The same two commands on any machine reproduce every figure above, and `validate.py` fails if the ground truth on disk is not the ground truth the seed produces.
