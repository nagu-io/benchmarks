<!-- Benchmark contract clauses, part 2. Indexed in ../contract-clauses.md. Section 2, Clauses 12 to 23. -->

### Clause 12 — Time to first token

12.1 Measure bound. How long a caller waits for the Agent to begin answering.

12.2 Measurement method. As the Measurement Method section 3.13: the elapsed time from the end of the caller's turn, or of caller speech, to the first token or audio sample of the Agent's reply, reported as the 50th and 95th percentiles by the nearest-rank method over Agent turns in the Measurement Window, excluding the Agent's opening turn, which is reported separately. Where the Agent emits a holding phrase before answering, time to first substantive token is reported alongside.

12.3 Ceiling. 95th percentile not more than placeholder seconds. Time to first substantive token, 95th percentile, not more than placeholder seconds.

12.4 Measurement Window. Each calendar month, and continuously for alerting purposes.

12.5 Evidence. The Partner receives the percentiles, the turn count, the opening-turn figures and the substantive-token figures in the Monthly Report, together with the endpointing source used.

12.6 Breach. The 95th percentile above the ceiling for the Measurement Window is a Severity 3 Incident. A holding phrase shall not be reported as the Agent's reply for the purposes of this clause.

### Clause 13 — Automation rate

13.1 Measure bound. The share of Items carried to a final state with no human action.

13.2 Measurement method. As the Measurement Method section 3.14: Items carried to a final state with no human action of any kind, divided by Items admitted to processing in the Measurement Window, where Items admitted means Items received less Items rejected before processing by a rule named in SOW clause 2.2. Items open at the end of the Window are reported as in flight.

13.3 Floor. Not less than placeholder percent.

13.4 Measurement Window. Each calendar month.

13.5 Evidence. The Partner receives the volume and automation table in the Monthly Report under Retainer Schedule clause 5.2.2, showing Items received, rejected before processing, admitted, automated, routed to review, in flight, and the automation rate.

13.6 Breach. The automation rate is not satisfied in any Measurement Window in which the wrong-automation rework ceiling in clause [X] is exceeded, whatever the automation figure. An automation rate below the floor while the rework ceiling is met is a Severity 3 Incident and the Provider shall propose a change within placeholder Business Days at no charge.

### Clause 14 — Wrong-automation rework

14.1 Measure bound. The labour caused by Items the System completed automatically and wrongly.

14.2 Measurement method. As the Measurement Method section 3.15: the sum of detection, correction and downstream correction minutes attributable to Items completed automatically and incorrectly, divided by Items completed automatically and expressed per one thousand such Items, using the labour model in clause [X]. Error classes with no detection route within the Measurement Window are reported as an open exposure count with the class named, and are not assigned an estimated minute figure.

14.3 Ceiling. Not more than placeholder minutes per one thousand automated Items, and an open exposure count of not more than placeholder Items per Measurement Window.

14.4 Measurement Window. Each calendar month, measured on the sampled audit of automated Items at the audit rate stated in SOW clause [X], grossed to the automated population with the sample size stated.

14.5 Evidence. The Partner receives the rework table in the Monthly Report showing, per error class, the count found in the audit sample, the detection route, the minutes per Item from the labour model, the total minutes, the rework per thousand automated Items, and the open exposure count with each class named.

14.6 Breach. Rework above the ceiling for a Measurement Window attracts the service credit for a measure below floor, and the Provider shall within placeholder Business Days lower the affected confidence thresholds or add the validation rule needed to route the affected class to review, at no charge, and restate the resulting automation rate before the change is applied.

### Clause 15 — Reviewer minutes per exception

15.1 Measure bound. The reviewer time each exception takes, which is the Partner's cost and therefore a reporting and redesign duty rather than a Provider performance guarantee.

15.2 Measurement method. As the Measurement Method section 3.16: total reviewer active time recorded against exceptions closed in the Measurement Window, divided by exceptions closed, reported as a mean and a median and broken down by queue entry code, with an idle cut-off of placeholder seconds. Queue waiting time, training time and sampled-audit reviews are excluded and reported separately.

15.3 Trigger figure. Placeholder minutes, mean, per exception. This figure is a trigger for the duty in Clause 15.6 and is not a Service Level.

15.4 Measurement Window. Each calendar month.

15.5 Evidence. The Partner receives the reviewer-time table in the Monthly Report showing exceptions closed, mean and median minutes overall and per entry code, audit minutes separately, and the total reviewer hours implied for the Window.

15.6 Breach. Where the mean exceeds the trigger figure in two consecutive Measurement Windows, the Provider shall, at no charge, analyse the causes and deliver a written proposal within placeholder Business Days covering thresholds, validation rules, queue design, interface changes or the model, and shall implement the option the Partner selects within placeholder Business Days. A failure to deliver the analysis is a failure of a Monthly Report element under clause [X].

### Clause 16 — Ninety-day drift

16.1 Measure bound. The movement of the tracked measures between acceptance and later Measurement Windows.

16.2 Measurement method. As the Measurement Method section 3.17: for each Tracked Measure, the figure at acceptance and the figure in the current Measurement Window, reported both on the Labelled Set version used at acceptance and on a fresh labelled sample of placeholder Items drawn from the preceding thirty days of live input, with both endpoints and both sample sizes stated. Changes agreed under SOW clause 10 are reported with their change reference and excluded from the drift figure.

16.3 Ceiling. A fall of not more than placeholder percentage points on the Labelled Set against the acceptance figure, and no Tracked Measure below its floor on the live sample.

16.4 Measurement Window. Each calendar month, and in full at ninety days after acceptance of milestone M4.

16.5 Evidence. The Partner receives, in the Monthly Report under Retainer Schedule clause 5.2.7, both endpoints, both sample sizes, the frozen-set and live-sample figures, the attribution between system change and input change, and the model, prompt and threshold versions at each endpoint.

16.6 Breach. A fall greater than the ceiling on the Labelled Set, or any Tracked Measure below its floor on the live sample, is a Severity 2 Incident under Retainer Schedule clause 4. The Provider shall place the affected class under review in accordance with `06-delivery/ops-runbook.md` section 5 and shall report the cause, the corrective action and the recovery criterion in the Monthly Report.

### Clause 17 — Drift detection lead time

17.1 Measure bound. How long the Provider takes to notice a change in the input and to tell the Partner about it.

17.2 Measurement method. As the Measurement Method section 3.18: the elapsed time from the first Item belonging to a shifted input population to the Provider's written notice to the Partner naming the affected class and the supporting evidence, with the internal detection timestamp reported alongside. Drift the Partner announced in advance is excluded. Where no notice was given inside the Measurement Window, the figure is reported as "not detected within the window" with the window length.

17.3 Ceiling. Written notice within placeholder business hours of onset. Internal detection within placeholder business hours of onset.

17.4 Measurement Window. Continuous, reported each calendar month and assessed in any Day-60 exercise run under clause [X].

17.5 Evidence. The Partner receives, for each drift observation, the onset timestamp established from the record, the detection timestamp, the notice timestamp, the signal that fired, the affected class and the action taken, in the Monthly Report and in the notice itself.

17.6 Breach. A drift not notified within the ceiling is a Severity 2 Incident under Retainer Schedule clause 4 and attracts the corresponding service credit. A drift detected internally and not notified within placeholder business hours of detection is a Severity 2 Incident whatever the onset time.

### Clause 18 — Incident mean time to restore

18.1 Measure bound. How long the Provider takes to restore service after an Incident.

18.2 Measurement method. As the Measurement Method section 3.19: for each Severity, the sum of restoration durations for Incidents closed in the Measurement Window divided by the count of those Incidents, where the clock starts at the earlier of the Provider's detection and the Partner's notice and stops when a monitoring check confirms that work submitted at intake reaches an output or the human review queue within the Service Level. Time waiting on a Partner dependency stops the clock and is reported separately.

18.3 Ceiling. The resolution targets in Retainer Schedule clause 3.1 for each Severity, which are placeholders to be set in the SOW.

18.4 Measurement Window. Each calendar month.

18.5 Evidence. The Partner receives, for each Severity, the Incident count, the mean, the median and the maximum restoration time, the time excluded as waiting on a Partner dependency, and the Incident record for each Incident under Retainer Schedule clause 4.3.

18.6 Breach. A missed resolution target attracts the service credit at Retainer Schedule clause 7.1 for the Severity concerned. Reporting a mean without the count, the median and the maximum does not satisfy clause 18.5.

### Clause 19 — Rollback time

19.1 Measure bound. How quickly the Provider can put the previous release back and clear the outputs of the release it replaced.

19.2 Measurement method. As the Measurement Method section 3.20: the elapsed time from the recording of a rollback decision to the previous signed release serving production traffic and passing the smoke set with its model pin, prompt version and threshold set restored, with decision time and re-queue completion time reported alongside. Rehearsals are labelled as rehearsals and reported separately from rollbacks performed on production.

19.3 Ceiling. Rollback within placeholder minutes of the decision. Re-queue of affected Items complete within placeholder hours of the decision.

19.4 Measurement Window. Each rollback, and at least one rehearsal each calendar quarter.

19.5 Evidence. The Partner receives the rollback record: the criterion met and its timestamp, the decision timestamp, the restored tag and pins, the smoke-set result, the re-queue count and completion time, and the change record reference, in the Monthly Report and, for a rollback in production, within the response time for the Severity concerned.

19.6 Breach. A rollback exceeding the ceiling, or a quarter with no rehearsal recorded, is a Severity 3 Incident. A rollback that restores service without re-queueing the Items processed by the withdrawn release does not satisfy this clause.

### Clause 20 — Report completeness

20.1 Measure bound. Whether the Monthly Report contains what it is required to contain.

20.2 Measurement method. As the Measurement Method section 3.21: the number of required Monthly Report elements that are present, cover the whole reporting period and carry the sample size or the basis for each figure, divided by the number of elements required by Retainer Schedule clause 5.2 and this SOW. An element that does not apply in the period is satisfied by an explicit statement to that effect and fails if it is simply absent. Timeliness is assessed separately.

20.3 Floor. One hundred percent, on the basis in Clause 20.2. Delivery by the fifth Business Day of the following month. This is the one measure in this Schedule whose floor is not a placeholder: a report element is either present and supported or it is not, and a partial floor would only invite an argument about which element could be left out.

20.4 Measurement Window. Each calendar month.

20.5 Evidence. The Partner receives the Monthly Report itself, and a completeness line at its front listing the required elements, their status, and any element stated as not applicable for the period.

20.6 Breach. A missing or unsupported element, or late delivery, attracts the service credit at Retainer Schedule clause 7.1 for a late Monthly Report. A figure reported without its sample size or its basis does not satisfy the element it belongs to, and the element is counted as missing.

### Clause 21 — Evidence, records and audit

21.1 For every measure in this Schedule the Provider shall produce, and the Partner shall receive, the evidence named in that measure's clause, delivered with the Monthly Report or, where the clause states a shorter time, within that time.

21.2 Each item of evidence carries the run identifier, the Measurement Window, the sample size, the Labelled Set version where one was used, and the model, prompt, schema and threshold versions in force, as `06-delivery/build-standards.md` section 8.1 requires.

21.3 The Provider shall retain the underlying records for each measure for placeholder months, including raw System outputs, queue and audit logs, Incident records and the configuration in force, so that any figure can be recomputed rather than argued about.

21.4 The Partner may audit any measure on placeholder Business Days' written notice, once per calendar year and additionally after any Severity 1 or Severity 2 Incident, by inspecting the records in Clause 21.3 or by re-running the measurement on a sample it draws itself. The Provider shall give the Partner the tooling and the instructions needed to do so.

21.5 The Partner may substitute its own random sample of equal size for any sample the Provider proposes, as Retainer Schedule clause 3.3 provides. Where the two samples give different figures, both are reported and the Partner's sample governs.

21.6 Evidence produced under this Schedule is the Partner's, is delivered in a form the Partner may pass to its own client under its own name without Provider branding, and contains no data belonging to any other partner of the Provider.

### Clause 22 — Remedies, re-measurement and persistent failure

22.1 At acceptance, a measure below its floor or above its ceiling means the Deliverable is not accepted. SOW clause 6.2 applies: the Provider corrects and redelivers, and a further Acceptance Period runs. The Partner may waive a measure in writing on the sign-off form; there is no other route past it.

22.2 In the run phase, a measure below its floor or above its ceiling attracts the service credit stated in Retainer Schedule clause 7.1 for that measure. Where clause 7.1 carries no row for the measure, a row is added to it in this SOW with a placeholder percentage, and the credit cap in Retainer Schedule clause 7.2 applies to the total.

22.3 Service credits are the Partner's sole financial remedy for a Service Level failure, as MSA clause 11.3 and Retainer Schedule clause 7.3 state. This Schedule does not limit the Partner's rights under the DPA or under MSA clause 14.4.

22.4 Re-measurement. Where the Provider disputes a figure, the Provider may re-measure once within placeholder Business Days on a sample the Partner draws. The re-measured figure replaces the original only where the original was produced from a defective sample, a harness defect or a configuration error, each of which the Provider must evidence. A re-measurement does not extend a notice period or a correction period.

22.5 Persistent failure. Retainer Schedule clause 7.4 applies to every measure in this Schedule: the same measure missed in three consecutive calendar months, or any measure missed in four of any six consecutive months, gives the Partner the right to terminate the affected SOW on 30 days' written notice under MSA clause 18.3 without a cure period, with exit assistance under MSA clause 19.

22.6 No measure in this Schedule is satisfied by a change to its own definition. A definition change takes effect only under Clause 1.3, only from the next Measurement Window, and only with both bases reported for the Window in which it is made.

### Clause 23 — Exclusions and measurement disputes

23.1 A failure of a measure in this Schedule is excluded, and no service credit accrues, to the extent it is caused by any of the matters listed in Retainer Schedule clause 10.1, which are incorporated into this Schedule without change.

23.2 In addition, and only where the SOW says so, a measure is excluded to the extent it is caused by: input types, formats, languages or volumes outside the assumptions in SOW clause 8.1; the Partner's failure to staff the review queue at the level in SOW clause 8.1.5; or a Labelled Set the Partner supplied that does not meet the labelling guide in clause [X].

23.3 The Provider shall claim an exclusion in the Monthly Report for the Window in which it arose, with the evidence. An exclusion claimed later is not available.

23.4 An exclusion suspends the credit, not the reporting. The Provider reports the measure, states the exclusion and its evidence, and reports the measure with the excluded items removed as well as with them included.

23.5 Where the parties disagree about a figure or an exclusion, the escalation matrix in Retainer Schedule clause 6 applies, and MSA clause 20 governs a dispute that is not resolved there. Neither party withholds an invoice or a credit while a measurement dispute is open.
