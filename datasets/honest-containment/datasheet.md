# Datasheet — Honest Containment dataset v1.0.0

Follows the structure of Gebru et al., "Datasheets for Datasets" (2018).
Dataset version 1.0.0 · Schema version 1.0 · Seed 20260902 · Written 2026-09-02.

**This data is synthetic.** Every scenario, policy document, caller script and audio file
in this folder was produced by `generate.py` and `tts.py`. No transcript of a real contact
was used. No recording of a real person was used. The four companies do not exist and the
policy documents were written for this benchmark. What that means for a reader of a result
is in "Known biases and limitations", and it is not a footnote: a score here tells you how
a system behaves on contacts that are shaped like production contacts, not how it behaves
on your production contacts.

---

## Motivation

**Why was the dataset created?**

Containment is the number most often quoted about a voice or chat agent and the number
least often defined. The same set of conversations produces very different containment
figures depending on which of four common definitions is used, and the definition is
usually left unstated. This dataset exists so the difference can be measured on fixed data
rather than argued about, and so that a BPO can put a definition into a statement of work.

The suite scores containment under all five definitions, false containment against each of
the four common ones, escalation recall, precision and quality, hallucinated-policy rate,
time to first token and turns to resolution. The definitions are in
`../../charter/methodology.md` sections 3.9 to 3.13 and they govern this dataset.

**Who created it and who funded it?**

Entailment Labs, for its own benchmark programme. No sponsorship, no paid placement, no
pre-agreed outcome. We sell voice and chat agents and our own system is scored by this
suite, in the same table, sorted on the metric. Charter sections 5 and 8.4 are the
discipline we accept in return, and section 9.10 states plainly that they do not remove our
interest in the outcome.

## Composition

**What do the instances represent?**

One instance is one contact: a customer with an intent, the policy pack the agent must work
from, the ground-truth resolution, a set of traps, and a hidden turn-by-turn caller script.

**How many instances are there?**

| Item | Count |
|---|---|
| Public scenarios | 300 |
| Private held-out scenarios | 60 |
| Reference transcripts | 300 |
| Policy documents | 38, of which 4 are superseded versions retained for tier 5 |
| Machine-readable policy values | 67 |
| Scenarios with audio | 120 |
| Rendered caller-turn audio files | 970, about 83 minutes |
| Human adjudication cases selected | 60, all unlabelled |

**What is in an instance?**

Intent class and statement; a second intent at tiers 3 and above; the policy pack by
document id; identity condition; ground truth as a resolution code, a resolution statement,
required actions, values the agent must state correctly, prohibited moves, and whether
escalation is required with its trigger, turn budget, destination and context fields; the
traps; the hidden caller script turn by turn with the language of each turn; the
false-containment cue; and the repeat-contact rule.

**Mixes**

| Dimension | Mix |
|---|---|
| Domain | telecom 75, banking 75, e-commerce 75, insurance 75 |
| Tier, charter 4.3 | T1 48, T2 96, T3 60, T4 56, T5 40 |
| Channel | text 48, voice 252 |
| Background noise level | 0 on 48, 1 on 96, 2 on 60, 3 on 96 |
| Language condition | Indian English 72, Filipino English 72, Hindi-English code-switched 80, Tagalog-English code-switched 76 |
| Escalation required | 172 of 300 |
| Either outcome acceptable, charter 3.11.4 | 6 |
| Contact carrying an out-of-scope intent | 40 |
| False-containment cue present | 96 |
| Prompt-injection scenarios | 22 |

**Trap counts**

`out_of_policy_request` 60, `out_of_policy_request_pressed_twice` 70,
`explicit_request_for_person` 74, `distress_cue` 72, `angry_customer` 74,
`contradictory_information` 40, `scripted_repeat_contact` 40, `prompt_injection` 22.

**Is there a label or target?**

Yes. Every scenario carries a ground-truth resolution and, where escalation is required,
the trigger, the turn budget, the accepted destinations and the context fields. Resolution
is judged by a judge model against that ground truth, with deterministic rule checks first.
Judge agreement with human labels is unmeasured; see "Uses".

**Is any information missing?**

Two things by design. There are no agent-side transcripts, because no system has been run.
And there is no audio for the caller turns of the 180 scenarios outside the audio selection;
`tts.py` renders any scenario on request.

**Does the data contain confidential or offensive content?**

No partner data, no client data, no scraped content. Some scripted caller turns express
distress: an inability to afford medicine, a recent bereavement, fear and confusion, and a
soft form of financial coercion. They are there because an agent that does not recognise
them is dangerous, and a benchmark that omits them cannot detect that.

One cue is deliberately absent from every generated caller turn. The published cue list in
each welfare policy includes an intention to self-harm, because a real cue list must. No
scenario in this set generates a caller utterance expressing it, and `validate.py` fails the
build if one appears. The reason is that we are not willing to mass-produce synthetic
self-harm speech and synthesise it into audio for a scoring exercise. The consequence is
that the highest-stakes cue on the list is not exercised by this dataset, and any result
from it is silent about that case. A partner who needs it tested should test it under
supervision on their own material, not here.

## Generation process

**How was the data collected?**

It was not collected. It was generated.

`policies.py` holds four invented companies with their policy corpora, written as
f-strings over a constants table so the prose and the machine-readable value cannot drift
apart. `intents.py` holds 60 intents, fifteen per domain, each tied to the documents that
decide it. `generate.py` assembles scenarios against the tier table in charter 4.3, builds
the hidden caller script beat by beat, and writes the transcripts, the manifest and the
audio specification. `tts.py` renders the audio.

**Was the data validated?**

`validate.py` runs 24 checks and exits non-zero on any failure: counts, tier conformance
per scenario, trap coverage, policy pack resolution, escalation-ground-truth consistency,
agreement between quoted values and the value index, absence of any checksum-valid
identifier, absence of full mobile numbers, absence of self-harm cues, banned words,
exclamation marks, manifest reconciliation, and, where the audio has been rendered, that no
file is missing or silent and that every measured signal-to-noise ratio is within 1.5 dB of
its target.

**Identifiers**

Account, order, policy and claim references are format-valid and carry no check digit.
`validate.py` scans every digit run of 12 to 19 characters and fails the build if any of
them passes the Luhn check. No full mobile number appears anywhere in the set; scripts refer
to the last four digits only. Charter section 6.3.

**Names and companies**

Generated from name pools. The companies are Orbanet Mobile, Vellora Bank, Broadleaf Retail
and Ashgrove Insurance, invented for this set. If a generated name collides with a real
entity, write to `hello@entailmentlabs.com`: we remove the item in the next dataset version
and record the removal in the changelog, without argument about likelihood. Charter 6.4.

**Adversarial content**

Twenty-two scenarios include a prompt-injection attempt inside the caller's words, labelled
`adversarial.prompt_injection`. Each is constructed against the synthetic policy packs in
this set and asks the agent to override an invented policy at an invented company. None of
them functions as an attack outside this benchmark. Charter 6.9.

## Audio

**How was it made?**

Text to speech only, charter 6.5. No recording of a real person, no voice cloning, no
synthetic voice presented as a specific individual. The engine is `espeak-ng` 1.51. The
noise beds are synthesised in `tts.py` with numpy: room tone from filtered pink noise and
mains hum, contact-centre babble summed from this set's own synthetic speech, street noise
from brown noise with vehicle passes and handset clicks. No third-party audio is used.

Every turn is band-limited to 300 to 3400 Hz and delivered at 8 kHz, 16-bit, mono, which is
the channel a voice agent receives.

**Noise levels**

| Level | Bed | Target signal-to-noise ratio | Measured, mean over the rendered set |
|---|---|---|---|
| 1 | quiet room | 25 dB | 25.00 dB, n=214 |
| 2 | contact centre | 15 dB | 15.00 dB, n=316 |
| 3 | street or market | 8 dB | 8.04 dB, n=440 |

The measured figures are measurements of the delivered files, taken over speech-active
frames identified on the noise-free turn. They are recorded per file in
`audio-manifest.jsonl`.

**What the audio is, and what it is not**

espeak-ng ships a Hindi voice, so the Hindi clauses of a Hindi-English turn are Hindi
speech. It ships no Indian English voice, no Filipino English voice and no Tagalog voice.
Those three conditions are rendered by the nearest available voice, and every manifest row
says so:

| Condition | Voice used | Fidelity |
|---|---|---|
| Hindi clauses | `hi` | native |
| Indian English | `en-gb`, slower and lower | approximated |
| Filipino English | `en-us` | approximated |
| Tagalog clauses | `id`, Indonesian | approximated |

The Indonesian voice shares a five-vowel system and a largely transparent Latin orthography
with Tagalog, which makes it the closest available approximation. It is not Tagalog speech.
All 970 rendered turns carry at least one approximated segment, because every turn contains
English.

**What is missing, and the command that produces it**

Native Indian English, Filipino English and Tagalog voices. `piper` is installed in the
build environment and its voice models are not: the model host is blocked by the sandbox's
egress proxy, which answers 403 to `CONNECT huggingface.co:443`. On a machine with access:

```bash
pip install piper-tts --break-system-packages
python3 -m piper.download_voices <voice-key>     # verify the key list against piper's docs
python3 tts.py --engine piper --voice-map piper-voices.json
```

`tts.py --check` prints this, and `render_segment_piper` raises rather than falling back to
espeak-ng, so no run can report an approximated voice as a native one.

**The language and noise cross is not full**

Charter 4.3 ties the noise level to the tier and the language mode to the tier: tier 2 is
one accented language at noise level 1, tiers 3 to 5 are code-switched at levels 2 and 3.
The audio therefore covers all four language conditions and all three noise levels, but not
every combination of them. The realised cross is: noise level 1 is Indian English 20 and
Filipino English 20; level 2 is Hindi-English 20 and Tagalog-English 20; level 3 is
Hindi-English 20 and Tagalog-English 20.

## Uses

**What is it for?**

Measuring what a voice or chat agent does with a policy pack, a caller who does not
cooperate, and a definition of success that is written down. Specifically: the spread
between containment definitions on identical contacts.

**What has it been used for so far?**

Nothing. No system has been run against it. Every results row in
`../../results/honest-containment-v1.0/` reads `not run` with its reason.

**Judge agreement is unmeasured**

Resolution and some policy-assertion decisions are made by a judge model. Charter 5.9
requires judge agreement with human labels, reported as Cohen's kappa, and requires a caveat
on every table that depends on the judge where agreement is below 0.8. The 60-case
adjudication set is selected, the labelling guide is written and the kappa computation runs
the moment labels exist. Until two people have labelled those 60 cases against transcripts
from a real run, judge agreement is unmeasured, not assumed, and every containment, false
containment and hallucinated-policy figure this suite produces carries that caveat.

**What should it not be used for?**

- Predicting a system's containment on your traffic. See "Known biases".
- Comparing a run of this suite against any figure produced by another method or another
  definition.
- Measuring speech recognition, voice quality, telephony reliability, barge-in behaviour or
  latency of a telephony carrier. The audio is synthetic speech in a synthetic noise bed and
  the runner sends turns, not a live call.
- Testing an agent's handling of a caller expressing an intention to self-harm. That cue is
  not generated here.
- Training. The set is small, its language is generated, and a system trained on it will
  score well here and tell you nothing.

## Known biases and limitations

1. **The escalation base rate is a design choice, not a traffic mix.** 172 of 300 contacts
   require a person under the ground truth, because charter 4.3 puts an out-of-policy
   request at tier 3 and an unverifiable identity at tiers 4 and 5. Real traffic escalates
   far less often. This inflates the visible difference between systems on escalation
   recall and compresses the containment ceiling. The per-tier tables exist so a reader can
   reweight, and reweighting is still not the same as testing on your own material.
2. **The language mix is ours.** Two Indian and two Philippine conditions, no others. A
   system tuned to those varieties will do better here than on a set drawn from elsewhere.
3. **The accents are approximated.** See "Audio". A system whose speech recognition is tuned
   to real Indian or Filipino English is not being tested on it here.
4. **The policy packs are short and internally consistent.** Real policy packs contradict
   themselves, run to hundreds of pages, and are out of date. One superseded document per
   tier-5 pack is a small gesture at that, not a model of it.
5. **The caller is a model or a script, not a person.** A simulated caller is more
   consistent, more patient and more literal than a real one. Both modes are recorded in the
   run header and they are not comparable to each other.
6. **The repeat-contact rule is scripted.** Whether a caller comes back is decided by the
   scenario, not observed. 61 contacts have a caller who comes back whatever the agent did,
   50 have a caller who never comes back, and 189 have a caller who comes back only if the
   outcome was not reached. Those proportions are a design choice and they move every
   containment figure that has a repeat-contact condition, ours included.
7. **Anger is scripted only at tier 3 and above**, so that tiers 1 and 2 stay trap-free as
   charter 4.3 requires. A dataset that spread anger evenly would test it better and would
   break the tier definitions.
8. **The deterministic policy check misses assertions without numbers**, and marks a correct
   figure unsupported where it comes from a document not in the pack. The judge pass covers
   the first; the second is the behaviour we want, and both are described in
   `suite/policy_check.py`.
9. **One currency, two caller locales.** All four companies are registered in India and
   price in rupees, so every amount in every policy pack and every script is in rupees,
   while callers in the Filipino English and Tagalog-English conditions use Philippine
   place names. That pairing is a simplification made to keep one value index behind the
   deterministic policy check, and it is stated here rather than left for a reader to
   notice.

## Distribution and maintenance

Published in `nagu-io/benchmarks` under CC BY 4.0 for the data and MIT for the code. The
private split in `private/` is never published and exists only to detect tuning against the
public set, charter 5.10.

Versioning follows charter section 7. A ground-truth correction is a major dataset version
and every affected table is re-run before it is published again. Superseded results stay
published, marked superseded, with a changelog entry.

Disputes: charter section 8.4, or `hello@entailmentlabs.com`.

Contact for a name collision, a ground-truth error or a removal request:
`hello@entailmentlabs.com`.
