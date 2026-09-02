# Orbanet Mobile — escalation matrix and supervisor callback
Policy OB-POL-006, version 1.6, effective 20 February 2026.

## 1. When a contact is escalated
An agent escalates, without argument and without a further attempt to resolve, where any
of the following occurs:

1. the caller asks to speak to a person, a supervisor, a manager or a human;
2. the caller states or implies a risk to their safety or wellbeing, on the cue list in
   OB-POL-008 section 2;
3. the caller asks for something this policy set forbids: the agent refuses, states the
   section it comes from, and transfers the contact so that a person reviews the refusal;
4. the caller cannot be verified under OB-POL-001 and asks for an account change anyway;
5. the account carries a legal, regulatory or media flag;
6. the caller reports that a payment has left their account twice.

## 2. Destinations
| Trigger | Destination queue |
|---|---|
| Request for a person, general | Voice support, tier 2 |
| Refused request outside policy | Voice support, tier 2 |
| Billing amount above the agent ceiling | Billing supervisor queue |
| Identity that cannot be verified | Identity desk |
| Safety or wellbeing cue | Welfare desk, priority route |
| Legal, regulatory or media flag | Complaints office |
| Suspected fraud on the account | Fraud operations |

## 3. Context that travels with an escalation
Every escalation carries: the account reference, the caller's stated intent in one line,
the verification factors confirmed so far, the policy sections already quoted to the
caller, any amount discussed, and the trigger that caused the escalation. An escalation
that arrives without these six fields is returned to the agent's queue.

## 4. Supervisor callback
Where no supervisor is available, a callback is booked within 4 business hours. The agent
gives the window and does not promise a shorter one.

## 5. What an agent must not do
Refuse a request for a person. Ask the caller to explain why they want a person before
transferring. Offer a credit in place of a transfer. End a contact that met a trigger in
section 1 without escalating it.
