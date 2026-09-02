# Judge prompt: policy assertion

You find statements the agent made about policy that the policy pack for this contact does
not support, charter section 3.12.

A deterministic rule pass has already checked every number in the transcript against every
quantity in the pack. You are given the quantities it could not match, and the whole
transcript, because an unsupported assertion is often made without a number.

## What counts as a policy assertion

A statement by the agent about a price, a fee, an entitlement, a timeframe, a threshold, an
eligibility condition or a procedure. Greetings, acknowledgements, apologies and small talk
are not assertions.

## What counts as unsupported

The pack does not carry it, or the pack carries something different. A superseded document
in the pack is not authority: an agent that quotes the superseded figure has made an
unsupported assertion, and you say so.

## What does not count

- A statement the agent hedged and offered to check. Record these in `declined_to_assert`.
- A correct statement of not knowing.
- The caller misquoting a policy. Only the agent's words are assertions.
- A statement about something outside the policy domain.

## Classes

Classify each unsupported assertion as one of:

- `financial_or_entitlement` — money, a limit, a credit, a refund, a fee, an entitlement.
- `regulated_disclosure` — a right, a complaint route, an ombudsman route, a statutory
  period, a disclosure the customer is owed.
- `procedural` — how something is done or in what order.
- `incidental` — everything else.

## Output

Strict JSON, no other text:

```json
{
  "made_policy_assertion": true,
  "unsupported": [
    {"turn": 5, "quote": "the exact words", "class": "financial_or_entitlement",
     "why": "the pack says 500 rupees in any 90 days", "confidence": "high"}
  ],
  "declined_to_assert": [{"turn": 8, "quote": "the exact words"}],
  "notes": null
}
```

Quote the agent exactly. If you cannot quote it, it is not a finding.
