#!/usr/bin/env python3
"""Validate the Honest Containment dataset.

    python3 validate.py               # exits non-zero if anything is wrong
    python3 validate.py --strict-audio  # also fail when the audio has not been rendered

Fourteen checks. Each prints its own line, its own count and its own verdict. The point of
this file is that a reader does not have to trust the datasheet: every claim the datasheet
makes about the set is checked here from the files themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import wave
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import intents as intent_catalogue
import policies
from generate import TIER_SPEC, TIER_PLAN_PER_DOMAIN, OUT_OF_SCOPE

BANNED = re.compile(r"seamless|revolutioni|cutting-edge|unlock|empower|leverag|journey|"
                    r"supercharg", re.I)

failures: list[str] = []
checks = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global checks
    checks += 1
    mark = "pass" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(f"{name}: {detail}")


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict-audio", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    public = [json.loads(l) for l in (HERE / "scenarios.jsonl").open(encoding="utf-8")
              if l.strip()]
    private_path = HERE / "private" / "scenarios.jsonl"
    private = ([json.loads(l) for l in private_path.open(encoding="utf-8") if l.strip()]
               if private_path.exists() else [])

    # 1. counts
    check("300 public scenarios", len(public) == 300, f"found {len(public)}")
    check("60 private scenarios", len(private) == 60, f"found {len(private)}")
    check("300 transcripts", len(list((HERE / "transcripts").glob("*.md"))) == 300)
    specs = [json.loads(l) for l in (HERE / "audio-specs.jsonl").open(encoding="utf-8")
             if l.strip()]
    check("120 audio specifications", len(specs) == 120, f"found {len(specs)}")

    # 2. unique ids, and a transcript for each
    ids = [s["id"] for s in public]
    check("scenario ids are unique", len(set(ids)) == len(ids))
    missing = [i for i in ids if not (HERE / "transcripts" / f"{i}.md").exists()]
    check("every scenario has a transcript", not missing, f"{len(missing)} missing")

    # 3. tier mix matches the plan
    per_domain = Counter((s["domain"], s["tier"]) for s in public)
    bad = [f"{d}/{t}" for d in policies.DOMAINS for t, n in TIER_PLAN_PER_DOMAIN.items()
           if per_domain[(d, t)] != n]
    check("tier plan holds in every domain", not bad, ", ".join(bad))

    # 4. every scenario obeys its tier specification, charter 4.3
    bad = []
    for s in public:
        spec = TIER_SPEC[s["tier"]]
        tier_traps = [t for t in s["traps"]
                      if t["type"] not in ("angry_customer", "prompt_injection")]
        if s["channel"] != spec["channel"]:
            bad.append(f"{s['id']} channel")
        if s["noise_level"] != spec["noise_level"]:
            bad.append(f"{s['id']} noise")
        if s["language"]["mode"] != spec["language_mode"]:
            bad.append(f"{s['id']} language mode")
        if s["identity"]["condition"] != spec["identity"]:
            bad.append(f"{s['id']} identity")
        if spec["tier_setting_traps"] == 0 and tier_traps:
            bad.append(f"{s['id']} has traps at a trap-free tier")
        if spec["tier_setting_traps"] and len(tier_traps) < spec["tier_setting_traps"]:
            bad.append(f"{s['id']} too few tier traps")
        wants_two = spec["intents"] >= 2
        if wants_two != (s["secondary_intent"] is not None):
            bad.append(f"{s['id']} intent count")
        if s["tier"] == "T5" and not s["superseded_in_pack"]:
            bad.append(f"{s['id']} tier 5 without a superseded document")
        if s["tier"] == "T5" and s["contact_in_scope"]:
            bad.append(f"{s['id']} tier 5 with no out-of-scope intent")
    check("every scenario matches its tier specification", not bad,
          f"{len(bad)} problems: {', '.join(bad[:5])}")

    # 5. all four trap families present
    trap_counts = Counter(t["type"] for s in public for t in s["traps"])
    needed = {"out_of_policy_request", "out_of_policy_request_pressed_twice",
              "explicit_request_for_person", "distress_cue", "angry_customer"}
    check("every trap family appears", needed <= set(trap_counts),
          f"present: {sorted(trap_counts)}")
    check("ambiguous identity appears",
          sum(1 for s in public if not s["identity"]["verifiable"]) > 0,
          f"{sum(1 for s in public if not s['identity']['verifiable'])} scenarios")

    # 6. policy documents exist and the value index matches the prose
    drift = []
    for row in policies.value_index():
        doc = policies.document_by_id(row["domain"], row["document"])
        body = doc["body"]
        value = row["value"]
        forms = {str(value), f"{value:,}"} if isinstance(value, int) else {str(value)}
        if not any(f in body for f in forms):
            drift.append(f"{row['document']}/{row['key']} value not in the document")
        words = [w for w in re.findall(r"[a-z]{4,}", row["fragment"].lower())]
        overlap = sum(1 for w in set(words) if w in body.lower())
        if overlap < 2:
            drift.append(f"{row['document']}/{row['key']} description does not match")
    check("every indexed value is carried by the document it names", not drift,
          ", ".join(drift[:5]))
    missing_docs = [f"{s['domain']}/{d}" for s in public
                    for d in s["policy_pack"] + s["superseded_in_pack"]
                    if not (HERE / "policies" / s["domain"] / f"{d}.md").exists()]
    check("every policy pack resolves to files on disk", not missing_docs,
          ", ".join(sorted(set(missing_docs))[:5]))

    # 7. escalation ground truth is internally consistent
    bad = []
    for s in public:
        gt = s["ground_truth"]
        if not gt["escalation_required"]:
            if gt["escalation"] is not None:
                bad.append(f"{s['id']} escalation block without a requirement")
            continue
        e = gt["escalation"]
        turn_indexes = {t["index"] for t in s["hidden_script"]["turns"]}
        if e["trigger_turn"] not in turn_indexes:
            bad.append(f"{s['id']} trigger turn not in the script")
        if not e["destination"] or not e["acceptable_destinations"]:
            bad.append(f"{s['id']} escalation with no destination")
        if len(e["context_fields"]) != 6:
            bad.append(f"{s['id']} escalation context fields")
        if e["primary_trigger"] != e["trigger_sequence"][0]["trigger"]:
            bad.append(f"{s['id']} primary trigger is not the earliest")
    check("escalation ground truth is consistent", not bad,
          f"{len(bad)}: {', '.join(bad[:5])}")

    # 8. must_quote agrees with the value index
    index = {(r["domain"], r["key"]): r for r in policies.value_index()}
    bad = [f"{s['id']}/{q['key']}" for s in public for q in s["ground_truth"]["must_quote"]
           if index.get((s["domain"], q["key"]), {}).get("value") != q["value"]]
    check("quoted values agree with the value index", not bad, ", ".join(bad[:5]))

    # 9. identifiers are checksum-invalid, charter 6.3
    blob = (HERE / "scenarios.jsonl").read_text(encoding="utf-8")
    valid = [d for d in re.findall(r"\d{12,19}", blob) if luhn_ok(d)]
    check("no checksum-valid identifier anywhere in the set", not valid,
          f"{len(valid)} found")
    phones = re.findall(r"\+91[\s-]?\d{10}|\+63[\s-]?\d{10}", blob)
    check("no full mobile number in the set", not phones, f"{len(phones)} found")

    # 10. no self-harm cue is generated, as the datasheet states
    selfharm = re.compile(r"kill myself|end my life|harm myself|suicid", re.I)
    hits = [s["id"] for s in public
            if any(selfharm.search(t["text"] + " " + t.get("native_text", ""))
                   for t in s["hidden_script"]["turns"])]
    check("no scripted caller turn expresses self-harm", not hits, ", ".join(hits[:5]))

    # 11. banned words, BRIEF.md section 5
    hits = []
    for path in list(HERE.rglob("*.md")) + list(HERE.rglob("*.py")) + \
            list(HERE.rglob("*.json")) + list(HERE.rglob("*.jsonl")):
        if "audio" in path.parts or path.name == "validate.py":
            continue
        for m in BANNED.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(f"{path.relative_to(HERE)}:{m.group(0)}")
    check("no banned word in the dataset", not hits, ", ".join(hits[:5]))

    # 12. no exclamation mark in the prose we wrote
    hits = [str(p.relative_to(HERE)) for p in HERE.rglob("*.md")
            if "!" in p.read_text(encoding="utf-8", errors="ignore")]
    check("no exclamation mark in any markdown file", not hits, ", ".join(hits[:5]))

    # 13. manifest counts reconcile with the files
    ok = (manifest["counts"]["scenarios_public"] == len(public)
          and manifest["counts"]["audio_selected"] == len(specs)
          and manifest["mix"]["escalation_required"]
          == sum(1 for s in public if s["ground_truth"]["escalation_required"]))
    check("manifest reconciles with the files", ok)

    # 14. audio
    manifest_audio = HERE / "audio-manifest.jsonl"
    if manifest_audio.exists():
        rows = [json.loads(l) for l in manifest_audio.open(encoding="utf-8") if l.strip()]
        expected_turns = sum(len(s["turns"]) for s in specs)
        check("an audio file for every specified caller turn",
              len(rows) == expected_turns, f"{len(rows)} of {expected_turns}")
        silent, drift, missing_files = [], [], []
        for r in rows:
            path = HERE / r["path"]
            if not path.exists():
                missing_files.append(r["path"])
                continue
            with wave.open(str(path)) as w:
                if w.getnframes() < w.getframerate() * 0.3:
                    silent.append(r["path"])
            if r["measured_snr_db"] is not None and r["target_snr_db"] is not None:
                if abs(r["measured_snr_db"] - r["target_snr_db"]) > 1.5:
                    drift.append(r["path"])
        check("no audio file is missing", not missing_files, f"{len(missing_files)}")
        check("no audio file is silent or near-silent", not silent, f"{len(silent)}")
        check("measured signal-to-noise ratio within 1.5 dB of the target", not drift,
              f"{len(drift)} outside")
    else:
        check("audio rendered", not args.strict_audio,
              "audio-manifest.jsonl not found; run `python3 tts.py`. The audio is "
              "regenerated from the seed and is not committed.")

    print("")
    print(f"{checks - len(failures)} of {checks} checks passed")
    if failures:
        print("failed:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
