#!/usr/bin/env python3
"""Simulated-customer runner for the Honest Containment benchmark.

    python3 runner.py --config config/agents.example.json --agent entailment-agent \
        --run-index 1 --out ../../../results/honest-containment-v1.0/runs

One contact per scenario. A simulated caller follows the hidden script, the system under
test answers, and the runner records everything the scorer needs and nothing it does not.

The system under test never receives: the hidden script, the ground truth, the traps, the
tier, the repeat-contact rule, or this file's knowledge of what the caller will say next.

If any preflight fails, the run stops before the first contact and writes a `not run`
record carrying the reason. It never writes a partial table, and it never writes a number
it did not measure (charter 3.1.8, 5.8).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapters
import judge as judge_mod
from customer import build_customer
from model_client import ModelClient, ModelSpec, NotConfigured

SUITE = Path(__file__).resolve().parent
DATASET = SUITE.parent
HARNESS_VERSION = "1.0.0"
DEFAULT_TURN_CAP = 24


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(DATASET),
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def load_scenarios(path: Path, only: list[str] | None, limit: int | None) -> list[dict]:
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    if only:
        rows = [r for r in rows if r["id"] in set(only)]
    if limit:
        rows = rows[:limit]
    return rows


def audio_for(scenario: dict, turn_index: int) -> str | None:
    path = DATASET / "audio" / scenario["id"] / f"turn-{turn_index:02d}.wav"
    return str(path) if path.exists() else None


def run_contact(adapter, scenario: dict, customer_mode: str,
                customer_client: ModelClient | None, turn_cap: int) -> dict:
    customer = build_customer(scenario, customer_mode, customer_client)
    handle = adapter.start_contact(scenario)
    turns: list[dict] = []
    agent_index = 0
    caller_index = 0
    transfer_turn = None
    customer_model_version = ""

    greeting = adapter.greet(handle)
    if greeting is not None:
        agent_index += 1
        turns.append({"index": len(turns) + 1, "role": "agent", "agent_turn": agent_index,
                      "is_greeting": True, "text": greeting.text,
                      "first_token_ms": greeting.first_token_ms,
                      "substantive_first_token_ms": greeting.substantive_first_token_ms,
                      "total_ms": greeting.total_ms, "tool_calls": greeting.tool_calls,
                      "escalation": greeting.escalation, "disposition": greeting.disposition,
                      "model_version": greeting.model_version})

    ended_by = "runner_turn_cap"
    outcome_reached = False
    while len(turns) < turn_cap:
        caller = customer.next_turn([t for t in turns], outcome_reached)
        if caller is None:
            ended_by = "caller"
            break
        caller_index += 1
        customer_model_version = caller.get("customer_model_version", customer_model_version)
        turns.append({"index": len(turns) + 1, "role": "caller",
                      "script_turn": caller["script_turn"], "purpose": caller["purpose"],
                      "text": caller["text"], "emotion": caller["emotion"],
                      "cue": caller["cue"]})
        if caller["ends_contact"] and caller["purpose"] == "callback_cue":
            ended_by = "caller_said_will_call_back"
            break

        reply = adapter.send(handle, caller["text"],
                             audio_for(scenario, caller["script_turn"]))
        agent_index += 1
        turns.append({"index": len(turns) + 1, "role": "agent", "agent_turn": agent_index,
                      "is_greeting": False, "text": reply.text,
                      "first_token_ms": reply.first_token_ms,
                      "substantive_first_token_ms": reply.substantive_first_token_ms,
                      "total_ms": reply.total_ms, "tool_calls": reply.tool_calls,
                      "filler_before_answer": reply.filler_before_answer,
                      "escalation": reply.escalation, "disposition": reply.disposition,
                      "model_version": reply.model_version, "error": reply.error})
        if reply.escalation and transfer_turn is None:
            transfer_turn = caller["script_turn"]
            ended_by = "transfer"
            break
        if reply.disposition in ("resolved", "caller_ended"):
            outcome_reached = reply.disposition == "resolved"
            ended_by = "agent"
            break
        if caller["ends_contact"]:
            ended_by = "caller"
            break

    end = adapter.end(handle)
    return {
        "scenario": scenario["id"],
        "domain": scenario["domain"],
        "tier": scenario["tier"],
        "channel": scenario["channel"],
        "turns": turns,
        "end": {
            "ended_by": ended_by if end.ended_by == "agent" else end.ended_by,
            "transfer_to_human": end.transfer_to_human,
            "human_joined": end.human_joined,
            "callback_booked": end.callback_booked,
            "post_contact_human_work": end.post_contact_human_work,
            "agent_disposition": end.agent_disposition,
        },
        "escalation_turn": transfer_turn,
        "customer_mode": customer_mode,
        "customer_model_version": customer_model_version,
        "connected": True,
        "status": "completed",
    }


def not_run_record(scenario: dict, reason: str, agent: str) -> dict:
    return {"scenario": scenario["id"], "domain": scenario["domain"], "tier": scenario["tier"],
            "channel": scenario["channel"], "agent": agent, "turns": [], "end": None,
            "connected": False, "status": "not_run", "not_run_reason": reason}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--agent", required=True, help="a system key in the config")
    ap.add_argument("--scenarios", default=str(DATASET / "scenarios.jsonl"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--run-index", type=int, default=1,
                    help="1, 2 or 3; charter 5.4 requires three runs at identical settings")
    ap.add_argument("--customer-mode", choices=["llm", "scripted"], default="llm")
    ap.add_argument("--turn-cap", type=int, default=DEFAULT_TURN_CAP)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="check every preflight and print what would run, calling nothing")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the loop with the scripted customer and no judge. The "
                         "run header is written publishable=false and the report generator "
                         "refuses it, because a self-test is not a measurement.")
    args = ap.parse_args()

    if args.self_test:
        args.customer_mode = "scripted"
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.agent not in config["agents"]:
        raise SystemExit(f"no system {args.agent!r} in {args.config}")
    agent_cfg = config["agents"][args.agent]
    scenarios = load_scenarios(Path(args.scenarios), args.only, args.limit)

    out_dir = Path(args.out) / args.agent / f"run-{args.run_index}"
    out_dir.mkdir(parents=True, exist_ok=True)

    header = {
        "suite": "honest-containment",
        "dataset_version": json.loads((DATASET / "manifest.json").read_text())["dataset_version"],
        "dataset_manifest_sha256": hashlib.sha256(
            (DATASET / "manifest.json").read_bytes()).hexdigest(),
        "harness_version": HARNESS_VERSION,
        "harness_commit": git_commit(),
        "prompt_hashes": judge_mod.prompt_hashes(),
        "agent": args.agent,
        "agent_display_name": agent_cfg.get("display_name", args.agent),
        "agent_kind": agent_cfg.get("adapter"),
        "run_index": args.run_index,
        "customer_mode": args.customer_mode,
        "judge_preflight": "skipped for a self test" if args.self_test else "required",
        "turn_cap": args.turn_cap,
        "started_at": now(),
        "scenarios": len(scenarios),
        "python": platform.python_version(),
        "price_list_date": config.get("price_list_date", "placeholder - record before a run"),
    }

    reasons: list[str] = []
    try:
        adapter = adapters.build(args.agent, agent_cfg)
        adapter.preflight()
    except NotConfigured as exc:
        adapter = None
        reasons.append(str(exc))

    customer_client = None
    if args.customer_mode == "llm":
        try:
            customer_client = ModelClient(ModelSpec.from_dict("customer", config["customer_model"]))
            customer_client.preflight()
        except (NotConfigured, KeyError) as exc:
            reasons.append(f"customer model: {exc}")

    judge_client = None
    try:
        if args.self_test:
            raise NotConfigured("self test: the judge is not called and no judged figure "
                                "is produced")
        judge_client = ModelClient(ModelSpec.from_dict("judge", config["judge_model"]))
        judge_client.preflight()
        if (agent_cfg.get("model") or {}).get("model") == config["judge_model"]["model"]:
            reasons.append("the judge model is the same as the model under test; charter 5.9 "
                           "requires a different judge")
    except (NotConfigured, KeyError) as exc:
        reasons.append(f"judge model: {exc}")

    if args.self_test:
        reasons = [r for r in reasons if not r.startswith("judge model: self test")]
    header["preflight_failures"] = reasons
    header["publishable"] = not args.self_test
    header["self_test"] = args.self_test

    if args.dry_run or reasons:
        status = "not_run"
        header["status"] = status
        header["not_run_reason"] = ("; ".join(reasons) if reasons
                                    else "dry run: nothing was called")
        header["ended_at"] = now()
        (out_dir / "run.json").write_text(json.dumps(header, indent=2), encoding="utf-8")
        with (out_dir / "contacts.jsonl").open("w", encoding="utf-8") as fh:
            for s in scenarios:
                fh.write(json.dumps(not_run_record(s, header["not_run_reason"], args.agent))
                         + "\n")
        print(f"status: not run\nreason: {header['not_run_reason']}")
        print(f"wrote {out_dir}/run.json and {len(scenarios)} not-run contact records")
        raise SystemExit(0 if args.dry_run else 3)

    started = time.perf_counter()
    with (out_dir / "contacts.jsonl").open("w", encoding="utf-8") as fh:
        for i, scenario in enumerate(scenarios, start=1):
            try:
                record = run_contact(adapter, scenario, args.customer_mode,
                                     customer_client, args.turn_cap)
                record["agent"] = args.agent
            except NotConfigured as exc:
                record = not_run_record(scenario, str(exc), args.agent)
            except Exception as exc:                       # a crash is a reported outcome
                record = {"scenario": scenario["id"], "domain": scenario["domain"],
                          "tier": scenario["tier"], "channel": scenario["channel"],
                          "agent": args.agent, "turns": [], "end": None, "connected": True,
                          "status": "failed", "failure_reason": f"{type(exc).__name__}: {exc}"}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            if i % 25 == 0:
                print(f"{i}/{len(scenarios)} contacts")

    header["status"] = "completed"
    header["ended_at"] = now()
    header["wall_clock_s"] = round(time.perf_counter() - started, 1)
    (out_dir / "run.json").write_text(json.dumps(header, indent=2), encoding="utf-8")
    print(f"wrote {out_dir}/contacts.jsonl")


if __name__ == "__main__":
    main()
