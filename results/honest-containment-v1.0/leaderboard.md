# Honest Containment leaderboard

Suite `honest-containment` · dataset version 1.0.0 · harness version 1.0.0 · built 2026-09-02

Every figure in this table is produced by a run. No run has happened, so every figure reads `not run` with its reason. Charter section 3.1.8 governs this file: a row with no run is never estimated, extrapolated, illustrated or filled with a plausible-looking figure.

The definitions behind every column are in `definitions-spread.md` and in `../../charter/methodology.md` sections 3.9 to 3.13. A rate is meaningless without its denominator, so each cell carries one once a run exists.

## Containment, five definitions

Sorted on containment under charter 3.9.1. Our own system sits where the sort puts it, charter 5.6.

| system | runs | containment, charter 3.9.1 | A no transfer | B no human handled | C self-service end state | D no repeat, 24 h | D no repeat, 72 h | A and D, no transfer and no repeat | spread |
|---|---|---|---|---|---|---|---|---|---|
| developer voice platform A | 0 | not run | not run | not run | not run | not run | not run | not run | not run |
| developer voice platform B | 0 | not run | not run | not run | not run | not run | not run | not run | not run |
| general model with the reference agent prompt | 0 | not run | not run | not run | not run | not run | not run | not run | not run |
| our agent | 0 | not run | not run | not run | not run | not run | not run | not run | not run |

`spread` is the distance between the highest of the four common definitions and ours, in percentage points, for the same contacts. It is the column this suite exists for.

### Why each row reads not run

| system | reason |
|---|---|
| developer voice platform A | voice-platform-a is not configured: base_url, docs_date, paths.create_session, paths.end_session, paths.send_turn, response_paths.agent_version, response_paths.disposition, response_paths.first_token_ms, response_paths.reply_text, response_paths.transfer, response_paths.transfer_destination, response_paths.transfer_fields still read placeholder. Fill them in from the platform's current API documentation and record the documentation date in the run config.; customer model: no interface key: environment variable HC_CUSTOMER_KEY is not set for the customer model placeholder - model version string; judge model: no interface key: environment variable HC_JUDGE_KEY is not set for the judge model placeholder - model version string, must differ from every model under test |
| developer voice platform B | voice-platform-b is not configured: base_url, docs_date, paths.create_session, paths.end_session, paths.send_turn, response_paths.agent_version, response_paths.disposition, response_paths.first_token_ms, response_paths.reply_text, response_paths.transfer, response_paths.transfer_destination, response_paths.transfer_fields still read placeholder. Fill them in from the platform's current API documentation and record the documentation date in the run config.; customer model: no interface key: environment variable HC_CUSTOMER_KEY is not set for the customer model placeholder - model version string; judge model: no interface key: environment variable HC_JUDGE_KEY is not set for the judge model placeholder - model version string, must differ from every model under test |
| general model with the reference agent prompt | no interface key: environment variable HC_GENERAL_LLM_KEY is not set for the agent model placeholder - model version string; customer model: no interface key: environment variable HC_CUSTOMER_KEY is not set for the customer model placeholder - model version string; judge model: no interface key: environment variable HC_JUDGE_KEY is not set for the judge model placeholder - model version string, must differ from every model under test |
| our agent | no interface key: environment variable HC_ENTAILMENT_KEY is not set for the agent model placeholder - model version string; customer model: no interface key: environment variable HC_CUSTOMER_KEY is not set for the customer model placeholder - model version string; judge model: no interface key: environment variable HC_JUDGE_KEY is not set for the judge model placeholder - model version string, must differ from every model under test |

## False containment, escalation, policy, latency

| system | false containment vs B | escalation recall | escalation precision | escalation quality | hallucinated policy | financial class | time to first token p50 ms | p95 ms | turns to resolution p50 |
|---|---|---|---|---|---|---|---|---|---|
| developer voice platform A | not run | not run | not run | not run | not run | not run | not run | not run | not run |
| developer voice platform B | not run | not run | not run | not run | not run | not run | not run | not run | not run |
| general model with the reference agent prompt | not run | not run | not run | not run | not run | not run | not run | not run | not run |
| our agent | not run | not run | not run | not run | not run | not run | not run | not run | not run |

## What is missing before this table carries figures

| Item | Who supplies it |
|---|---|
| An interface key per system under test, per the environment variables in `suite/config/agents.example.json` | a person |
| A spend cap set with each provider before the run | a person |
| The API base and response paths for each voice platform, from its current documentation, with the documentation date | a person |
| A decision on which model versions are in scope | a person |
| A judge model that is not one of the models under test, charter 5.9 | a person |
| 60 labelled adjudication cases, so that judge agreement can be reported | two labellers, following `datasets/honest-containment/labelling/labelling-guide.md` |

## Judge agreement

Unmeasured. The 60-case adjudication set is selected and the kappa computation is written, and neither can produce a figure until a run has produced transcripts and two people have labelled them. Charter section 5.9 requires the caveat on every table that depends on the judge, and it applies to every containment, false containment and hallucinated-policy figure this suite will publish.
