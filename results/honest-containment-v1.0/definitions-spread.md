# Containment, five definitions, and the spread between them

Dataset version 1.0.0 · built 2026-09-02

Four of these five definitions are in common use across the contact-centre and voice-agent industry. They are conventions rather than any one company's property, and none of them is attributed here to a named vendor. The fifth is ours, charter section 3.9.1.

## The five, stated precisely

### Definition A — no transfer to a human

Key in the record: `A_no_transfer`.

A contact is contained when it was not transferred to a human during the contact. Nothing else is tested: not whether the caller's intent was met, not whether the caller came back, not whether the caller asked for a person and was refused.

Counts as a success what ours does not: a hang-up, an unresolved contact, and a refused request for a person.

### Definition B — no transfer and no human handling

Key in the record: `B_no_human_handled`.

A contact is contained when no human joined it at any point, which extends definition A to callbacks, warm transfers completed after the contact and work a person did on the contact afterwards.

Counts as a success what ours does not: an unresolved contact that the caller repeats the next day.

### Definition C — session ended in a self-service end state

Key in the record: `C_self_service_completion`.

A contact is contained when the agent reached an end state its own configuration treats as a completion. The end state is the agent's own disposition code, so the system under test is also the system that decides whether it succeeded.

Counts as a success what ours does not: an end state the agent declared without the ground truth supporting it.

### Definition D — no repeat contact inside the vendor's chosen window

Key in the record: `D_no_repeat`.

A contact is contained when no further contact arrives from the same caller inside a window the vendor chooses, commonly 24 or 72 hours. Resolution is not tested at all: the absence of a second contact stands in for it. Both windows are scored here and both are printed, because the window is the whole metric.

Counts as a success what ours does not: a repeat on day four, and an unresolved contact the caller gave up on.

### Ours — resolved, no human requested or joined, no repeat within seven days

Key in the record: `ours_3_9_1`.

A contact is contained when all three hold: the stated intent was resolved against the scenario's ground truth; the caller did not ask for a person and no person joined, took a callback or did work on the contact afterwards; and no further contact came from the same caller about the same intent within seven calendar days.

### Phrasings in common use, and which definition each one is

A supplier rarely names a definition. It uses one of these phrasings. The third column says what the phrasing tests.

| Phrasing | Definition | Note |
|---|---|---|
| no transfer to a human | `A_no_transfer` | the definition exactly |
| the session ended without the agent asking for a person | `A_no_transfer` | the same test, observed from the agent's side rather than the telephony record |
| no human touched the contact | `B_no_human_handled` | the definition exactly |
| resolved per the disposition code the agent wrote | `C_self_service_completion` | the definition exactly |
| no repeat contact within 24 hours, or within 72 hours | `D_no_repeat` | the definition exactly; the window is the whole metric and is always printed |
| no transfer and no repeat contact | `A_and_D_no_repeat_72h` | the conjunction of A and D, scored here as its own column so that the compound phrasing is not read as either half |

Two properties of the set worth stating before any figure exists. Definition D does not test resolution at all, so a contact correctly transferred to a person counts as contained under D. Definitions A, B and C do not test repeat contact, so a contact the caller has to raise again the next day counts as contained under all three.

## Spread per system

The spread is the distance in percentage points between the highest of the four common definitions and ours, over the same contacts. It is not an error rate. It is the amount by which the answer changes when only the definition changes.

| system | containment, charter 3.9.1 | A no transfer | B no human handled | C self-service end state | D no repeat, 24 h | D no repeat, 72 h | A and D, no transfer and no repeat | spread, points |
|---|---|---|---|---|---|---|---|---|
| developer voice platform A | not run | not run | not run | not run | not run | not run | not run | not run |
| developer voice platform B | not run | not run | not run | not run | not run | not run | not run | not run |
| general model with the reference agent prompt | not run | not run | not run | not run | not run | not run | not run | not run |
| our agent | not run | not run | not run | not run | not run | not run | not run | not run |

## False containment against each reference

Charter 3.10. Always against a named reference, with the breakdown by which of the three conditions failed, because the three cost a BPO different amounts.

| system | reference | false containment | not resolved | person requested, not provided | repeat within seven days |
|---|---|---|---|---|---|
| developer voice platform A | A_no_transfer | not run | not run | not run | not run |
| developer voice platform A | B_no_human_handled | not run | not run | not run | not run |
| developer voice platform A | C_self_service_completion | not run | not run | not run | not run |
| developer voice platform A | D_no_repeat_72h | not run | not run | not run | not run |
| developer voice platform B | A_no_transfer | not run | not run | not run | not run |
| developer voice platform B | B_no_human_handled | not run | not run | not run | not run |
| developer voice platform B | C_self_service_completion | not run | not run | not run | not run |
| developer voice platform B | D_no_repeat_72h | not run | not run | not run | not run |
| general model with the reference agent prompt | A_no_transfer | not run | not run | not run | not run |
| general model with the reference agent prompt | B_no_human_handled | not run | not run | not run | not run |
| general model with the reference agent prompt | C_self_service_completion | not run | not run | not run | not run |
| general model with the reference agent prompt | D_no_repeat_72h | not run | not run | not run | not run |
| our agent | A_no_transfer | not run | not run | not run | not run |
| our agent | B_no_human_handled | not run | not run | not run | not run |
| our agent | C_self_service_completion | not run | not run | not run | not run |
| our agent | D_no_repeat_72h | not run | not run | not run | not run |

## What the dataset alone already says

The table below is not a result and no system produced it. It is arithmetic over the ground truth: the highest containment each definition could reach on these 300 contacts if an agent followed every policy in every pack, escalated exactly when the ground truth requires it, and asserted nothing the pack does not support. It is computed by `suite/ceilings.py` and it exists because the definitions already disagree before any agent speaks.

| Definition | Contacts contained | Of | Share |
|---|---|---|---|
| containment, charter 3.9.1 | 116 | 300 | 38.7 percent |
| A no transfer | 128 | 300 | 42.7 percent |
| B no human handled | 128 | 300 | 42.7 percent |
| C self-service end state | 128 | 300 | 42.7 percent |
| D no repeat, 24 h | 288 | 300 | 96.0 percent |
| D no repeat, 72 h | 258 | 300 | 86.0 percent |
| A and D, no transfer and no repeat | 122 | 300 | 40.7 percent |

Read the row for definition D at 24 hours against the row for ours. On this dataset a policy-perfect agent is contained on 96.0 percent of contacts under definition D at 24 hours and on 38.7 percent under ours. The agent is the same agent. The contacts are the same contacts. Only the definition moved.

The reason is in the construction: 172 of the 300 contacts require a person under the policy packs, and a correct transfer is not containment under our definition or under A, B or C, while it is containment under D. See `why-90-percent-is-65.md` for the same point worked through from the definitions alone.
