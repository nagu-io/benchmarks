# Day-60 self-assessment

Run this against your current supplier in one afternoon. No engineering, no access to
anything, no permission from anybody. A meeting room, the last three monthly reports,
and someone from the supplier who can answer questions.

Version 1.0.0 · Charter version 1.0.0 · Written 2026-09-02.

---

## What this is

The full Day-60 exercise in `rubric.md` injects a drift, triggers an incident and
forces a rollback against a live deployment. That takes a written agreement, a change
window and two weeks. This version asks for the same evidence about things that have
already happened, and it takes an afternoon.

**The two scores are not the same measurement, and they are never compared.** A full
exercise measures what a supplier does under a test. This measures what a supplier can
show you about what it has already done. A supplier can score well here and badly
there. Write the score as:

> Day-60 self-assessment 00 of 100 achievable · from records, no exercise run ·
> version 1.0.0 · assessed 0000-00-00

The charter caps the self-assessment at tier T2 for the same reason: the harder tiers
need the ability to change a production configuration, and you have no such ability
over someone else's system.

---

## What this is worth

Most of the value is not the number. It is the list at the end of every section headed
"no target in the contract". A measure with no target cannot be missed, cannot be
enforced and cannot be improved on any schedule you control. If the afternoon produces
nothing else, it produces that list, and that list is what a renewal conversation is
made of.

---

## Before the afternoon

Send this list five working days ahead. Ask for it in writing. What arrives, and what
does not, is itself part of the answer.

| # | Ask for |
|---|---|
| 1 | The last three monthly reports, as delivered, not re-exported |
| 2 | The delivery timestamp of each of those three reports |
| 3 | Every incident record from the last three months, whatever the severity |
| 4 | Every drift observation from the last three months, with the dates it was detected and the date you were told |
| 5 | The alert log, or a count of alerts raised and of alerts withdrawn as false, for the last three months |
| 6 | The record of the most recent rollback or rollback rehearsal, with its dates and times |
| 7 | The list of changes deployed in the last three months, with dates |
| 8 | The current confidence thresholds, and the date each was last changed |
| 9 | The current model version and the date it last changed, including changes the provider made behind an unchanged name |
| 10 | The contract, the statement of work and the service level schedule, whichever hold the targets |

Nobody needs to build anything. Every item on that list either exists or does not, and
which of those two is true is most of what you are trying to find out.

**Who to have in the room.** One person from the supplier who can answer without
checking, one person from your operations who sees the queue every day, and you. Ninety
minutes is enough for the questions; the rest of the afternoon is reading.

---

## How to score

Every question below scores full points, half, or zero. The rules:

- **Full** only if the evidence is in front of you. Not described, not promised, not
  "we could pull that". In front of you, on the day.
- **Half** if the evidence exists but is incomplete, late, or came from a person rather
  than from a system.
- **Zero** if it does not exist, or if it exists and does not answer the question.
- **No target in the contract** scores zero, and goes on the list. That is not the
  supplier's failure. It is yours and theirs jointly, and it is fixable at the next
  renewal.
- **Not applicable** where nothing of the kind happened in the period. Remove those
  points from your achievable total rather than awarding them, and write the achievable
  total beside the score.

Half points round down to a whole point.

---

## Section A — do they notice when the work changes, 25 points

The single most useful thing to know about a supplier at day sixty. Every process
changes: new senders, new formats, new categories, a busy season. The question is
whether they see it before you do.

### A1. When did they last tell you the input had changed. 8 points

**Ask:** "In the last three months, what changed about the work coming in, when did you
first see it, and when did you tell us."

| | |
|---|---|
| **A good answer** | Names a specific change, gives a date it started, a date it was detected and a date you were told, and the three dates are different and all in the record |
| **A weak answer** | "Nothing has changed." Volume in a back office is never that stable, and a supplier that has seen nothing in three months is a supplier that is not looking |
| **Another weak answer** | A change you raised, presented as one they found |

**Score.** 8 if they detected a change themselves and the dates come from records. 4 if
they detected it but the dates come from memory, or if the only changes recorded are
ones you raised. 0 if there is no record of any drift observation.

### A2. How long between them seeing it and you hearing about it. 8 points

**Ask:** "For that change, how many hours or days between the detection and the written
notice to us, and what does the contract require."

| | |
|---|---|
| **A good answer** | A number in hours or business hours, taken from two timestamps, and a target in the contract it is measured against |
| **A weak answer** | "It went into the monthly report." A monthly report is not a notice. A change that started on the second of the month and reached you on the fifth of the next is thirty-three days of items you did not know about |
| **A weak answer** | "We'd tell you straight away." A description of intent, with no instance |

**Score.** 8 if the gap is within the contract's notice target. 4 if there is a
measured gap but it is outside the target, or if the notice was the monthly report and
nothing sooner. 0 if there is no record of a notice, or if the contract sets no notice
target, in which case write it on the list.

### A3. What was in the notice. 5 points

Take the last written notice they sent you about a change in the work. One point for
each of these five things being in it.

| # | Is it in the notice |
|---|---|
| 1 | What changed, in words your operations team can act on |
| 2 | When it started, and how they worked that out |
| 3 | How many items were affected, and over what period |
| 4 | What they did, what they will do, and by when |
| 5 | The effect on any figure that has a floor or a ceiling in the contract, or a plain statement that there is none |

**A weak answer** is a notice that says a change was observed and is being monitored.
That is a sentence, not a notice. It scores 1 out of 5 at best.

### A4. How often do their alerts turn out to be nothing. 4 points

**Ask:** "How many alerts fired in the last three months, and how many were withdrawn
as false."

**Why this question.** A monitoring system that alerts constantly also has a very short
detection time and is worth nothing, because nobody reads it any more. A supplier who
cannot tell you the false-alert rate cannot tell you what their detection time means.

**Score.** 4 if both counts exist and the false rate is at or below a tolerance the
contract states. 2 if both counts exist and there is no tolerance in the contract, or
the rate is above it. 0 if the counts do not exist.

---

## Section B — what happens when something breaks, 25 points

Use the most recent incident of any severity. If there has been none in three months,
ask for the most recent one at all, and note the date. A supplier with no incident in a
year is either very good or not recording them, and the records tell you which.

### B1. How quickly did a named person pick it up. 5 points

**Ask:** "Show me the ticket. When did the clock start, and when did a named engineer
acknowledge it."

**A good answer** starts the clock at the earlier of their own detection and your
report, not at the time the ticket was created. Those are different, sometimes by
hours, and the difference is always in the supplier's favour when it is not checked.

**Score.** 5 if the acknowledgement is inside the contract's response target for that
severity, measured from the right start. 2 if it is inside twice the target, or the
clock started at ticket creation. 0 if it is outside twice the target, or the contract
sets no response target.

### B2. How long until the work was flowing again. 10 points

**Ask:** "When did work submitted at intake start reaching an output or the review queue
again, and what confirmed it."

| | |
|---|---|
| **A good answer** | A timestamp from a monitoring check, and the check itself |
| **A weak answer** | The time the ticket was closed. A closed ticket is an administrative event |
| **A weak answer** | The time the cause was found. Finding the cause is not restoring the service, and the two can be days apart |

**Score.** 10 if restoration is inside the contract's resolution target for that
severity, confirmed by a check. 5 if inside twice the target, or if the only evidence
is a ticket closure. 0 if outside twice the target, or if the contract sets no
resolution target.

**Ask also:** "Was any of that time spent waiting on us." A supplier who tracks that
separately is measuring honestly. A supplier who has never separated it is reporting a
number that contains your delay as well as theirs, in whichever direction suits.

### B3. How did they tell you, while it was happening. 5 points

One point each, from the messages themselves.

| # | Is it true |
|---|---|
| 1 | They told you before you asked |
| 2 | The first message named the severity and what was affected |
| 3 | Updates kept coming at a regular interval, with no long silence, until it was fixed |
| 4 | The messages were clear about what was known and what was still a guess |
| 5 | A final message confirmed it was fixed and said what confirmed it |

### B4. What did they write down afterwards. 5 points

One point each. The record has to exist within five working days of the fix; a record
written later scores zero on this question whatever it contains.

| # | Is it in the record |
|---|---|
| 1 | A timeline with real timestamps, not a paragraph |
| 2 | The cause, or a plain statement that it is not yet known, with a next step and a date |
| 3 | How many items were affected, and how that was counted |
| 4 | What was done for those items |
| 5 | A corrective action with a named owner and a date |

**A weak answer** is a record whose corrective action is "monitoring has been improved".
That has no owner and no date, so nothing happens on a schedule you can check.

---

## Section C — can they put it back, 20 points

The question behind this section: if a change made things worse on a Tuesday, what
happens on the Tuesday.

### C1. How long from the problem being clear to someone deciding. 4 points

**Ask:** "The last time you rolled back, when did you know you needed to and when did
someone decide."

**Why.** A rollback that takes four minutes after a two-hour argument is not fast. Most
suppliers measure the four minutes.

**Score.** 4 if the decision time is inside a target in the contract. 2 if there is a
recorded decision time and no target. 0 if there is no recorded decision time.

### C2. How long the rollback itself took. 8 points

**Ask:** "From the decision, how long until the previous version was serving and had
passed its checks."

**A good answer** includes the check that was run on the restored version, and its
result. **A weak answer** is the deployment time alone: a deployment that completes and
is not verified is a change, not a rollback.

**Score.** 8 if inside a target in the contract, verified by a check. 4 if inside twice
the target, or if it was a rehearsal on a copy rather than a real rollback, or if there
is no verifying check. 0 if there has never been a rollback or a rehearsal, or if the
contract sets no target.

**If they have never rolled back or rehearsed one**, that is the answer. Score 0 and
write it down. The first rollback in a live process is not the one you want to be
timing.

### C3. What happened to the work the bad version had already touched. 5 points

**Ask:** "How did you find the items the rolled-back version had processed, and what
happened to them."

**Why this is the question most often unanswered.** A rollback that restores the service
and leaves the outputs of a bad release sitting in your downstream systems is not
finished. Those items are in your client's data.

**Score.** 5 if they can show the list of affected items and a record of what was done
with them. 2 if they can describe how they would find them but did not. 0 if they
cannot identify which items a given release processed.

### C4. Did everything go back, not just the code. 3 points

One point each, shown from the running system after the rollback, not from a plan.

| # | Did it go back |
|---|---|
| 1 | The model version |
| 2 | The prompt or configuration version |
| 3 | The confidence thresholds |

**Why all three.** A rollback that restores the code and leaves a threshold where the
bad release put it has restored the wrong system, and every figure after it is measured
under a configuration nobody chose.

---

## Section D — is the monthly report evidence, 20 points

You have three of them in front of you. This is the part of the afternoon you can do
without the supplier in the room.

### D1. Is everything in it. 12 points

Ten things belong in a monthly report. Count how many are present, cover the whole
month, and carry their sample size or their basis where they are a figure.

| # | Element | Present, whole month, supported |
|---|---|---|
| 1 | Volumes: received, processed, straight through, sent to review, rejected | |
| 2 | Automation rate | |
| 3 | Exception rate, against its ceiling | |
| 4 | Accuracy against its floor, with the sample size and how the sample was taken | |
| 5 | Every incident, with severity, times, cause and preventive action | |
| 6 | Every change deployed, with its window, its purpose and its result | |
| 7 | Drift observations, the checks run, and any retraining done or recommended | |
| 8 | Next month's actions, what they need from you, and the risks they see | |
| 9 | Uptime and the service level table, each line marked met or not met | |
| 10 | Service credits, if any | |

**Score.** Count the elements that pass, divide by ten, multiply by twelve, round to a
whole number. Do it for each of the three months and take the average.

**The test that decides most of this score:** a figure with no sample size and no basis
fails, even though it is on the page. An accuracy of 96 percent with no sample size is
not a measurement. So is a volume with no period and an uptime with no exclusion list.
Apply the test to every figure, not only the accuracy line.

**An element that did not apply** passes if the report says "none" and fails if it is
simply missing. A month with no incidents and no incident section is a report you
cannot tell apart from a month whose incidents were left out.

### D2. Are the changes to the system in it, with dates. 4 points

One point each.

| # | Is it stated, with its date |
|---|---|
| 1 | Every change to a confidence threshold |
| 2 | Every change to the model version, including a change the provider made behind the same name |
| 3 | Every change to a prompt or configuration version |
| 4 | Where any of those happened, the affected figure restated at both the old and the new setting, or a plain statement that it has not been |

**Why this one matters more than it looks.** An exception rate that improved and a
threshold that moved in the same month are one sentence apart from an honest report and
a misleading one. No figure in it is wrong. The report is still unusable.

### D3. Did it arrive on time. 4 points

Fifth working day of the following month, for each of the three.

| Condition | Points |
|---|---|
| All three on or before the fifth working day | 4 |
| All three on or before the tenth | 2 |
| Any later than the tenth, or missing | 0 |

Score this separately from completeness. A complete report that arrives late and a thin
report that arrives on time are different problems and averaging them hides both.

---

## Section E — can any of it be checked, 10 points

### E1. Did the timestamps come from systems. 5 points

One point for each of these five that you saw as a system record: a log line, a ticket
field, a mail header, a monitoring result, a deployment record. A screenshot counts. A
person's recollection does not, however confident and however senior.

| # | Timestamp |
|---|---|
| 1 | When the change in the work started |
| 2 | When they detected it |
| 3 | When they told you |
| 4 | When the service was confirmed restored after the incident |
| 5 | When the restored version passed its checks after the rollback |

### E2. Can they reproduce one number. 5 points

Pick one figure from the most recent monthly report before you say which. Then ask them
to show you how it was worked out.

| # | Element | Points |
|---|---|---|
| 1 | The report says which sample or population, which configuration and which period the figure came from | 2 |
| 2 | They produced the underlying records the same afternoon | 2 |
| 3 | Recomputing it gives the same answer, to the rounding the report states | 1 |

**If the answer to any of the three is no**, that is worth more to you than the figure
was. A number that cannot be reproduced is not evidence, and every decision you have
made on it was made on something else.

---

## The afternoon, in order

| Time | What |
|---|---|
| First 30 minutes | Alone with the three monthly reports. Score section D. It needs nobody from the supplier |
| Next 45 minutes | Section A and section B with the supplier in the room. Ask for the record on every date they say aloud |
| Next 30 minutes | Section C. If they have never rolled back, this is short, and the shortness is the finding |
| Next 15 minutes | Section E. Pick the figure last, so it cannot be prepared |
| Last 30 minutes | Total the score. Write the two lists: measures with no target in the contract, and answers given from memory with no record behind them |

---

## What you write down at the end

1. The score, in the form at the top of this file, with the achievable total beside it.
2. The five section subtotals. A total of 70 made of a strong report and no rollback is
   a different supplier from a total of 70 made the other way round.
3. **The list of measures with no target in the contract.** This is the output that
   changes something. Every line on it is a thing you cannot enforce today and can
   write into the next statement of work in an afternoon of your own.
4. The list of answers that came from memory. Not an accusation. A list of things to
   ask for in writing next month, and a way to see whether the answer changes.
5. What was not applicable, and therefore removed from the achievable total.

Clause language for every target this assessment looks for is in
`10-benchmarks/charter/contract-clauses.md`, clauses 17 to 20.

---

## Two things this assessment cannot tell you

**Whether the model is any good.** Nothing in this afternoon measures accuracy,
extraction quality or containment. A supplier can score 90 here on a system that is
wrong a third of the time. Run it beside a test on your own material, not instead of
one.

**What would happen under a real failure.** This measures what a supplier can show you
about the past. The full exercise in `rubric.md` measures what they do under a test,
and the two answers differ often enough that the charter keeps them in separate tables.
