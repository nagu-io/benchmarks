# Test fixtures

Synthetic, hand-written, and not the output of any system. These files exist so the
scorer's arithmetic can be checked against fixed input. A fixture is never scored into a
leaderboard: the replay adapter writes `agent_kind: replay` and the report generator
refuses to publish a replay run.

`contacts.replay.jsonl` is one contact record shaped exactly as `runner.py` writes them,
with the agent turns written by hand to exercise a specific path through the scorer.
