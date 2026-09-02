<!-- Benchmark contract clauses, part 3. Indexed in ../contract-clauses.md. Sections 3 to 5. -->

## 3. How these clauses sit with the acceptance criteria library

3.1 `06-delivery/acceptance-criteria-library.md` is where a delivery lead chooses what "done" means. This document is where the chosen row becomes contract language. The mapping is one to one where a library row already exists, and the clause adds a definition where it does not.

| Library row | Clause here | What the clause adds |
|---|---|---|
| Document intelligence, field-level accuracy | 2 | The denominator rule that counts invented fields as assessed and incorrect |
| Document intelligence, straight-through rate | 3 | The sampled-audit convention, and the tie to the accuracy floor |
| Document intelligence, exception rate | 4 | The entry-code basis, the threshold record, and the identity with the straight-through rate |
| Document intelligence, latency | 7 | The nearest-rank method and the exclusion of queue age |
| Document intelligence, audit completeness | 20 | The report element basis and the "figure without a sample size fails" rule |
| Voice and chat, containment | 8 | The three-part definition, the seven-day repeat test and the whole-population denominator |
| Voice and chat, handoff correctness | 10 | Recall, precision and quality as three separate floors |
| Voice and chat, escalation latency | 10, 12 | The turn budget and the first-token measurement |
| Voice and chat, policy-compliance sampling | 11 | The hallucinated-policy classes and the zero tolerance in the financial class |
| Back-office, transaction accuracy | 2, 13 | The Item-level automation definition alongside field accuracy |
| Back-office, exception-handling completeness | 15 | Reviewer minutes as a reporting and redesign duty |
| Cross-cutting, runbook delivered | 19 | Rollback time and the rehearsal duty |
| No library row yet | 5, 6, 9, 14, 16, 17, 18 | Calibration, cost per document, false containment, wrong-automation rework, ninety-day drift, drift detection lead time, and mean time to restore |

3.2 Where a clause here creates a measure the library does not carry, the library is updated in the same change, so that the two documents do not drift apart. That update is an item for a person, listed in section 4.

## 4. Placeholders to be set before signature

Every entry below is a decision. A placeholder left in a signed document is a defect.

| Clause | Placeholder | Who decides |
|---|---|---|
| 1.1 | The Measurement Method version annexed | Benchmark owner, delivery lead |
| 2.3, 2.4 | Accuracy floor overall and per Tracked Field; monthly sample size | Delivery lead with the Partner process owner |
| 3.3, 3.6 | Straight-through floor; proposal period after a miss | Delivery lead |
| 4.3 | Exception-rate ceiling | Delivery lead with the Partner process owner |
| 5.3, 5.6 | Expected calibration error ceiling; high-confidence accuracy floor; recalibration period | ML engineer, delivery lead |
| 6.3, 6.6 | Cost per Document ceiling and tolerance; notice and remedy periods | Delivery lead, accountant |
| 7.3 | Latency ceilings at the 50th and 95th percentiles | Delivery lead with the Partner process owner |
| 8.3 | Containment floor | Delivery lead with the Partner process owner |
| 9.3 | False containment ceiling | Delivery lead |
| 10.3, 10.4 | Escalation recall, precision and quality floors; monthly sample size | Delivery lead, Partner process owner |
| 11.3, 11.4, 11.6 | Hallucinated-policy ceiling; sample size; corrective plan period | Delivery lead, Partner process owner |
| 12.3 | Time to first token and first substantive token ceilings | Delivery lead |
| 13.3 | Automation rate floor | Delivery lead with the Partner process owner |
| 14.3, 14.6 | Rework ceiling per thousand automated Items; open exposure ceiling; remedy period | Delivery lead, Partner process owner |
| 15.2, 15.3, 15.6 | Idle cut-off; trigger figure; analysis and implementation periods | Operations lead, Partner process owner |
| 16.2, 16.3 | Live sample size; drift ceiling in percentage points | ML engineer, delivery lead |
| 17.3, 17.6 | Notice and detection ceilings in business hours | Operations lead, delivery lead |
| 18.3 | Resolution targets per Severity, from Retainer Schedule clause 3.1 | Delivery lead, Partner lead |
| 19.3 | Rollback and re-queue ceilings | Engineering lead, operations lead |
| 21.3, 21.4 | Record retention months; audit notice period | Security lead, lawyer |
| 22.2, 22.4 | Service-credit percentages for each measure with no existing row; re-measurement period | Founder, lawyer, accountant |
| 23.2 | Which additional exclusions, if any, the SOW allows | Lawyer, delivery lead |
| Section 3.2 | Update `06-delivery/acceptance-criteria-library.md` with the rows clauses 5, 6, 9, 14, 16, 17 and 18 create | Delivery lead |

## 5. Which clauses a lawyer must review before first use

None of this has been reviewed. The list below is what a lawyer should look at first, and why, so the review is not a general reading of twenty-three clauses.

| Clause | Why it needs review |
|---|---|
| 1.1 to 1.3 | Incorporating an external document by reference, and freezing the annexed version. Confirm the annexed copy governs, that a later publication cannot change a signed obligation, and that Clause 1.3 is a real restriction on the Provider changing a definition after signature |
| 1.6, 22.6 | The interaction with SOW clause 2.4 and MSA clause 2.4 on precedence, so that a measurement Schedule cannot override the MSA by implication |
| 2.6, 4.6, 7.6, 10.6, 11.6, 16.6, 17.6 | Each of these makes a measurement failure a Severity 2 Incident. Confirm this is the intended trigger for the Retainer Schedule remedies, and that it does not expand the Provider's exposure beyond the liability cap in MSA clause 14 |
| 11.3, 11.6 | A zero-tolerance obligation on a class of statements, with a Severity 2 on first occurrence. Confirm the drafting is workable and that the class list in the Schedule is closed rather than open-ended |
| 14.6, 15.6, 5.6, 3.6 | Obligations to perform work "at no charge" following a miss. Confirm the scope is bounded and that it does not become an uncapped remediation duty |
| 22.2 | New service-credit rows in Retainer Schedule clause 7.1 with placeholder percentages, and the cap in clause 7.2. This is the clause the Retainer Schedule cover note already flags: confirm the credits are a genuine pre-estimate and not a penalty under section 74 of the Indian Contract Act 1872 |
| 22.3 | Service credits as sole financial remedy, read against MSA clause 11.3, and the carve-outs for the DPA and MSA clause 14.4 |
| 22.5 | The persistent-failure termination right applying to every measure in the Schedule, which materially widens the trigger in Retainer Schedule clause 7.4 |
| 21.4, 21.5 | The audit right, the Partner's right to substitute its own sample, and the rule that the Partner's sample governs. Confirm the notice period and frequency are acceptable and that the tooling duty is bounded |
| 21.6 | Evidence delivered in a form the Partner may pass to its own client. Confirm this against the DPA and against MSA clause 3, and that it creates no direct relationship with the Partner Client |
| 23.1 to 23.4 | Exclusions incorporated from Retainer Schedule clause 10, the late-claim bar in 23.3, and the duty in 23.4 to report a measure both with and without excluded items |
| 23.5 | The no-withholding rule during a measurement dispute, read against MSA clause 20 and the payment terms in MSA clause 12 |

5.1 Two further items are for a person rather than a lawyer. An accountant should confirm the currency and the price-basis wording in Clause 6, which ties a contractual ceiling to a third party's published list price. The founder should decide the service-credit percentages in Clause 22.2 before any of these clauses is offered to a partner, because the clauses are unusable without them.

5.2 Nothing in this document has been reviewed, signed, sent or relied on. It is drafting held in `10-benchmarks/charter/` until the review in this section is complete and the placeholders in section 4 are set.
