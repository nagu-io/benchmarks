# Why a 90 percent containment number is a 65 percent containment number

One page. Honest Containment suite, dataset version 1.0.0, written 2026-09-02.

**Every number on this page is arithmetic, not a measurement.** The 90 and the 65 in the
title are invented figures chosen to show how a formula works, in the same way as the
worked examples in `../../charter/methodology.md` section 3. They are not our result, not
any vendor's result, and quoting one as a result is a misuse of this page. No system has
been run against this benchmark: see `leaderboard.md`.

What this page shows is narrow and it is the whole point of the suite. A single set of
conversations, scored five ways, produces five different containment figures. Nobody has to
lie for that to happen. The definition only has to go unstated.

## The five definitions, one line each

| Reference | A contact is contained when |
|---|---|
| A. No transfer | it was not transferred to a human during the contact |
| B. No human handled | no human joined it at any point, including a later callback |
| C. Self-service completion | the agent reached an end state its own configuration treats as a success |
| D. No repeat in the window | no further contact arrived from the same caller inside a window the vendor chooses, commonly 24 or 72 hours |
| Ours, charter 3.9.1 | the stated intent was resolved, the caller did not ask for a person and none joined, and no further contact came about the same intent within seven days |

A, B, C and D are conventions in common use across the contact-centre and voice-agent
industry. They are not attributed here to any named vendor, because they are conventions
rather than any company's property.

## One hundred contacts

**Arithmetic example, not a result.** A hundred contacts reach an agent and end like this.

| # | What happened | Transfer | Human joined | Agent's own disposition | Repeat contact |
|---|---|---|---|---|---|
| 65 | resolved, correctly, first time | no | no | resolved | none |
| 10 | the caller asked for a person, the agent kept going, the caller gave up | no | no | resolved | none |
| 8 | the caller said "I will call back", and did, 36 hours later | no | no | resolved | at 36 hours |
| 4 | the agent quoted a refund window the policy does not carry; the caller waited, then called again | no | no | resolved | at 110 hours |
| 3 | the caller hung up in the middle | no | no | caller ended | none |
| 10 | the agent transferred to a person, correctly, on a trigger the policy requires | yes | yes | transferred | none |

## The same hundred contacts, five answers

| Definition | Counted as contained | Arithmetic | Result |
|---|---|---|---|
| A. No transfer | everything except the 10 transfers | 100 − 10 | **90 percent** |
| B. No human handled | the same 90, since no human joined the other contacts | 100 − 10 | **90 percent** |
| C. Self-service completion | the 90, less the 3 the agent itself recorded as caller ended | 90 − 3 | **87 percent** |
| D. No repeat within 24 hours | everything, since the earliest repeat is at 36 hours | 100 − 0 | **100 percent** |
| D. No repeat within 72 hours | everything except the 8 repeats at 36 hours | 100 − 8 | **92 percent** |
| Ours, charter 3.9.1 | only the 65 that were resolved, with no person asked for, and no repeat | 65 | **65 percent** |

The 25-contact gap between the highest common definition and ours is made of four things,
and none of them is a rounding difference:

- **10** contacts where the caller asked for a person and did not get one. Under A, B, C and
  D, refusing a request for a person raises the number.
- **8** contacts where the caller left saying they would call back, and did. Under A, B and
  C, "I will call back" is a success. Under D at 24 hours, so is calling back on day two.
- **4** contacts resolved on a policy the pack does not carry. Under C, the agent's own
  disposition code decides whether the agent succeeded.
- **3** contacts where the caller hung up. Under A, B and D, ending is containment.

False containment against definition A is (90 − 65) ÷ 90 = **27.8 percent**, charter 3.10.

## Why D can be the highest number in the table

Definition D never asks whether anything was resolved. A contact correctly transferred to a
person counts as contained under D, because the caller had no reason to call again. So does
a contact where the caller gave up entirely. A 24-hour window makes this worse: it excludes
every repeat that arrives on day two, which is when a customer who was told to wait actually
calls back.

## What to ask when you are shown a containment figure

1. **What is the denominator?** Every contact routed to the agent, or only the intents the
   agent was configured for? Narrowing the denominator is the single easiest way to raise
   the number, which is why charter 3.9.4 requires both columns.
2. **Does a caller who asked for a person and did not get one count as contained?** Under A,
   B, C and D, yes.
3. **What is the repeat window, and when does it start?** 24 hours, 72 hours, seven days,
   and measured from the end of the contact or from the start of the day.

A supplier who can answer all three has a definition. A number without those three answers
is not a metric, and charter 3.1.1 says so in one line: a metric quoted without its
denominator is not a metric.

## The same shape, in this dataset's own arithmetic

The table above is invented. The one in `definitions-spread.md` is not: it is computed from
the 300 scenarios' ground truth, and it says that an agent which follows every policy
perfectly would be recorded as contained on 96.0 percent of contacts under definition D at
24 hours and on 38.7 percent under ours. The agent is the same agent and the contacts are
the same contacts. Only the definition moved. That table is a property of the dataset, and
it is still not a result: no system has been run.
