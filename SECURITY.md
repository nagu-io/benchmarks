# Security

## Reporting a vulnerability

Write to **security@entailmentlabs.com**, or open a private security advisory through
GitHub's "Report a vulnerability" on this repository.

Do not open a public issue for a vulnerability.

Include: what you found, where, how to reproduce it, and what an attacker could do with it.
A proof of concept helps. If you would like a reply in a particular time frame, say so.

| Step | What happens |
|---|---|
| Acknowledgement | We reply confirming we have it, and tell you who is handling it |
| Assessment | We reproduce it, decide severity, and tell you what we found and what we plan to do |
| Fix | We fix it and tell you when it lands |
| Disclosure | We publish what happened, and credit you if you want to be credited |

We do not run a paid bug bounty. We will credit you by name or handle in the advisory and in
the changelog if you want that, and we will not credit you if you do not.

## Scope

**In scope**

- The harness (`harness/`): the CLI, the adapters, the scorer, the report writer. In
  particular anything that would cause it to leak a key it reads from the environment, write
  outside its output directory, or execute content from a dataset or a provider response.
- The dataset generators, validators, scorers and drift simulators under `datasets/`.
- The published site at bench.entailmentlabs.com.
- Anything in this repository that would let a contributor's pull request run code in our CI
  with access to a secret.

**Out of scope**

- The security posture of a model provider we call. Report that to the provider.
- Findings that require a key we do not have and would not have.
- Denial of service against GitHub or against the site's CDN.
- Automated scanner output with no demonstrated impact.

## What is deliberately not here

No API key, token, credential or private endpoint appears in this repository, and none is
stored in the harness. Every adapter reads its key from an environment variable it names in
`harness/src/entail_bench/data/models.yaml`, and the harness never writes one to a log, a
report, a run record or a chart.

If you find a key committed anywhere in the history, treat it as a vulnerability and tell us
at the address above. It is a mistake, not a test.

## Data in this repository

Everything is synthetic. Nothing was scraped, nothing was copied from a real document, and no
recording of a real person is here. Identifiers that resemble government or financial
identifiers — Aadhaar-style, PAN-style, card numbers, IBANs — are format-valid and
checksum-invalid by construction, so that nothing in a public set can resolve to a real person
or account. Each dataset's `validate.py` fails the build if a checksum-valid identifier
appears.

If you believe an item resolves to a real person, account or company, that is a privacy
report rather than a vulnerability. Write to hello@entailmentlabs.com. We remove the item in
the next dataset version and record the removal in the changelog, without an argument about
likelihood.

## Prompt-injection scenarios in the datasets

The Honest Containment set contains prompt-injection scenarios. They are constructed against
the synthetic policy packs in that set, they are labelled as adversarial in the ground truth,
and they are written so that they do not function as an attack outside the benchmark. If you
find one that does, tell us and we will replace it.

## Supported versions

The current release is supported. Older dataset and harness versions stay published so that a
past figure can still be reproduced, but a security fix is issued against the current version
only.
