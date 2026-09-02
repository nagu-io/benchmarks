# Exception Economics v1.0 — findings

Dataset `exception-economics` version 1.0.0 · seed 20260902 · ground truth sha256 `49af7a5ee30fb3fc` · scorer version 1.0.0 · charter version 1.0.0 · run date 2026-09-02 · ground truth synthetic.

## What these findings are, and are not

No system has been run against this dataset, so there is no finding here about any model, service or vendor, and none will be written until a run exists. What follows are findings about the measurement itself: what the arithmetic of a cost model does to an automation rate, and which numbers move when the input moves. Every one is tied to a table in `leaderboard.md` or `drift.md`, and every one rests on synthetic ground truth scored with a synthetic reference decision policy.

## 1. The headline metric is the one that moves least

In the drift simulation at threshold 0.80, the automation rate falls 8.0 percentage points between acceptance and day 90, from 72.3 percent to 64.3 percent. Over the same steps the wrong-automation rate rises 18.8 percentage points and the net cost per item rises 166 percent.

A monthly report carrying only the automation rate would describe that quarter as stable. Table: `drift.md`, live-distribution drift at threshold 0.80.

## 2. Net cost per item is not monotonic in the threshold

Across the sweep from 0.50 to 0.99, net cost per item falls, reaches a minimum of INR 51.3600 at threshold 0.68, and then rises to INR 118.2131 at threshold 0.95. The most cautious threshold in the sweep costs 130 percent more per item than the cheapest.

Caution is not free. It is paid for in reviewer minutes, which rise from 1,638.8 per 1,000 items at the minimum to 6,845.1 at threshold 0.95. Table: `leaderboard.md`, the threshold that minimises net cost.

## 3. Raising the threshold hides the exposure rather than removing it

Open exposure items, wrong automations in classes with no detection route inside the window, fall from 3 at threshold 0.80 to 0 at threshold 0.95 in the baseline sample. In the drift simulation at day 90 the same count is 8 at threshold 0.80 and 2 at threshold 0.95.

The count falls because fewer items are automated at all, not because the process acquired a way of finding the errors. Nothing in the model detects them at any threshold. Tables: `leaderboard.md`, wrong-automation rework by error class; `drift.md`, live-distribution drift.

## 4. The tier is where the cost sits, not the average

At threshold 0.80, tier 1 automates 83.4 percent of 320 items with 1 wrong automation. Tier 5 automates 55.8 percent of 163 items with 19 wrong. The wrong-automation rate of automated items is 0.4 percent at tier 1 and 20.9 percent at tier 5.

A headline figure over a mix is a statement about the mix as much as about the policy, which is why charter 4.1.4 makes the mix travel with the number. Table: `leaderboard.md`, per tier.

## 5. Equal automation rates across work types do not mean equal cost

At threshold 0.80, know-your-customer cases automate at 70.8 percent and ticket triage at 73.5 percent. On the automation rate alone the two look like the same piece of work.

They are not. The 119 know-your-customer exceptions take 1,874.0 reviewer minutes; the 169 ticket exceptions take 997.2, a factor of 1.9 on a comparable count. The rework is further apart still: 309.0 minutes against 209.0.

One threshold across a mixed queue is a choice to be wrong in one direction on part of it, and a single blended automation rate does not show which part. Table: `leaderboard.md`, per work type.

## 6. The mean reviewer minute is a weak number without the entry code

At threshold 0.80 the mean is 10.21 minutes per exception and the median is 7.60. By entry code the mean runs from 4.12 minutes on 18 processing failures to 27.50 minutes on 26 policy flags, a factor of 6.7.

A queue redesign that moves items between codes moves the mean without changing anyone's workload. Charter 3.16.1 requires the breakdown for that reason. Table: `leaderboard.md`, reviewer minutes by queue entry code.

## 7. The cheapest exception to triage creates the most work

Processing failures are the shortest exception in the model, 4.12 minutes each at threshold 0.80. The items behind them still have to be done: 203.0 minutes of manual handling, against 74.1 minutes of triage.

That manual handling sits outside the charter's net cost composition, so it is reported beside it rather than inside it. A supplier reporting only reviewer minutes per exception would show a processing failure as the cheapest thing it does. Table: `leaderboard.md`, reported separately.

## 8. Exclusions are large enough to move a rate on their own

Of 1,700 items received, 44 were rejected before processing by a named rule, 23 were abandoned when an upstream system was unavailable and 24 were open at window close, leaving 1,609 admitted.

Moving those exclusions in or out of the denominator moves the automation rate without changing a single decision, which is why charter 3.1.2 counts each of them beside the figure it was excluded from. Table: `leaderboard.md`, denominators.

## What is still missing

Every finding above concerns the measurement. None concerns a system. The suite produces a system row the moment a decision policy with real predictions is supplied through `score.py --predictions`, and until then the leaderboard's system table stays empty rather than illustrated.
