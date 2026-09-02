# Contributing

Thank you for looking. This repository takes four kinds of contribution, and each one has a
different bar.

Read `charter/methodology.md` first. It is the document every suite follows, and most
questions about "why is it scored that way" are answered in it, usually in the exclusions.

## 1. Disputing a figure

The most valuable contribution. Open a **dispute a result** issue. It must name the table, the
row, the dataset and harness versions, and what is wrong. Two kinds are accepted:

- **A defect**: wrong ground truth, a harness bug, a wrong price, a wrong model version
  string, a misconfigured adapter.
- **A disagreement with a definition**: you think a denominator or an exclusion is wrong.

Both are published in the disputes log with their status and date, and both are answered in
public whichever way they go. A defect that is upheld corrects the table, bumps the version,
and leaves the original figure visible and marked superseded. A definition disagreement does
not change the definition for the current release; the objection is published beside the
definition and considered for the next major charter version.

There is one appeal per dispute, decided by the named benchmark owner and published either
way with its reasoning.

## 2. Adding a system to a leaderboard

Open an **add a model** issue. What we need:

- The system, and how it is reached: a provider interface, a self-hosted OpenAI-compatible
  endpoint, a document service, or an HTTP endpoint speaking the generic contract in
  `harness/src/entail_bench/adapters/http_endpoint.py`.
- Who pays for the interface cost of the run, and whether there is a rate limit that stops
  three runs over the full set.
- The model version string the provider reports, or how to obtain it.

If it speaks a shape the harness already knows, adding it is one row in
`harness/src/entail_bench/data/models.yaml` naming an adapter and the environment variables
it reads. A new provider shape is a subclass with `_build_request` and `_parse_response`;
splitting those two is what lets the contract tests drive it from a recorded fixture with no
network.

A vendor may fund the interface cost of running its own system. If it does, the report header
says so, and it changes nothing else: the vendor sees its rows only through the pre-publication
notice, at the same time as every other vendor. Notice is not approval, and no vendor can
delay, edit or veto a publication.

## 3. Code

Pull requests to the harness, the generators, the scorers and the validators are welcome.

- **Tests are the contribution.** A scorer change without a test that fails before it and
  passes after it will be asked for one. The existing tests run with no network and no key;
  yours must too. Adapter tests are driven by recorded fixtures in `harness/tests/fixtures/`,
  every one of which is synthetic and labelled as such.
- **Nothing in a test fixture may look like a result.** A fixture is not a measurement. If a
  reader could mistake a number in your fixture for a benchmark figure, change the number.
- **Run the suite before you open the pull request**: `pip install 'entail-bench[dev]' &&
  pytest`, and for a dataset change, the dataset's own `validate.py`.
- **Say what your change does to a published figure.** A change that cannot move any figure is
  a patch. A capability added without changing a score, such as a new adapter, is a minor
  version. A change to a scoring rule, a field-rules file or an alias table is a major version,
  because it can move a figure and every affected table has to be re-run before it is published
  again.

## 4. Data

Dataset changes are held to the strictest bar in this repository, because a ground-truth
correction changes scores by construction.

- Every dataset is generated from a seed and must stay deterministic. `validate.py` checks
  that regenerating from the seed reproduces the committed file byte for byte, and a change
  that breaks that is not accepted.
- Every generated identifier must remain format-valid and checksum-invalid. `validate.py`
  fails the build if a checksum-valid Aadhaar-style, PAN-style, card or IBAN identifier
  appears anywhere in a set.
- No real data. Nothing scraped, nothing copied from a real document, no recording of a real
  person, no voice cloned from an identifiable person, and no partner material of any kind.
- A ground-truth correction is a major dataset version. Say which items change and how many.
- If a generated name, address or company name collides with a real entity, write to
  hello@entailmentlabs.com. We remove the item in the next dataset version and record the
  removal in the changelog, without an argument about likelihood.

## What is out of scope

- Requests to remove a row, soften a reason, or replace a `not run` with an estimate.
- Marketing text of any kind, for us or anyone else.
- Weighting the tiers into a single difficulty score. A weighted score would let a supplier
  argue about the weights instead of about the tiers.
- Prompt engineering aimed at one system. The same prompt goes to every model, and there is no
  private prompt.

## Style

- Sentence case in headings. No exclamation marks.
- Every number carries its basis or its source. Where a real figure is needed and not yet
  known, write "placeholder" rather than a guess.
- Every metric states its unit, its numerator, its denominator and its exclusions. A metric
  quoted without its denominator is not a metric.
- British spelling in prose. Code and identifiers follow the language's conventions.

## Licence of contributions

Code you contribute is licensed MIT. Data you contribute is licensed CC BY 4.0. By opening a
pull request you confirm that you have the right to contribute the material under those terms
and that it contains no third party's confidential or personal data.
