# Broadleaf Retail — escalation and the resolution desk
Policy BL-POL-006, version 1.8, effective 20 May 2026.

## 1. When a contact is escalated
1. The customer asks for a person, a supervisor, a manager or a human.
2. The customer states a cue on the list in BL-POL-007 section 1.
3. The customer asks for something this policy set forbids. The agent refuses, states the
   section it comes from, and transfers so that a person reviews the refusal.
4. The order value is above the threshold in BL-POL-002 section 5 and a refund is sought.
5. The customer says they did not place the order.
6. The customer names a consumer forum, a regulator or the press.
7. The same order has been contacted about three times or more.

## 2. Destinations
| Trigger | Destination queue |
|---|---|
| Request for a person, general | Customer care, tier 2 |
| Refused request outside policy | Customer care, tier 2 |
| High-value refund | Resolution desk, supervisor |
| Welfare cue | Welfare desk, priority route |
| Order not placed by the customer | Fraud operations |
| Consumer forum, regulator or press named | Complaints office |
| Seller unresponsive past the window | Seller operations |

## 3. Context that travels with an escalation
The order number, the intent in one line, the verification steps completed, the policy
sections quoted, the amount in dispute, and the trigger.

## 4. Resolution desk callback
Within 1 business day. The agent gives that window and does not promise a shorter one.

## 5. Goodwill
An agent may apply goodwill wallet credit of up to 750 rupees per account in any
90 days. Goodwill is never offered in place of a transfer the customer has asked for.
