# Exception Economics — one page for a chief financial officer

Dataset `exception-economics` version 1.0.0 · seed 20260902 · ground truth sha256 `49af7a5ee30fb3fc` · scorer version 1.0.0 · charter version 1.0.0 · run date 2026-09-02 · ground truth synthetic.

## Read this first

This page contains no measured claim about any vendor's system, because no vendor's system has been run. It contains the arithmetic of a cost model with placeholder inputs, applied to synthetic items with known answers. Its use is to show which numbers decide the business case and how far they move each other. It is not a quotation, a benchmark result or a saving.

Every money input to it is a placeholder and is marked as such in every table below. Replace them with your own figures and the arithmetic holds; leave them and the money columns mean nothing on their own.

## The one thing worth taking from this page

Automation rate is not a result. A policy that automates more can cost more, because the work created by a wrong automation is not the work saved by a right one, and because some wrong automations are never found at all.

## The model, in full

| Input | Value | Status |
|---|---|---|
| Fully loaded reviewer cost, INR per hour | 1,000.00 | placeholder — replace with your own fully loaded cost |
| Fully loaded reviewer cost, USD per hour | 20.00 | placeholder — replace with your own fully loaded cost |
| Exchange rate applied between the two | none | the two rates are independent placeholders; no rate is applied and none should be inferred |
| Machine cost per item | 0.00 | no system has been run, so no measured cost per item exists |
| Reviewer minutes per exception | see the labour model | modelling assumptions, each with its basis stated; none measured |
| Rework minutes per wrong automation | see the labour model | modelling assumptions, each with its basis stated; none measured |
| Items | 1,609 admitted | synthetic, with known answers |

## What the arithmetic gives

Per item admitted, across 1,609 items, at three confidence thresholds.

| Confidence threshold | Automation rate % | Reviewer min per 1,000 items | Rework min per 1,000 automated | Net cost per item, INR | Net cost per item, USD | Wrong automations nobody would find |
|---|---|---|---|---|---|---|
| 0.80 | 72.2 | 2,842.3 | 899.2 | 61.5474 | 1.2309 | 3 |
| 0.90 | 37.4 | 5,374.9 | 890.2 | 98.4845 | 1.9697 | 1 |
| 0.95 | 14.6 | 6,845.1 | 314.9 | 118.2131 | 2.3643 | 0 |

Raising the threshold from 0.80 to 0.95 cuts the automation rate from 72.2 percent to 14.6 percent and raises the net cost per item from INR 61.5474 to INR 118.2131, at the placeholder rate. In USD, from 1.2309 to 2.3643, at the other placeholder rate. Both movements are the same arithmetic seen in two currencies, not two observations.

## The threshold that minimises cost, in this model

| Figure | Value |
|---|---|
| Minimising threshold | 0.68 |
| Automation rate there, % | 86.9 |
| Net cost per item, INR | 51.3600 |
| Net cost per item, USD | 1.0272 |
| Net cost per item at threshold 0.95, INR | 118.2131 |
| Difference, percent of the minimum | +130.2 |

The minimum sits below the lowest of the three published thresholds. Where a real system's minimum sits depends on how well its confidence is calibrated, which is measured, not assumed, and which nobody has measured here.

## What ninety days of input drift does to the same model

Simulation output over synthetic ground truth. At threshold 0.80, comparing the acceptance measurement with day 90.

| Measure | At acceptance | At day 90 | Change |
|---|---|---|---|
| Automation rate, % | 72.3 | 64.3 | -8.0 pp |
| Net cost per item, INR | 58.9849 | 156.9655 | +166.1 % |
| Net cost per item, USD | 1.1797 | 3.1393 | +166.1 % |
| Wrong automations nobody would find | 0 | 8 | +8 items |

The automation rate falls 8.0 percentage points, which a monthly report would describe as broadly stable. The net cost per item rises 166 percent over the same ninety days. That gap between the reported measure and the cost measure is the reason this suite exists.

## The line that carries no number

Three of the eleven error classes in the labour model have no detection route inside a monthly measurement window: a support ticket that needed escalation and was closed as routine, a know-your-customer case wrongly passed, and an invoice exception wrongly posted. Nothing in the process looks for them. They are counted and named as open exposure and they are never priced, because a detection time invented for an error nobody would find is exactly the kind of figure that makes a business case look better than the business.

At threshold 0.80 the simulation leaves 3 such items in the baseline sample and 8 at day 90 of the drift simulation. Those counts are the honest form of that risk. A money figure beside them would not be.

## Three questions this page equips you to ask a supplier

1. At what confidence threshold is your quoted automation rate measured, and what is the wrong-automation rate on the same row at the same threshold.
2. Which of your error classes has no detection route inside a monthly window, and how many items were in those classes last month.
3. What were the automation rate and the net cost per item at acceptance, and what were the same two figures ninety days later, with both endpoints and both sample sizes.

The contract language for all three is in `10-benchmarks/charter/contract-clauses.md`, clauses 13 to 16.

