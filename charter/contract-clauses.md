# Benchmark contract clauses

Clause language for every metric in `methodology.md` section 3, written to be pasted into `01-legal/sow-template.md` and, where the clause governs the run phase, into `01-legal/ops-retainer-schedule.md`.

Owner: Benchmark owner, Entailment Labs (placeholder name)
Version 1.0.0, issued against charter version 1.0.0
Written 2026-09-02

> **Lawyer review — before first use**
> Every clause here is drafting, not advice, and none of it has been reviewed. Section 5 lists each clause a lawyer must review and why. In summary: the Severity 2 escalations in clauses 2, 4, 7, 10, 11, 16 and 17 change what triggers the Retainer Schedule remedies; the new service-credit rows these clauses assume in Retainer Schedule clause 7.1 must be priced and confirmed not to operate as a penalty under section 74 of the Indian Contract Act 1872, as the Retainer Schedule cover note already flags; clause 22 must be read against MSA clause 11.3, which makes service credits the sole financial remedy for a Service Level failure; and clause 21 must be read against DPA obligations before any evidence pack is passed to the Partner's own client.
> Nothing in this document is signed, sent or relied on until that review is complete.

## 1. How to use this document

1.1 This document holds twenty-three clauses. Clause 1 incorporates the measurement method. Clauses 2 to 20 each bind one metric, in the same order as the index in `methodology.md` section 3.2. Clauses 21 to 23 hold the evidence, remedy and exclusion mechanics that the metric clauses refer to.

1.2 Do not paste all twenty-three into a Statement of Work. Choose the measures that describe "done" for the process in scope, exactly as `06-delivery/acceptance-criteria-library.md` section 2 directs, and paste only those clauses plus clauses 1, 21, 22 and 23. Fewer measures, each with a number, are worth more than many without one.

1.3 Where each clause goes.

| Clause | Metric | Insertion point |
|---|---|---|
| 1 | Definitions and incorporation | New Schedule to the SOW, referenced from SOW clause 6.3 |
| 2 | Field-level accuracy | SOW clause 6.3 table, accuracy floor row; Retainer Schedule clause 3.1 accuracy row |
| 3 | Straight-through-processing rate | SOW clause 6.3 table, new row |
| 4 | Exception rate | SOW clause 6.3 table, exception-rate ceiling row; Retainer Schedule clause 3.1 |
| 5 | Confidence calibration | SOW clause 6.3 table, new row |
| 6 | Cost per document | SOW clause 6.3 table, new row; SOW clause 7 where a per-transaction fee is used |
| 7 | Latency | SOW clause 6.3 table, turnaround row; Retainer Schedule clause 3.1 |
| 8 | Containment | SOW clause 6.3 table, new row, voice and chat SOWs |
| 9 | False containment | Reporting duty; Retainer Schedule clause 5.2, new sub-clause |
| 10 | Escalation accuracy | SOW clause 6.3 table, new row |
| 11 | Hallucinated-policy rate | SOW clause 6.3 table, new row; Retainer Schedule clause 4 severity table |
| 12 | Time to first token | SOW clause 6.3 table, new row |
| 13 | Automation rate | SOW clause 6.3 table, new row, back-office SOWs |
| 14 | Wrong-automation rework | SOW clause 6.3 table, new row |
| 15 | Reviewer minutes per exception | Reporting duty; Retainer Schedule clause 5.2, new sub-clause |
| 16 | Ninety-day drift | Retainer Schedule clause 5.2.7, replacing the drift sub-clause |
| 17 | Drift detection lead time | Retainer Schedule clause 3.1, new Service Level row |
| 18 | Incident mean time to restore | Retainer Schedule clause 3.1, resolution rows |
| 19 | Rollback time | Retainer Schedule clause 3.1, new Service Level row; clause 8 change windows |
| 20 | Report completeness | Retainer Schedule clause 3.1, Monthly Report row |
| 21 | Evidence and audit | New Schedule to the SOW |
| 22 | Remedies and re-measurement | New Schedule to the SOW; read with Retainer Schedule clause 7 |
| 23 | Exclusions and measurement disputes | New Schedule to the SOW; read with Retainer Schedule clause 10 |

1.4 Reference convention, and renumbering on insertion. In this document a capitalised "Clause" means a clause of the clause set in section 2; a lower-case "section" means a section of this document; and a reference such as "SOW clause 6.2" or "Retainer Schedule clause 7.1" means a clause of that other document. These clause numbers are this document's. When a clause is pasted into a Statement of Work it takes the numbering of that document, and the cross-references inside it are updated to match. A cross-reference to a measure clause or to a Schedule list is therefore written as "clause [X]", to be completed on insertion. References to Clause 1 and to Clauses 21 to 23 are written out, because those four clauses travel with every set.

1.5 Placeholders. Every floor, ceiling, window, period and percentage is a placeholder, with one exception: the report completeness floor in Clause 20.3 is fixed at one hundred percent, for the reason that clause gives. A placeholder left in a signed document is a defect, not a default. Section 4 lists every placeholder in one table so that none is missed at signature.

1.6 Precedence. The MSA prevails over the SOW except where the SOW names an MSA clause by number and states that it is overridden, per SOW clause 2.4 and MSA clause 2.4. Nothing in this document overrides the DPA, and nothing in it limits any right the Partner has under DPA clause 8 or MSA clause 14.4.

1.7 Definitions used below. "Measurement Method" means `methodology.md` at the version named in Clause 1.1. "Labelled Set" means the frozen labelled evaluation set named in the SOW, with its version identifier. "Measurement Window" means the period stated in the clause. Terms capitalised and not defined here have the meaning given in the MSA.

## The clause set, in parts

The clause set is published in parts so that a clause can be linked, reviewed and cited on its own. The parts are the document: nothing here is a summary and nothing is left out.

| Part | Contents | Read |
|---|---|---|
| 01 | Section 2, the clause set: Clause 1 definitions and incorporation, Clause 2 field-level accuracy, Clause 3 straight-through-processing rate, Clause 4 exception rate, Clause 5 confidence calibration, Clause 6 cost per document, Clause 7 latency, Clause 8 containment, Clause 9 false containment, Clause 10 escalation accuracy, Clause 11 hallucinated-policy rate | [`01-clauses-1-to-11.md`](contract-clauses/01-clauses-1-to-11.md) |
| 02 | Clause 12 time to first token, Clause 13 automation rate, Clause 14 wrong-automation rework, Clause 15 reviewer minutes per exception, Clause 16 ninety-day drift, Clause 17 drift detection lead time, Clause 18 incident mean time to restore, Clause 19 rollback time, Clause 20 report completeness, Clause 21 evidence, records and audit, Clause 22 remedies, re-measurement and persistent failure, Clause 23 exclusions and measurement disputes | [`02-clauses-12-to-23.md`](contract-clauses/02-clauses-12-to-23.md) |
| 03 | 3. How these clauses sit with the acceptance criteria library, 4. Placeholders to be set before signature, 5. Which clauses a lawyer must review before first use | [`03-sections-3-to-5.md`](contract-clauses/03-sections-3-to-5.md) |

Clause 1 and Clauses 21 to 23 travel with every set. Section 4, in part 03, is the placeholder checklist to work through before signature; section 5, in the same part, is the lawyer-review list.
