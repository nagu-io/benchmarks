<!-- Benchmark contract clauses, part 1. Indexed in ../contract-clauses.md. Section 2, Clauses 1 to 11. -->

## 2. The clause set

### Clause 1 — Definitions and incorporation of the measurement method

1.1 The measures in this Schedule are calculated in accordance with the document titled "Benchmark charter and methodology", version placeholder, published by the Provider (the "Measurement Method"). A copy of the version in force at the date of this SOW is annexed. The annexed copy prevails over any later version for the purposes of this SOW.

1.2 Where a measure in this Schedule states a numerator, a denominator or an exclusion, that statement prevails over the Measurement Method. Where this Schedule is silent, the Measurement Method applies.

1.3 The Provider shall not change a definition, a denominator, an exclusion, a confidence threshold or a match rule that affects a measure in this Schedule without the Partner's prior written agreement recorded through the change-control form in SOW clause 10. A change agreed under this clause takes effect from the start of the next Measurement Window and is stated in the next Monthly Report, together with the measure calculated on both the old and the new basis for that Window.

1.4 Every figure reported under this Schedule is accompanied by its sample size, its Measurement Window, the Labelled Set version where one was used, and the model, prompt and threshold versions in force. A figure reported without those items does not satisfy the obligation to report it.

1.5 Rounding does not create compliance. A floor is met only where the unrounded figure meets it, and a ceiling is met only where the unrounded figure is at or below it.

1.6 Where a measure was not produced by a measurement, it is reported as "not measured" with the reason. The Provider shall not report an estimated, extrapolated or illustrative figure as a result.

### Clause 2 — Field-level accuracy

2.1 Measure bound. Field-level accuracy of the System on the Labelled Set and, in the run phase, on the monthly sample drawn under Retainer Schedule clause 3.3.

2.2 Measurement method. As the Measurement Method section 3.3: the number of field instances whose returned value matches the labelled value under the match rules in clause [X], divided by the number of field instances assessed, being every field instance in the Labelled Set for the Documents scored plus every field returned by the System for which the Labelled Set holds no counterpart. Field instances marked unreadable by the labeller are excluded and reported separately.

2.3 Floor. Not less than placeholder percent overall, and not less than placeholder percent for each field listed as a Tracked Field in clause [X].

2.4 Measurement Window. At acceptance, on the Labelled Set at milestone M2 and again at M5. In the run phase, each calendar month, on the monthly sample of placeholder Documents.

2.5 Evidence. The Partner receives the harness report for each measurement, carrying the run identifier, the Labelled Set version, the model, prompt and threshold pins, the per-field table, the sample size and the exclusions, delivered with the Monthly Report and retained for the period in clause 21.

2.6 Breach. At acceptance, the Deliverable is not accepted and SOW clause 6.2 applies. In the run phase, accuracy below the floor for a Measurement Window is a Severity 2 Incident under Retainer Schedule clause 4, attracting the service credit at Retainer Schedule clause 7.1 for accuracy below floor, and the Provider shall state the cause and the corrective action in the Monthly Report. Three consecutive Windows below the floor engage Retainer Schedule clause 7.4.

### Clause 3 — Straight-through-processing rate

3.1 Measure bound. The share of Documents that leave the System with no human action.

3.2 Measurement method. As the Measurement Method section 3.4: Documents released with no human action of any kind, divided by Documents admitted to processing in the Measurement Window, where Documents admitted means Documents received less Documents rejected before processing by a rule named in SOW clause 2.2. A Document drawn into the sampled audit counts as straight-through only where the audit changed nothing.

3.3 Floor. Not less than placeholder percent.

3.4 Measurement Window. Each calendar month, and at milestones M2 and M5 on the Labelled Set.

3.5 Evidence. The Partner receives the volume table in the Monthly Report under Retainer Schedule clause 5.2.1, showing Documents received, rejected before processing, admitted, released straight through, and routed to review, with the audit count and the audit change count stated separately.

3.6 Breach. This floor is not satisfied in any Measurement Window in which the accuracy floor in clause [X] is missed, whatever the straight-through figure. A straight-through rate below the floor while accuracy is at or above the floor is a Severity 3 Incident and the Provider shall propose a threshold or model change within placeholder Business Days at no charge.

### Clause 4 — Exception rate

4.1 Measure bound. The share of Documents that enter the human review queue.

4.2 Measurement method. As the Measurement Method section 3.5: Documents with at least one review-queue entry under any entry code other than a sampled audit that resulted in no change, divided by Documents admitted to processing. The straight-through rate in clause [X] and this rate use the same denominator and sum to one hundred percent.

4.3 Ceiling. Not more than placeholder percent, measured at the confidence thresholds recorded in the configuration in force during the Measurement Window.

4.4 Measurement Window. Each calendar month.

4.5 Evidence. The Partner receives the exception table in the Monthly Report under Retainer Schedule clause 5.2.3, broken down by entry code, with the confidence thresholds in force and the date of any threshold change during the Window.

4.6 Breach. Exception rate above the ceiling for the Measurement Window attracts the service credit at Retainer Schedule clause 7.1 for exception rate above ceiling. Exception rate above the ceiling for two consecutive Business Days is a Severity 2 Incident under Retainer Schedule clause 4. The Provider shall not lower the exception rate by raising a confidence threshold without the Partner's written agreement under Clause 1.3.

### Clause 5 — Confidence calibration

5.1 Measure bound. The expected calibration error of the confidence the System reports, and the accuracy of its high-confidence outputs.

5.2 Measurement method. As the Measurement Method section 3.6: the weighted mean absolute difference between the accuracy and the mean reported confidence of each of ten equal-width confidence bins, over field instances carrying a reported confidence; and separately the accuracy of field instances returned with a confidence of 0.95 or above. Field instances with no reported confidence are excluded and their share is reported.

5.3 Ceiling and floor. Expected calibration error not more than placeholder. Accuracy of field instances at or above 0.95 confidence not less than placeholder percent.

5.4 Measurement Window. At milestones M2 and M5 on the Labelled Set, and each calendar quarter in the run phase on the accumulated monthly samples.

5.5 Evidence. The Partner receives the calibration section of the harness report, including the reliability diagram, the per-bin table with counts, and the share of outputs carrying no confidence.

5.6 Breach. Where either figure is missed, the Provider shall recalibrate the confidence thresholds at no charge within placeholder Business Days, shall restate the expected exception rate and accuracy at the new thresholds before applying them, and shall obtain the Partner's written agreement under Clause 1.3.

### Clause 6 — Cost per document

6.1 Measure bound. The provider and compute cost of processing a Document.

6.2 Measurement method. As the Measurement Method section 3.7: the total provider and compute charges incurred in processing Documents in the Measurement Window, at the list prices in force on the date stated in the Monthly Report, divided by Documents admitted to processing. Human review labour, build cost and any negotiated discount are excluded.

6.3 Ceiling. Not more than placeholder per Document in the currency stated in SOW clause 1, with a tolerance of placeholder percent.

6.4 Measurement Window. Each calendar month.

6.5 Evidence. The Partner receives the cost line in the Monthly Report, stating the total charges, the Document count, the cost per Document, the price list date, and each provider and service contributing to the total.

6.6 Breach. Where the figure exceeds the ceiling plus the tolerance, the Provider shall notify the Partner within placeholder Business Days with the cause and the options to restore it, and shall implement the agreed option within placeholder Business Days. Where the cause is a provider price change outside the Provider's control, the parties shall treat it as a change under SOW clause 10 rather than as a Service Level failure.

### Clause 7 — Latency

7.1 Measure bound. The time taken to process a Document.

7.2 Measurement method. As the Measurement Method section 3.8: the elapsed time from admission of a Document to processing until the complete validated output is written or the Document enters the human review queue, whichever occurs first, reported as the 50th, 95th and 99th percentiles by the nearest-rank method over Documents completed in the Measurement Window. Time in the human review queue is excluded and reported separately as queue age.

7.3 Ceiling. 95th percentile not more than placeholder seconds. 50th percentile not more than placeholder seconds.

7.4 Measurement Window. Each calendar month, and continuously for alerting purposes.

7.5 Evidence. The Partner receives the latency percentiles, the Document count, the maximum, and the queue-age figures in the Monthly Report, and has read access to the same measures in the portal.

7.6 Breach. The 95th percentile above the ceiling for the Measurement Window is a Severity 3 Incident. The 95th percentile above the ceiling on each of three consecutive Business Days is a Severity 2 Incident under Retainer Schedule clause 4 and engages the corresponding service credit.

### Clause 8 — Containment

8.1 Measure bound. The share of Contacts the Agent resolved without a person and without the caller coming back.

8.2 Measurement method. As the Measurement Method section 3.9: Contacts in which the caller's stated intent was resolved in accordance with the outcome definitions in clause [X], no person was requested by the caller and none joined or performed work on the Contact, and no further Contact was received from the same caller regarding the same intent within seven calendar days, divided by all Contacts routed to the Agent, including Contacts whose intent falls outside the Agent's configured scope. A Contact that ended without resolution is not contained, however it ended.

8.3 Floor. Not less than placeholder percent under this definition. Any figure the Provider reports under a different definition is reported alongside this one and never in place of it.

8.4 Measurement Window. Each calendar month, with the seven-day repeat-contact test applied to Contacts that began at least seven days before the end of the Window; Contacts beginning inside the final seven days are carried into the next Window and the carry count is stated.

8.5 Evidence. The Partner receives the containment table in the Monthly Report showing, for the Window: Contacts routed, Contacts excluded under the Measurement Method section 3.9.5 with the reason, Contacts resolved, Contacts in which a person was requested, Contacts followed by a repeat within seven days, the containment figure under this clause, and the figure under each other definition the Provider or any third party reports.

8.6 Breach. Containment below the floor for the Measurement Window attracts the service credit at Retainer Schedule clause 7.1 for a measure below floor. Three consecutive Windows below the floor engage Retainer Schedule clause 7.4. The Provider shall not raise the figure by narrowing the denominator; a change to the denominator is a change under Clause 1.3.

### Clause 9 — False containment

9.1 Measure bound. The share of Contacts counted as contained under any other definition that are not contained under clause [X].

9.2 Measurement method. As the Measurement Method section 3.10: Contacts counted as contained under the named reference definition that fail at least one condition of clause [X], divided by Contacts counted as contained under that reference definition, broken down by the failing condition: not resolved, a person requested and not provided, or a repeat Contact within seven days.

9.3 Ceiling. Not more than placeholder percent against any definition the Provider reports. Where the Provider reports containment only under clause [X], this clause imposes a reporting duty and no ceiling.

9.4 Measurement Window. Each calendar month, on the same basis as clause [X].

9.5 Evidence. The Partner receives, in the Monthly Report, each containment definition the Provider or any platform in the delivery chain reports, its figure, and the false containment rate against it with the failing-condition breakdown.

9.6 Breach. A failure to report a definition in use, or to report the false containment rate against it, is a failure of the Monthly Report element under clause [X] and attracts the service credit for a late or incomplete Monthly Report. A false containment rate above the ceiling is a Severity 3 Incident and the Provider shall report the cause and the corrective action in the next Monthly Report.

### Clause 10 — Escalation accuracy

10.1 Measure bound. Whether the Agent hands a Contact to a person when it must, and does not when it need not.

10.2 Measurement method. As the Measurement Method section 3.11. Escalation recall means Contacts requiring escalation under clause [X] in which the Agent escalated within the turn budget stated for that trigger, divided by Contacts requiring escalation. Escalation precision means correct escalations divided by all escalations made. Escalation quality means escalations reaching the destination in clause [X] carrying every required context field, divided by escalations made.

10.3 Floors. Escalation recall not less than placeholder percent. Escalation precision not less than placeholder percent. Escalation quality not less than placeholder percent.

10.4 Measurement Window. At acceptance on the Labelled Set, and each calendar month on a random sample of placeholder Contacts reviewed against the escalation rules in clause [X].

10.5 Evidence. The Partner receives the escalation table in the Monthly Report showing Contacts requiring escalation, escalations made, correct escalations, escalations reaching the right destination with full context, and the list of Contacts in which a required escalation did not occur.

10.6 Breach. A failure to escalate on an explicit request for a person, or on a distress cue on the list in clause [X], is a Severity 2 Incident under Retainer Schedule clause 4 on each occurrence, regardless of the measured rate, and the Provider shall notify the Partner within the Severity 2 response time. Recall or precision below its floor for a Measurement Window attracts the service credit for a measure below floor.

### Clause 11 — Hallucinated-policy rate

11.1 Measure bound. The share of Contacts in which the Agent asserted something the policy pack does not support.

11.2 Measurement method. As the Measurement Method section 3.12: Contacts containing at least one assertion of a policy, price, entitlement, timeframe or procedure not supported by the policy pack in force for that Contact, divided by Contacts containing at least one policy assertion, with the rate over all Contacts reported beside it and with assertions classified as financial or entitlement, regulated disclosure, procedural, or incidental.

11.3 Ceiling. Not more than placeholder percent overall. Zero in the financial, entitlement and regulated-disclosure classes listed in clause [X].

11.4 Measurement Window. Each calendar month, on a random sample of placeholder Contacts, plus every Contact the Partner refers for review.

11.5 Evidence. The Partner receives the hallucinated-policy table in the Monthly Report with the rate, the class breakdown, the sample size, the judge model and prompt versions where a judge was used, the judge agreement figure, and the transcript reference for every unsupported assertion found.

11.6 Breach. An unsupported assertion in the financial, entitlement or regulated-disclosure classes is a Severity 2 Incident under Retainer Schedule clause 4 on the first occurrence, whatever the measured rate, and is reported to the Partner within the Severity 2 response time with the transcript and the corrective action. A rate above the overall ceiling attracts the service credit for a measure below floor and requires a written corrective plan within placeholder Business Days.
