# The CI workflow, and why it is in this folder

`ci/github-workflow-ci.yml` is the continuous-integration workflow for this repository. It
belongs at `.github/workflows/ci.yml`, and it is not there yet.

The reason is mechanical. This repository was populated through the GitHub API by an
integration whose token does not carry the `workflows` permission, so every attempt to write
under `.github/workflows/` is refused with a 403. That is a sensible restriction — a token
that can add a workflow can run code in your CI — and the right answer is for a person to
install it rather than for the integration to be given the scope.

## Installing it

```bash
git clone https://github.com/nagu-io/benchmarks
cd benchmarks
mkdir -p .github/workflows
git mv ci/github-workflow-ci.yml .github/workflows/ci.yml
git rm ci/README.md
git commit -m "Install the CI workflow"
git push
```

Or paste the file into the GitHub web editor at `.github/workflows/ci.yml` and delete this
folder.

## What it checks

Five jobs, and none of them touches the network after the install step:

| Job | What it proves |
|---|---|
| `harness` | The harness installs and its tests pass on Python 3.11 and 3.12 with egress blocked and no interface key set. The block is verified, not assumed: the job fails if an outbound connection still succeeds. |
| `datasets` | Regenerating a dataset from its seed reproduces the committed ground truth byte for byte, and every identifier still fails its real check digits. |
| `results` | Every markdown table in the Exception Economics results folder is rebuilt from its JSON. A figure edited by hand fails the build. |
| `no-estimated-figures` | No results file carries a hedged figure, a `not run` without a reason, or filler text. This is charter 3.1.8 made executable. |
| `lint` | The required files exist, the citation file and issue templates parse, and nothing key-shaped or internal is committed. |

The first job is the one worth understanding. A BPO engineer has to be able to run this
harness inside a locked network before trusting a number from it, and a test that quietly
reached a provider would hide a dependency on one. So the workflow blocks egress and then
checks that egress is really blocked before running anything.
