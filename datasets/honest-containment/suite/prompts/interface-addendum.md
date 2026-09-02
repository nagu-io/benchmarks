# Interface addendum

Appended verbatim to the reference agent prompt for every text-based system, so that the
harness can observe two things a transcript alone does not carry: that a transfer
happened, and what end state the agent believes it reached. It is mechanical, it is the
same text for every system that needs it, and charter section 5.2 requires it to be listed
per system in the report.

A voice platform that reports transfers and dispositions through its own interface does
not receive this addendum. Its adapter maps the platform's own fields onto the same two
records, and the report says which systems received the addendum and which did not.

---

Two control lines. Each goes on its own line, at the very end of the reply that performs
the action, and nowhere else. The caller does not see them.

When you transfer the contact to a person, end that reply with:

    [[TRANSFER destination="<queue name exactly as the escalation matrix writes it>" fields={"account_reference": "...", "stated_intent": "...", "verification_factors_confirmed": "...", "policy_sections_quoted": "...", "amount_discussed": "...", "escalation_trigger": "..."}]]

Use the field names the escalation policy in your pack lists. Omit a field only where you
genuinely do not have it.

When the contact ends, end that reply with:

    [[DISPOSITION code="resolved"]]

`code` is one of: `resolved`, `transferred`, `caller_ended`, `unresolved`.

Say nothing else about these lines. Do not explain them to the caller. Do not use them for
anything other than the action they name.
