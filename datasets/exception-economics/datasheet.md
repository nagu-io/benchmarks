# Datasheet — Exception Economics dataset v1.0.0

Follows the structure of Gebru et al., "Datasheets for Datasets" (2018).
Dataset version 1.0.0 · Schema version 1.0 · Seed 20260902 · Written 2026-09-02 ·
Charter version 1.0.0.

**This data is synthetic.** Every item was written by `generate.py`. No ticket, case
or invoice was taken from a real one. No item contains a real company, a real person
or a real address, and every identifier is invalid by construction. What that means
for a reader of a result is set out in "Known biases and limitations", and it is not a
footnote.

**No system has been run against this dataset.** The figures in
`results/exception-economics-v1.0/` are produced by scoring a synthetic reference
decision policy that ships with the data. They are arithmetic. They are not a
measurement of any model, service or vendor.

---

## Motivation

**Why was the dataset created?**

Back-office automation is sold on one number: the share of work items the system
handles without a person. That number is not a result on its own. A system that
automates every item and is wrong on a tenth of them can cost more than one that
automates half and is right, because the work created by a wrong automation is not the
work saved by a right one, and because some wrong automations are never found at all.

This dataset is one half of the measurement of that trade. `labour-model.yaml` is the
other half: it converts the outcomes into reviewer minutes, rework minutes and money,
so that automation rate and its cost can be read on the same row. The metric
definitions live in `10-benchmarks/charter/methodology.md` sections 3.14 to 3.17 and
govern everything here.

**Who created it and who funded it?**

Entailment Labs, for its own benchmark programme. No external funding, no sponsorship
and no paid placement (charter 5.7).

---

## Composition

**What do the instances represent?**

One instance is one back-office work item: a unit of work with a known correct final
state. Three kinds.

| Work type | Items | The decision to be made | The final states |
|---|---|---|---|
| `ticket_triage` | 790 | Categorise a support ticket, set its priority, decide whether it must be escalated | One of ten baseline categories or four unseen ones, one of four priorities, escalate or not |
| `kyc_case` | 495 | Pass, refer or reject a know-your-customer case and record the reason | `pass`, `refer` or `reject`, with one of six reason codes |
| `invoice_po_recon` | 715 | Match an invoice against one or more purchase orders, or hold it | `matched`, `partial_match_hold`, `exception_hold`, `reject`, with the purchase-order set |

Total 2,000 items.

**How many instances, and are there splits?**

| Split | Items | Published |
|---|---|---|
| `public_sample` | 100 | Yes, in `sample/`, committed in parts — see `sample/README.md` |
| `private_holdout` | 300 | No. Never published, per charter 5.10 |
| `open` | 1,600 | Not materialised separately; regenerable from the seed |

Both splits are stratified across work type and tier and drawn from a named
deterministic stream, so the split assignment is part of the ground truth rather than
a property of which folders exist.

**Is there a label or target?**

Yes. Every item carries `ground_truth.outcome`, a single string in the encoding
defined in `outcomes.py`. Every item carries a difficulty tier and the six tier
parameters that produced it, so the tier is checkable from the item.

**Is any information missing?**

By design, three things. First, no item carries a rendered document, an email body or
a transcript: the suite scores decisions and their cost, not extraction, which is what
the Messy Scan suite is for. Second, no item carries a real system's prediction; the
reference policy that ships with it is synthetic and labelled as such on every table.
Third, three error classes carry no rework minutes anywhere in the labour model,
because they have no detection route inside a monthly window. That absence is
deliberate and is reported as an open exposure count.

**Are relationships between instances made explicit?**

Items are independent. There is no threading, no repeat contact and no shared
customer across items, which is a simplification and is listed under limitations.

**Are there errors, noise or redundancies?**

Wrong outcomes in the reference policy are generated on purpose, at rates that rise
with the tier, and they are labelled. The generator's own draw can occasionally
reproduce the ground truth while trying to produce a wrong outcome; when it does, the
item is recorded as correct rather than as a wrong answer that happens to be right.
`validate.py` checks that the stored error class and the classifier agree on all 2,000
items.

**Does it contain confidential, offensive or personal data?**

No. Every name, company, city, identifier and amount is generated. No partner data of
any kind is present, and none ever will be, per charter 6.2.

**Are identifiers real?**

No, and they are invalid by construction rather than by chance, per charter 6.3.

| Identifier | Shape | Why it cannot be valid |
|---|---|---|
| Individual tax identifier, PAN-shaped | 10 characters | Position 4 holds a holder-type letter drawn from a fixed set in the real scheme; every one here holds `X`, which is not in that set |
| Business tax identifier, GSTIN-shaped | 15 characters | The leading state code is `00`, which is not an allocated state code, and the embedded PAN-shaped block is invalid as above |
| KYC document number | `KYC-ZZ######` | The `ZZ` block matches no issuing scheme in the model |

`validate.py` checks all three on every item and fails the build otherwise.

---

## Collection and generation process

**How was the data acquired?**

It was not acquired. It was generated by `generate.py` from a single integer seed.
Nothing was scraped, copied, purchased or derived from a real document.

**What was the sampling strategy?**

Every item's work type, tier and population are planned before any content is
generated, using the largest-remainder method so that the planned mix is exact rather
than approximate. Content, lifecycle and the reference policy are then drawn on three
separate named streams derived from the seed and the item id, so that adding a field
to one part of an item cannot move another part.

| Mix | Value | What it is |
|---|---|---|
| Work-type mix, baseline | ticket 0.40, KYC 0.25, reconciliation 0.35 | A design decision of the charter, not a measurement of any real queue |
| Tier mix, baseline | T1 0.20, T2 0.25, T3 0.25, T4 0.20, T5 0.10 | A design decision |
| Shifted population | 300 items, all tier 5 | Charter 4.4.2 makes tier 5 the only tier the drift simulation applies to |

**Over what timeframe?**

Items carry a received timestamp inside a thirty-day window beginning 2026-04-01. The
window is a property of the generated data, not a record of anything.

**Was an ethical review process conducted?**

No review board was involved, and none applies: the data is wholly generated and
contains no human subject. The data-ethics rules that do apply are in charter section
6, and `validate.py` enforces the ones that can be checked mechanically.

---

## Difficulty parameters

Charter 4.4 defines the tiers over six dimensions. Every item records the value
actually used for each one, so the tier can be verified from the item.

| Tier | Sources to reconcile | Key availability | Match cardinality | Tolerance rules | Order dependent | Ground truth basis |
|---|---|---|---|---|---|---|
| T1 | 1 | Exact key on both sides | One to one | None | No | Single answer, no judgement |
| T2 | 2 | Exact key, formatted differently | One to one | Amount rounding | No | Single answer |
| T3 | 2 to 3 | No exact key; name, amount, date window | One to many | Amount rounding, date window | No | Single answer via a labelling-guide rule |
| T4 | 3 to 4 | No exact key | Many to many | The above plus part-delivery split | Yes | Single answer; cost of error exceeds review |
| T5 | 3 to 5 | No exact key | Many to many | The above plus credit-note offset, wider date window | Yes | Two sources disagree; a policy document decides |

A tier is assigned only if every criterion in its row holds. It is a property of the
item, assigned at generation, and it never changes because a system found the item
hard (charter 4.1.1).

---

## Uses

**What has the dataset been used for?**

Nothing yet, beyond producing the reference-policy arithmetic in
`results/exception-economics-v1.0/`. No system has been scored on it.

**What is it suitable for?**

Comparing decision policies and confidence thresholds on the same labelled items under
one published labour model; showing how automation rate, rework and reviewer time
trade against each other; testing whether a supplier's reported figures reconcile with
the charter's denominators.

**What is it not suitable for?**

- Estimating a partner's own cost. The minutes are modelling assumptions and the money
  is a placeholder. Substituting a partner's own figures is the intended use; quoting
  ours is not.
- Measuring extraction, transcription, or anything about how a document or a
  conversation is read. That is Messy Scan and Honest Containment.
- Predicting how a system will behave on a partner's own queue. The mixes here are
  ours. Charter 9.1 is explicit that reweighting towards a partner's mix is still not
  the same as testing on their material.
- Producing a figure about a vendor. No vendor has been run.

---

## Distribution and licence

Data under CC BY 4.0. Code under MIT. Both licences sit in the public repository at
`nagu-io/benchmarks` and in this folder's parent, per charter 6.6.

The private split is never published. The public sample is published as a release
archive.

---

## Maintenance

Maintained by the benchmark owner named in `charter/methodology.md`. Contact
`hello@entailmentlabs.com`.

Versioning follows charter section 7. A ground-truth correction is always a major
dataset version, because it changes scores by construction. Superseded results stay
published and marked superseded, with a changelog entry saying what changed.

Where a generated company or person name collides with a real entity, the route is
`hello@entailmentlabs.com`. The item is removed in the next dataset version and the
removal is recorded, without argument about likelihood (charter 6.4).

---

## Known biases and limitations

**1. The labour model is the result.** Every money figure this suite produces is the
labour model's minutes multiplied by a placeholder rate. Change the minutes and the
ranking of two thresholds can change with them. The minutes are modelling assumptions,
each with its reasoning stated, and not one of them was measured. A partner who
substitutes measured times should expect a different answer, and that is the intended
use of the file.

**2. The reference decision policy is synthetic.** Its accuracy by tier, its confidence
distribution and its overconfidence on unseen categories are parameters chosen so that
the threshold trade-off is visible. A real system's calibration decides where its own
cost minimum sits, and no real system has been measured here.

**3. The mixes are ours.** The work-type mix, the tier mix, the error-class mix and the
share of items rejected before processing are design decisions. A headline figure over
a mix is partly a statement about the mix, which is why every table carries the mix
and every result is broken out by tier.

**4. Items are independent.** No repeat contact, no threading, no shared customer, no
queue ageing and no reviewer fatigue. A real back office has all five, and all five
move reviewer minutes.

**5. Three error classes are uncosted on purpose.** The open exposure count is the
honest form of a risk with no detection route, and it is not a small share of the real
cost of being wrong. A reader who compares net cost per item across thresholds is
comparing the priced part only. The count sits beside it for that reason.

**6. One rate, three work types.** The scorer applies one confidence threshold across
a mixed queue. Splitting the threshold by work type would change every figure in the
report, and doing so is a legitimate design a partner may prefer.

**7. The drift simulation is a simulation.** It shifts the input and holds the policy
fixed, so it measures sensitivity to input change and nothing else. Frozen-set drift
is zero in it by construction. That zero says nothing about whether a real system
would stay stable across ninety days.

**8. English only, and one document culture.** The identifiers, tax shapes and
reconciliation conventions lean towards Indian and generic Western formats. A partner
working in other jurisdictions will find the tolerance rules and the key availability
patterns unfamiliar.

**9. Three runs do not apply here.** Charter 3.1.4 requires three runs per system.
This scorer is deterministic, so its output does not vary between runs on the same
input. The three-run rule takes effect when a real system's predictions are scored,
and the three prediction files are then the three runs.
