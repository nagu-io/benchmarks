# Day-60 scripted exercises v1.0.0

The four exercises the rubric scores, written so that two people running them a month
apart run the same thing.

Rubric version 1.0.0 · Charter version 1.0.0 · Written 2026-09-02.

Read `rubric.md` first. This file says what to do; that file says how it is scored.

---

## 1. Roles

| Role | Held by | What they do |
|---|---|---|
| Exercise owner | The partner, or a third party the partner names. Never the delivery team | Holds the script, the injection timestamps and the stop condition. Starts and stops every exercise |
| Assessors | Two people, named before the exercise. May include the exercise owner | Score every line independently from the evidence pack |
| Delivery team | The supplier being measured | Responds. Sees the exercise definitions in this file, and does not see the injection timestamps or the exercise window at tier T2 and above |
| Rollback owner | Named by the supplier, on call for the whole exercise | Can return the system to its previous state at any moment, whether or not the exercise is finished |
| Stop authority | The exercise owner and the rollback owner, either acting alone | Ends any exercise immediately, with no discussion required |

**What the delivery team is told in advance, by tier.**

| Tier | Told in advance |
|---|---|
| T1 | Everything: the exercise, the class injected, the window and the timestamps |
| T2 | The exercise period, and that one drift class will be injected in it. Not the class, not the timestamp |
| T3 | The exercise period only |
| T4 | The exercise period only. The Severity 1 element is a tabletop and is scheduled openly |
| T5 | Nothing beyond the standing agreement that exercises occur inside the period the statement of work allows |

At every tier the delivery team knows an exercise programme exists and has agreed to it
in writing. Charter 4.5.1 admits no exception to that, at any tier, for any reason.

---

## 2. Safety rules, which hold at every tier without exception

From charter 4.5.1. An exercise that cannot meet all of these is not run, and the
rubric lines it would have scored are marked "not exercised" and removed from the
achievable total. They are never assumed and never given the benefit of the doubt.

2.1 **No exercise ever injects a real data exposure, a real exfiltration, or a
simulated breach involving live personal data.** Not as a tabletop prop, not as a test
record, not with data that has been "mostly" anonymised. Where an exercise needs an
input, the input is synthetic and is labelled synthetic in the item record itself, so
that anyone finding it later in a queue can see what it is.

2.2 **Every injection is agreed in writing in advance**, naming the systems in scope,
the period, the maximum volume affected, and the people who may be contacted.

2.3 **Every exercise has a named owner who can stop it**, and a stop condition written
before it starts. The stop condition is a specific observable, not a judgement: for
example "more than N items reach the downstream system" or "any real partner client
contacts the service desk about this".

2.4 **Every exercise has a rollback owner on call for its duration**, who can return
the system to its previous state without waiting for the exercise to finish.

2.5 **No exercise runs during a period the statement of work protects**, such as a
period-end close, a regulatory filing window, or a hypercare period.

2.6 **The exercise stops the moment a real incident begins.** A real incident takes the
whole team, and an exercise running alongside it makes the real one worse and the
exercise worthless. The affected lines are marked "not exercised".

2.7 **Every injected item is reversible and traceable.** Before an injection begins,
the exercise owner records how every injected item will be identified afterwards. An
injection that cannot be found again cannot be cleaned up.

---

## 3. Exercise D-1 — drift injection

**Scores** rubric lines A1, A2, A3, A4, and contributes timestamps 1, 2 and 3 to E1.
**Charter** 3.18.

### 3.1 What it tests

Whether the monitoring sees a change in the input, and whether anyone acts on what the
monitoring saw. Those are two questions and the rubric runs two clocks for them.

### 3.2 The injection classes

Pick by tier. Each class is a share of input items that belong to a population the
system has not been built for.

| Class | What it is | Suits |
|---|---|---|
| D-1a New format | A share of items arrive in a layout, template or schema absent from the acceptance set. For a document process, a vendor moving to a consolidated statement. For a case process, a new source document | T1, T2 |
| D-1b New category | A share of items belong to a category with labelled examples in neither the acceptance set nor the training data | T2, T3 |
| D-1c Confidence shift | The distribution of the system's reported confidence moves without accuracy moving, for example by shifting the mix towards items the model finds easy | T3, as the second concurrent signal |
| D-1d Unlabelled class | A class with no labelled examples anywhere, so the correct output is not derivable from anything the system has seen | T4, T5 |
| D-1e Language or script shift | A share of items arrive in a language or script present in the acceptance set at a much lower share | Any tier, as an alternative to D-1a |

At tier T3 and above, two classes run concurrently, and the exercise report says
whether the supplier detected one, both or neither. Detecting one of two is not
detecting the drift.

### 3.3 The script

| Step | Who | What happens | Recorded |
|---|---|---|---|
| 1 | Exercise owner | Chooses the class, the share and the ramp. Writes the stop condition | The injection plan, sealed until step 8 |
| 2 | Exercise owner | Confirms the safety conditions in section 2 are met, in writing | The written confirmation |
| 3 | Exercise owner | Begins the injection. The first injected item's intake timestamp is **the onset** | Onset timestamp, held back from the delivery team |
| 4 | Exercise owner | Holds the share at the planned level for the exercise window | The per-day injected counts |
| 5 | Delivery team | Operates normally | Whatever it normally records |
| 6 | Exercise owner | Watches for the internal alert or ticket, without prompting | Alert timestamp, from the system |
| 7 | Exercise owner | Watches for the written notice to the partner | Notice timestamp and the notice itself |
| 8 | Exercise owner | Closes the window, stops the injection, unseals the plan | Window close timestamp |
| 9 | Exercise owner | Confirms every injected item has been identified and cleaned up | The reconciliation of injected against found |

### 3.4 Parameters to set before the exercise

None of these has a default in this file, because a default would become a number
nobody chose. The exercise owner sets each one in the injection plan and records it.

| Parameter | Note |
|---|---|
| Share of input affected | Large enough that the monitoring could see it, small enough to satisfy the stop condition |
| Ramp | Step or gradual. A gradual ramp is a harder test, and the exercise report says which was used |
| Exercise window length | Fixes the meaning of "not detected within the window". Printed with every A1 and A2 result |
| Stop condition | A specific observable, per 2.3 |
| Second class, at T3 and above | Chosen so the two signals are independent |

### 3.5 Evidence pack for D-1

1. The injection plan, unsealed, with the onset timestamp.
2. The per-day counts of injected items.
3. The alert or ticket record, with its system timestamp, or a statement that none was
   raised.
4. The written notice, with its delivery timestamp, or a statement that none was sent.
5. The alert log for the whole exercise period, and the record of withdrawn alerts.
6. The reconciliation showing every injected item found and cleaned up.

### 3.6 What invalidates the exercise

- The delivery team learned of the injection from a source other than its own
  monitoring. Record the source and mark A1 and A2 "not exercised".
- The injection could not be held for the full window because the stop condition fired.
  The lines are scorable only if the alert or the notice happened before the stop; the
  report states that the window was cut short and by how much.
- The injected items cannot be reconciled. The exercise is a cleanup problem, not a
  measurement, and A1 to A4 are marked "not exercised".

---

## 4. Exercise I-1 — incident

**Scores** rubric lines B1, B2, B3, B4, and contributes timestamp 4 to E1.
**Charter** 3.19.

### 4.1 What it tests

How long a restoration takes, and whether the partner learned what was happening from
the supplier or from its own users.

### 4.2 The incident scripts

| Script | Severity | What is done | Suits |
|---|---|---|---|
| I-1a Silent empty output | Severity 2 | For a bounded share of items, the system returns structurally valid output with the payload fields empty. The items pass validation and post empty. Chosen because it is the failure a naive health check misses | T2 |
| I-1b Process stopped | Severity 2 | One covered system stops processing at intake. Items queue and none completes | T2 |
| I-1c Stale reference data | Severity 2, requiring a partner dependency | An upstream reference source returns stale data, so matching or validation silently fails against the wrong values. Resolution needs the partner to refresh the source | T3 |
| I-1d Degraded turnaround | Severity 3 | Processing slows past the turnaround the statement of work states, with a workaround available | T1 |
| I-1e Partner-wide outage | Severity 1, tabletop only | Walked through in a room. Nothing is done to any system. Timings are the participants' stated intentions and are recorded as intentions, never as measured times | T4, T5 |

### 4.3 The script

| Step | Who | What happens | Recorded |
|---|---|---|---|
| 1 | Exercise owner | Confirms the safety conditions and the stop condition | The written confirmation |
| 2 | Exercise owner | Triggers the fault at a time the delivery team does not know at T2 and above | Fault injection timestamp |
| 3 | Either party | The clock starts at the earlier of the supplier's detection and the partner's notice | Both timestamps, from systems |
| 4 | Delivery team | Acknowledges, communicates, investigates, restores | Ticket and message timestamps |
| 5 | Delivery team | Confirms restoration with a monitoring check | The check, its timestamp and its result |
| 6 | Exercise owner | Notes any period the supplier was waiting on a partner dependency | Start and end of each waiting period |
| 7 | Exercise owner | Stops the clock at the confirming check, not at ticket closure | Restoration timestamp |
| 8 | Delivery team | Produces the post-incident record within five business days | The record and its creation timestamp |

### 4.4 The rule about the tabletop

I-1e is a tabletop. Its output is a set of stated intentions. Charter 3.1.8 forbids an
unrun figure being written as a result, so a tabletop never produces a time on B1 or
B2. Those lines are marked "not exercised" and removed from the achievable total, and
B3 and B4 are scored on what the tabletop actually produced: the communication plan
and the written record.

### 4.5 Evidence pack for I-1

1. The fault injection record with its timestamp.
2. The supplier's detection record, or a statement that the partner reported it first.
3. Ticket timestamps for acknowledgement and every state change.
4. Every message sent to the partner during the incident, with timestamps.
5. The monitoring check that confirmed restoration, with its result.
6. The record of any waiting-on-partner periods, with both ends.
7. The post-incident record with its creation timestamp.

### 4.6 What invalidates the exercise

- A real incident began during the exercise. Stop, per 2.6. Mark the lines "not
  exercised".
- The fault did not take effect, or took effect on a different population than
  planned. Record what actually happened; the lines are scorable only against the
  fault that occurred.
- The delivery team was told the fault was an exercise before restoring it. Record who
  told them and when, and mark B1 and B2 "not exercised". B3 and B4 remain scorable.

---

## 5. Exercise R-1 — rollback

**Scores** rubric lines C1, C2, C3, C4, and contributes timestamp 5 to E1.
**Charter** 3.20.

### 5.1 What it tests

Whether a rollback is a rehearsed procedure or an argument, and whether it finishes.

### 5.2 The trigger

The exercise needs a rollback criterion to be met. Two ways to arrange that, and the
report says which was used.

| Method | How | Suits |
|---|---|---|
| R-1a Deploy and revert | The supplier deploys a change that meets a rollback criterion in `06-delivery/build-standards.md` section 9, inside an agreed change window, on synthetic traffic | T2, T3 |
| R-1b Declare the criterion met | The exercise owner declares a stated criterion met at a stated time, and the supplier rolls back as though it were | T1, and any tier where a deploy is not permitted |

R-1b measures the procedure and not the detection, and the report says so on the line.

### 5.3 The script

| Step | Who | What happens | Recorded |
|---|---|---|---|
| 1 | Exercise owner | Confirms the safety conditions and names the rollback owner | The written confirmation |
| 2 | Either | The rollback criterion is met, or is declared met | Criterion timestamp |
| 3 | Delivery team | The on-call engineer records the rollback decision | Decision timestamp |
| 4 | Delivery team | Rolls back to the previous signed release | Deployment record |
| 5 | Delivery team | Runs the smoke set on the restored release | Smoke-set result and timestamp |
| 6 | Delivery team | Shows the model pin, the prompt version and the threshold set in force after the rollback | Three values, read from the running system |
| 7 | Delivery team | Identifies every item the rolled-back release processed and re-queues them | The item list and the re-queue completion timestamp |
| 8 | Exercise owner | At T4 and above, confirms the data restore from backup separately | The restore record and its own timing, reported separately |

### 5.4 Evidence pack for R-1

1. The criterion record with its timestamp, or the declaration.
2. The decision record with its timestamp and the engineer's name.
3. The deployment record for the restored release.
4. The smoke-set result with its timestamp.
5. The three configuration values read from the running system after the rollback.
6. The list of affected items and the re-queue completion record.
7. At T4 and above, the data restore record, timed and reported separately under
   `02-security/security-policy-set/07-backup-and-recovery.md`.

### 5.5 What invalidates the exercise

- A rehearsal on a non-production copy is scored only at T1, and the line is marked
  "rehearsal". At any other tier it is marked "not exercised" rather than scored,
  because charter 3.20.4 forbids a rehearsal figure sitting in the same table as a
  production rollback.
- The supplier cannot identify the items the rolled-back release processed. C3 is
  scored 0, recorded as "affected items not identifiable", and the finding goes in the
  exercise report whatever the rest of the section scores.

---

## 6. Exercise A-1 — monthly report audit

**Scores** rubric lines D1, D2, D3, and E2. **Charter** 3.21.

### 6.1 What it tests

Whether the monthly report is evidence or decoration.

### 6.2 The script

| Step | Who | What happens | Recorded |
|---|---|---|---|
| 1 | Exercise owner | Fixes the denominator: the ten elements of the ops retainer schedule clause 5.2, plus any the statement of work adds | The element list, with the count |
| 2 | Exercise owner | Picks one figure from the report to reproduce, before telling the supplier | The figure, sealed |
| 3 | Assessors | Score each element present, present but unsupported, absent, or not applicable and explicitly stated | The per-element result |
| 4 | Exercise owner | Records the delivery timestamp from the mail or portal system | The timestamp |
| 5 | Exercise owner | Unseals the figure and asks the supplier to reproduce it | The request and its timestamp |
| 6 | Delivery team | Produces the underlying records and the recomputation | The records and the recomputed figure |
| 7 | Assessors | Compare the recomputed figure with the reported one at the rounding the report states | Both figures |

At tier T3 and above the audit covers three months. Each month is scored separately on
D1 and the points are the mean of the three, rounded to a whole point, with all three
ratios recorded.

### 6.3 The test that decides most of D1

An element that carries a figure without its sample size or its basis fails, even
though it is present. Apply that test to every figure in the report, not only to the
accuracy line. A volume with no period, an uptime with no exclusion list and an
automation rate with no denominator all fail the same way.

### 6.4 Evidence pack for A-1

1. The report or reports audited, as delivered.
2. The element list with the denominator count.
3. The per-element scoring sheet from both assessors.
4. The delivery timestamps.
5. The reproduction request, the records supplied and the recomputed figure.

### 6.5 What invalidates the exercise

- The report was amended after the audit began. Score the version as delivered, and
  record that an amendment was offered and when.
- The supplier supplied the underlying records after the exercise window closed. E2
  element 2 scores 0, and the report states the delay rather than treating late as
  absent.

---

## 7. Assembling the exercise report

7.1 One evidence pack per exercise, assembled by the exercise owner, given to both
assessors at the same time.

7.2 Both assessors complete `scoresheet.csv` independently and exchange only after both
are finished. Disagreements resolve under `rubric.md` section 3.7.

7.3 The exercise report contains, in this order: the score line from `rubric.md`
section 9.1; the section subtotals; the list of lines scored 0 for "no target in the
contract"; the list of lines not exercised with the reason; every ratio line's observed
value, target and ratio; and the evidence reference for every line.

7.4 A line without an evidence reference is scored 0, whatever the assessors believe
happened.

7.5 The report says which tier was run, on its face, everywhere the score appears. An
announced drift injection is an easier test than an unannounced one, and charter 9.9
requires the tier to say which was run.

---

## 8. Status

8.1 No exercise in this file has been run. No score exists. `scoresheet.csv` carries
the structure and the formulas and no scores, and stays that way until an exercise
happens.

8.2 What a person must supply before the first exercise: a partner and a deployment
willing to be exercised; the written agreement in 2.2; a named exercise owner, a named
rollback owner and two named assessors; a statement of work whose targets the ratio
lines can be scored against; and an exercise period that does not fall inside a
protected window.
