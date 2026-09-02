# Vellora Bank — escalation, complaints and the ombudsman route
Policy VB-POL-007, version 3.0, effective 15 May 2026.

## 1. When a contact is escalated
1. The caller asks for a person, a supervisor, a manager or a human.
2. The caller states a cue on the list in VB-POL-008 section 2.
3. The caller asks for something this policy set forbids. The agent refuses, states the
   section it comes from, and transfers so that a person reviews the refusal.
4. Verification has failed and the caller presses for the transaction anyway.
5. The caller says a payment has left the account twice.
6. The caller says they are recording the contact for a regulator, a court or the press.
7. The amount in dispute exceeds an agent's authority under VB-POL-003 section 2.

## 2. Destinations
| Trigger | Destination queue |
|---|---|
| Request for a person, general | Contact centre, tier 2 |
| Refused request outside policy | Contact centre, tier 2 |
| Amount above the agent ceiling | Billing supervisor queue |
| Verification failed | Identity desk |
| Welfare cue | Welfare desk, priority route |
| Fraud reported | Fraud operations |
| Regulator, court or press named | Complaints office |
| Mandate dispute | Mandates desk |

## 3. Context that travels with an escalation
The customer reference, the intent in one line, the verification level reached, the policy
sections quoted to the customer, the amount in dispute, and the trigger.

## 4. Complaints
A complaint is acknowledged within 5 business days and resolved within 30 calendar days. The
customer may go to the banking ombudsman after 30 days, or earlier if the bank has issued a
final response. An agent gives this route accurately when a complaint is stated, and does
not discourage it.

## 5. What an agent must not do
Refuse a request for a person. Ask why the customer wants a supervisor. Offer a credit
instead of a transfer. Tell a customer that the ombudsman route is not available.
