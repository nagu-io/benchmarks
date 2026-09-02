# Day-60 rubric v1.0.0

A score out of 100 for a deployment sixty days after go-live. Ours or anyone's.

Rubric version 1.0.0 · Charter version 1.0.0 · Written 2026-09-02.

Governed by `10-benchmarks/charter/methodology.md`. Where this rubric and the charter
disagree, the charter wins until it is changed there and its version is raised. The
metric definitions this rubric scores are charter 3.18 (drift detection lead time),
3.19 (incident mean time to restore), 3.20 (rollback time) and 3.21 (report
completeness). The tier definitions are charter 4.5.

---

## 1. What this measures, and what it does not

1.1 Day-60 measures whether a deployment is still trustworthy two months after it went
live. It measures the operations around a system: whether the monitoring sees a change
in the input, whether anyone acts on what the monitoring saw, how long a restoration
takes, whether a rollback is a rehearsed procedure or an argument, and whether the
monthly report is evidence or decoration.

1.2 It does not measure model quality at all. That is the point of running it beside
Messy Scan, Honest Containment and Exception Economics. A deployment can score highly
here on a weak model and poorly on a strong one, and both of those outcomes are
information a partner needs before signing a second statement of work.

1.3 It is a rubric, not a dataset. It is run against a live deployment, by a person,
under the safety conditions in `scripted-incidents.md` section 2. Nothing in this
folder can be scored from a file.

1.4 A Day-60 score is comparable only with another Day-60 score run at the same tier
and at the same rubric version. Both travel with the number, always, in this form:

> Day-60 score 00 of 100 achievable · tier T0 · rubric v1.0.0 · exercised
> 0000-00-00 to 0000-00-00

---

## 2. Tiers

2.1 From charter 4.5. The tier describes the exercise, not the deployment. A harder
tier is a harder test, so a score without its tier is not a score.

| Tier | Environment | Drift injected | Incident | Rollback | Report audit |
|---|---|---|---|---|---|
| T1 | Non-production copy | One class, announced window | One Severity 3, scripted | Rehearsed on the copy | One month |
| T2 | Live-like environment at production-shaped volume | One class, unannounced within an agreed exercise period | One Severity 2, scripted | Performed during an agreed change window | One month |
| T3 | Production, within the change-window rules of the statement of work | Two concurrent signals, for example input drift and a confidence shift | One Severity 2 requiring a partner dependency to resolve | Performed, with the re-queue of affected items measured | Three months |
| T4 | Production | A class with no labelled examples | A Severity 1 exercised as a tabletop only | Performed, including a data restore from backup | Three months, spanning a provider model version change |
| T5 | Production | As T4, and the exercise is initiated by the partner without prior notice to the delivery team, inside the rules the statement of work allows | As T4 | As T4 | Three months, spanning a provider model version change and a threshold change |

2.2 The self-assessment version in `self-assessment.md` is capped at T2, because the
higher tiers require the ability to change a production configuration (charter 4.5.2).

---

## 3. How the score is built

3.1 One hundred points, all of them allocated below. No discretionary points, no
overall impression mark, and no weighting a supplier can argue about after the fact.

| Section | What it scores | Points |
|---|---|---|
| A | Drift detection and notice | 25 |
| B | Incident response and communication | 25 |
| C | Rollback | 20 |
| D | Monthly report completeness | 20 |
| E | Evidence and reproducibility | 10 |
| | **Total** | **100** |

3.2 Every line is one of three kinds, and each kind has one scoring rule.

| Kind | Rule |
|---|---|
| **Ratio line** | The observed time is divided by the target for that measure in the statement of work. Bands in 3.3 |
| **Checklist line** | A stated list of elements, one point each, present or absent. No partial element |
| **Computed line** | An arithmetic formula stated on the line, applied to counts the assessor records |

3.3 Bands for every ratio line. `r` is observed divided by target.

| Condition | Points |
|---|---|
| `r` at or below 1.00 | Full points for the line |
| `r` above 1.00 and at or below 2.00 | Half the line's points, rounded down to a whole point |
| `r` above 2.00 | 0 |
| Not achieved before the exercise window closed | 0, recorded as "not achieved within the window", with the window length. Never extrapolated to a longer window (charter 3.18.5) |
| The statement of work states no target for this measure | 0, recorded as "no target in the contract" |

3.4 A line scored 0 for "no target in the contract" is not a failure of the delivery
team, and the report says so on the line. It is a gap in the contract, and it is the
most common finding this rubric produces against an incumbent supplier. The absence of
a target is why the line cannot be scored, and scoring it as a pass would reward the
absence.

3.5 Lines not exercised. Where a line could not be exercised, for example because the
safety conditions in `scripted-incidents.md` section 2 could not be met, it is scored
"not exercised" and removed from **both** the points awarded and the points
achievable. It is never assumed, never given a default and never given the benefit of
the doubt (charter 4.5.1).

3.6 The reported score. Points awarded divided by points achievable, times 100, to one
decimal place, with the achievable total printed beside it. A score with any line not
exercised is never compared with a full-scope score, and the report states which lines
were not exercised.

3.7 Two assessors. Every line is scored independently by two assessors from the same
evidence pack. Where they agree, the score stands. Where they disagree:

| Situation | Resolution |
|---|---|
| A ratio line, disagreement about a timestamp | The timestamp from the system record wins over the timestamp from a person's account. If both are system records, the earlier start and the later end win, which is the reading least favourable to the supplier |
| A checklist line, disagreement about whether an element is present | The element is absent unless the evidence pack contains it. An element described in conversation and not in the pack is absent |
| A computed line | Recompute from the recorded counts. A computed line cannot be disputed except by disputing a count |
| Anything else | The lower score stands, and the disagreement is recorded on the line |

3.8 Every line requires named evidence, listed on the line below and recorded in
`scoresheet.csv`. A line with no evidence reference is scored 0 whatever the assessors
believe happened. This rule is the whole rubric in one sentence: an unsupported figure
in a supplier report is the problem the charter exists to address, and an unsupported
score in this rubric would be the same problem wearing a different hat.

---

## 4. Section A — drift detection and notice, 25 points

Scores exercise D-1 in `scripted-incidents.md`. Charter 3.18.

### A1. Detection lead time, 8 points — ratio line

**Measured.** Hours from the onset timestamp, being the first input item belonging to
the shifted population, to the internal alert or ticket that records the drift.

**Target.** The detection target in the statement of work. Where the statement of work
sets only a notice target, the detection line uses that same target and the fact is
recorded on the line.

**Evidence required.** The exercise owner's injection log, holding the onset timestamp,
which the delivery team does not see in advance. The alert record or ticket, with its
system timestamp. Both are copied into the evidence pack.

**Scored 0 if.** The drift was not detected before the exercise window closed. Record
"not detected within the window" and the window length.

### A2. Notice lead time, 8 points — ratio line

**Measured.** Hours from the same onset timestamp to the written notice reaching the
partner, naming the affected class and giving the supporting evidence. Reported in
hours and in business hours; the ratio uses whichever unit the statement of work's
target is expressed in.

**Target.** The notice target in the statement of work.

**Evidence required.** The notice itself, with its delivery timestamp from the mail or
ticket system, not from the sender's account of when it was sent.

**Why this is separate from A1.** Charter 3.18.1 runs two clocks because they answer
different questions. A1 asks whether the monitoring saw it. A2 asks whether anyone
acted on what the monitoring saw. The gap between them is the part a partner never
sees in a supplier's own reporting.

### A3. Notice content, 5 points — checklist line

One point for each element present in the written notice. No partial credit.

| # | Element |
|---|---|
| 1 | Names the affected class or population in terms the partner can act on, not only an internal identifier |
| 2 | States the onset the supplier believes applies, and how it was established |
| 3 | States the count of items affected so far, with the period the count covers |
| 4 | States what the supplier has done and what it proposes to do, with a date |
| 5 | States the effect on any measure that carries a floor or a ceiling in the statement of work, or states explicitly that there is none |

### A4. False-alert accounting, 4 points — computed line

**Why.** Charter 3.18.4: a monitoring system that alerts constantly also has a lead
time near zero and is worth nothing. Lead time is not scored without this line.

| Condition | Points |
|---|---|
| The false-alert count for the exercise period is recorded, and is at or below the tolerance in the statement of work | 4 |
| Recorded, and above the tolerance | 2 |
| Recorded, and the statement of work states no tolerance | 2, with "no tolerance in the contract" recorded |
| Not recorded | 0 |

**Evidence required.** The alert log for the exercise period, and the record of which
alerts were withdrawn as false.

---

## 5. Section B — incident response and communication, 25 points

Scores exercise I-1 in `scripted-incidents.md`, at the severity the tier states.
Charter 3.19.

### B1. Acknowledgement, 5 points — ratio line

**Measured.** Elapsed time from the start of the incident clock to acknowledgement by a
named engineer. The clock starts at the earlier of the supplier's own detection
timestamp and the partner's notice timestamp, not the time the ticket was opened and
not the time an engineer picked it up (charter 3.19.3).

**Target.** The response target for that severity in the ops retainer schedule clause
3.1, as completed in the statement of work.

**Evidence required.** Ticket timestamps for both ends. Where the supplier detected the
incident itself, the monitoring record showing the detection time.

### B2. Time to restore, 10 points — ratio line

**Measured.** Elapsed time from the same clock start to the moment a monitoring check
confirms that work submitted at intake reaches an output or the review queue within
the service level. Not the time the ticket was closed, and not the time the root cause
was found (charter 3.19.4).

**Target.** The resolution target for that severity in the ops retainer schedule clause
3.1, as completed in the statement of work.

**Excluded from the elapsed time, and reported separately.** Time waiting on a partner
dependency, which stops the clock. The waiting total is recorded on the line so that
neither party can hide inside the other's delay (charter 3.19.5). At tier T3 and above
the incident requires a partner dependency, so this figure is always present there.

**Evidence required.** The monitoring check that confirmed restoration, with its
timestamp and its result. A ticket marked resolved without a confirming check does not
satisfy this line.

### B3. Communication during the incident, 5 points — checklist line

One point each.

| # | Element |
|---|---|
| 1 | The partner was told, by the supplier, before the partner asked |
| 2 | The first message named the severity and the systems affected |
| 3 | Updates arrived at the interval the statement of work states, or better, with no gap longer than that interval until restoration |
| 4 | The messages distinguished what was known from what was suspected |
| 5 | A closing message confirmed restoration and stated the confirming check |

### B4. Post-incident record, 5 points — checklist line

One point each. The record must exist within five business days of restoration; a
record produced later scores 0 on this line whatever it contains.

| # | Element |
|---|---|
| 1 | A timeline with system timestamps, not a narrative |
| 2 | The cause, or a plain statement that the cause is not yet established, with the next step and a date |
| 3 | The count of items affected, and how that count was established |
| 4 | What was done for the affected items, including any re-queue or re-processing |
| 5 | A corrective action with a named owner and a date |

---

## 6. Section C — rollback, 20 points

Scores exercise R-1 in `scripted-incidents.md`. Charter 3.20.

### C1. Decision time, 4 points — ratio line

**Measured.** Minutes from the rollback criterion being met to the on-call engineer
recording the decision.

**Target.** The decision target in the statement of work. Where none exists, charter
3.20 offers no default and the line is scored 0 with "no target in the contract".

**Why.** A rollback that takes four minutes after a two-hour argument is not fast
(charter 3.20.3).

### C2. Rollback time, 8 points — ratio line

**Measured.** Minutes from the decision being recorded to the previous signed release
serving production traffic and passing the smoke set with its model pin, prompt version
and threshold set restored.

**Target.** The rollback target in the statement of work.

**Evidence required.** The smoke-set result on the restored release, with its timestamp.

**Labelling.** A rehearsal on a non-production copy is scored on this line at tier T1
only, and the score line is marked "rehearsal". A rehearsal figure is never placed in
the same table as a rollback performed on production (charter 3.20.4).

### C3. Re-queue completion, 5 points — ratio line

**Measured.** Minutes from the decision being recorded to every item processed by the
rolled-back release being identified and re-queued for review.

**Target.** The re-queue target in the statement of work.

**Why.** A rollback that restores the service quickly and leaves the outputs of a bad
release sitting in the partner's downstream systems is not finished.

**Scored 0 if.** The supplier cannot identify which items the rolled-back release
processed. Record "affected items not identifiable", which is a finding in its own
right and belongs in the exercise report whatever the rest of the section scores.

### C4. Restored configuration proven, 3 points — checklist line

One point each. Each element requires the value to be shown from the running system
after the rollback, not from a deployment plan.

| # | Element |
|---|---|
| 1 | The model version pin in force after the rollback matches the previous signed release |
| 2 | The prompt version in force after the rollback matches the previous signed release |
| 3 | The threshold set in force after the rollback matches the previous signed release |

---

## 7. Section D — monthly report completeness, 20 points

Scores exercise A-1 in `scripted-incidents.md`. Charter 3.21.

### D1. Completeness, 12 points — computed line

**Formula.** Points = round( elements present and passing ÷ elements required × 12 ).

**Denominator.** The ten elements of `01-legal/ops-retainer-schedule.md` clause 5.2,
plus any element the statement of work adds. The denominator is recorded on the line,
because it differs per statement of work.

| # | Element required by clause 5.2 |
|---|---|
| 1 | Volumes: received, processed, straight through, routed to review, rejected, by day and in total |
| 2 | Automation rate |
| 3 | Exception rate against the ceiling |
| 4 | Accuracy against the floor, with the sample size and the method |
| 5 | Incidents: each one with severity, times, cause and preventive action, and the service level results |
| 6 | Changes: each change deployed, its window, its purpose and its result |
| 7 | Drift observations, the checks run, and any retraining or re-evaluation performed or recommended |
| 8 | Next month's actions, partner dependencies needed, and risks the supplier sees |
| 9 | Uptime and the service level table with each result marked met or not met |
| 10 | Service credits accrued, if any |

**An element passes only if** it is present, covers the whole reporting period, and
carries its sample size or its basis where it is a figure. An element that is present
and gives a figure without its sample size or its basis **fails** (charter 3.21.3).
This is the single most common failure this rubric finds, and it is not a technicality:
an unsupported figure in a partner report is the problem the whole charter exists to
address.

**Elements that do not apply in the period** pass if the report states "none"
explicitly, and fail if they are simply absent. The count of not-applicable elements is
recorded on the line (charter 3.21.5).

**Where the audit covers three months** (tiers T3 and above), the line is scored on
each month separately and the points are the mean of the three, rounded to a whole
point. The three monthly ratios are all recorded.

### D2. Changes stated with their dates, 4 points — checklist line

One point each. Each element scores only if the change is stated **with its date**.

| # | Element |
|---|---|
| 1 | Every confidence threshold change in the period is stated with its date |
| 2 | Every provider model version change in the period is stated with its date, including changes the provider made behind an unchanged model name |
| 3 | Every prompt or configuration version change in the period is stated with its date |
| 4 | Where any of the three occurred, the report restates the affected measure at both the old and the new configuration, or states plainly that it has not |

**Why this is its own line.** Charter 3.5.7 requires a threshold change and its date in
the monthly report, because the exception rate is a function of the threshold and moves
the moment the threshold does. A report that shows an improved exception rate and does
not mention that the threshold moved is not wrong on any single figure, and is not
usable.

### D3. Timeliness, 4 points — banded line

Scored separately from completeness. A complete report delivered late and an incomplete
report delivered on time are different failures and are not averaged together (charter
3.21.6).

| Condition | Points |
|---|---|
| Delivered on or before the fifth business day of the following month | 4 |
| Delivered after the fifth and on or before the tenth business day | 2 |
| Delivered later, or not delivered | 0 |

**Evidence required.** The delivery timestamp from the mail or portal system.

---

## 8. Section E — evidence and reproducibility, 10 points

The section that decides whether the other ninety points mean anything.

### E1. Timestamps come from system records, 5 points — checklist line

One point for each of the five timestamps below, where the assessor obtained it from a
system record rather than from a person's account. A system record is a log line, a
ticket field, a mail header, a monitoring result or a deployment record. A screenshot
of one counts; a person's recollection does not, however confident.

| # | Timestamp |
|---|---|
| 1 | The drift onset, from the exercise owner's injection log |
| 2 | The internal alert or ticket that recorded the drift |
| 3 | The written notice to the partner |
| 4 | The monitoring check confirming restoration after the incident |
| 5 | The smoke-set pass on the restored release after the rollback |

### E2. A reported figure can be reproduced, 5 points — checklist line

The assessor picks one figure from the monthly report before the exercise begins, names
it in the evidence pack, and asks the supplier to reproduce it.

| # | Element | Points |
|---|---|---|
| 1 | The report states the sample or population, the configuration in force and the period the figure came from | 2 |
| 2 | The supplier produced the underlying records within the exercise window | 2 |
| 3 | The recomputed figure matches the reported one within the rounding the report states | 1 |

**Note on element 3.** A mismatch scores 0 on that element and is recorded with both
figures. It is not by itself evidence of anything worse than a spreadsheet, and the
exercise report says so rather than implying more.

---

## 9. Reporting the score

9.1 The score is reported in this form and no other:

> Day-60 score **00.0** of **100** achievable · tier **T0** · rubric **v1.0.0** ·
> exercised **0000-00-00 to 0000-00-00** · assessors **two, named** · lines not
> exercised: **none**

9.2 Section subtotals are always published beside the total. A total of 70 built from a
strong report and no rollback is a different deployment from a total of 70 built the
other way round, and a single number cannot tell them apart.

9.3 Every line scored 0 for "no target in the contract" is listed separately, under the
heading "not scorable because the contract sets no target". That list is the most
useful output of the exercise for a partner about to renew.

9.4 What a score means. The bands below are the rubric's own statement of what it
asserts, not a market claim about anyone.

| Band | What the evidence supports |
|---|---|
| 85 to 100 | Every exercised measure met its contractual target, the report is complete and supported, and the timestamps came from systems |
| 70 to 84 | The operations work, with one or two measures outside target or one report element unsupported |
| 50 to 69 | The deployment runs and the operations around it are informal. Expect the gaps to appear under load rather than in an exercise |
| Below 50 | The measures either were not met or could not be evidenced. Which of those two applies matters more than the number, and section 9.3 is where a reader finds out |

9.5 A partial exercise is reported as a partial exercise. Charter 5.8: a system that
cannot complete a suite is reported with the reason, a partial figure is never promoted
into a headline, and an incomplete row is never compared with a complete one.

---

## 10. Point allocation in full

Every point in the rubric, in one table, so that a reader can check the arithmetic
without reading the sections.

| Line | Section | Kind | Points |
|---|---|---|---|
| A1 Detection lead time | A | Ratio | 8 |
| A2 Notice lead time | A | Ratio | 8 |
| A3 Notice content | A | Checklist, 5 elements | 5 |
| A4 False-alert accounting | A | Computed | 4 |
| B1 Acknowledgement | B | Ratio | 5 |
| B2 Time to restore | B | Ratio | 10 |
| B3 Communication during the incident | B | Checklist, 5 elements | 5 |
| B4 Post-incident record | B | Checklist, 5 elements | 5 |
| C1 Decision time | C | Ratio | 4 |
| C2 Rollback time | C | Ratio | 8 |
| C3 Re-queue completion | C | Ratio | 5 |
| C4 Restored configuration proven | C | Checklist, 3 elements | 3 |
| D1 Completeness | D | Computed | 12 |
| D2 Changes stated with their dates | D | Checklist, 4 elements | 4 |
| D3 Timeliness | D | Banded | 4 |
| E1 Timestamps come from system records | E | Checklist, 5 elements | 5 |
| E2 A reported figure can be reproduced | E | Checklist, 3 elements | 5 |
| **Total** | | | **100** |

Section totals: A 25, B 25, C 20, D 20, E 10.

---

## 11. Status

11.1 No Day-60 exercise has been run. The rubric is written; the score is not.

11.2 Running one requires, and no agent can supply: a partner and a deployment willing
to be exercised, a written agreement under the safety conditions in
`scripted-incidents.md` section 2, a named owner who can stop the exercise, a rollback
owner on call for its duration, a statement of work whose targets the ratio lines can
be scored against, and two assessors.

11.3 `scoresheet.csv` holds the structure and the formulas with no scores in it. It
stays that way until an exercise happens.
