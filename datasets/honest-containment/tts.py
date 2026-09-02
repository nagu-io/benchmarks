#!/usr/bin/env python3
"""Render the caller-side audio for the Honest Containment dataset.

    python3 tts.py --check        # what this environment can and cannot render
    python3 tts.py                # render every scenario in audio-specs.jsonl
    python3 tts.py --only hc-tel-0033 --keep-clean

Input   audio-specs.jsonl, written by generate.py
Output  audio/<scenario>/turn-NN.wav, one file per caller turn, and
        audio-manifest.jsonl, one row per file with the voice used, the measured
        signal-to-noise ratio and the sha256

What is real here and what is an approximation
----------------------------------------------
The speech is text-to-speech, as charter section 6.5 requires. No recording of a real
person is used and no voice is cloned.

espeak-ng ships a Hindi voice, so the Hindi segments of a code-switched turn are Hindi
speech. It ships no Indian English voice, no Filipino English voice and no Tagalog voice.
Those three conditions are therefore rendered by the nearest available voice with the
prosody settings recorded in VOICES below, and every manifest row carries
`accent_fidelity: approximated` and names the substitution. The scenario's accent label
is metadata about the caller the script describes; it is not a claim about the audio.
`--check` prints the substitutions and the command that replaces them with native voices.

The noise beds are synthesised here from numpy, not sampled from recordings, so the set
carries no third-party audio. Levels are set to a target signal-to-noise ratio and the
achieved ratio is measured on the delivered file and written to the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
TTS_SR = 22050          # espeak-ng output rate
OUT_SR = 8000           # telephony rate, the channel a voice agent receives
BAND = (300.0, 3400.0)  # telephony band

# Voice per language segment. "fidelity" is the honest label that reaches the manifest.
VOICES = {
    "en:indian_english": {
        "voice": "en-gb", "speed": 152, "pitch": 44, "amplitude": 105,
        "fidelity": "approximated",
        "substitution": "espeak-ng has no Indian English voice; en-gb is used at a lower "
                        "speed and pitch. The segment is not Indian English speech.",
    },
    "en:filipino_english": {
        "voice": "en-us", "speed": 158, "pitch": 54, "amplitude": 105,
        "fidelity": "approximated",
        "substitution": "espeak-ng has no Filipino English voice; en-us is used. The "
                        "segment is not Filipino English speech.",
    },
    "en:hindi_english": {
        "voice": "en-gb", "speed": 150, "pitch": 44, "amplitude": 105,
        "fidelity": "approximated",
        "substitution": "the English half of a Hindi-English turn is rendered with en-gb; "
                        "espeak-ng has no Indian English voice.",
    },
    "en:tagalog_english": {
        "voice": "en-us", "speed": 156, "pitch": 52, "amplitude": 105,
        "fidelity": "approximated",
        "substitution": "the English half of a Tagalog-English turn is rendered with "
                        "en-us; espeak-ng has no Filipino English voice.",
    },
    "hi:hindi_english": {
        "voice": "hi", "speed": 148, "pitch": 48, "amplitude": 105,
        "fidelity": "native",
        "substitution": "",
    },
    "tl:tagalog_english": {
        "voice": "id", "speed": 152, "pitch": 50, "amplitude": 105,
        "fidelity": "approximated",
        "substitution": "espeak-ng has no Tagalog voice; the Indonesian voice is used, "
                        "which shares a five-vowel system and a largely transparent Latin "
                        "orthography with Tagalog. The segment is not Tagalog speech.",
    },
}

EMOTION = {
    "neutral":    {"speed": 0,   "pitch": 0,  "gain_db": 0.0},
    "firm":       {"speed": -6,  "pitch": -4, "gain_db": 1.0},
    "angry":      {"speed": 14,  "pitch": 9,  "gain_db": 2.5},
    "distressed": {"speed": -14, "pitch": 5,  "gain_db": -1.5},
    "mixed":      {"speed": 0,   "pitch": 0,  "gain_db": 0.0},
}

# Filler used to build the contact-centre babble bed. Neutral service language, so that
# the bed carries no policy content that a scorer could accidentally match on.
BABBLE_TEXT = [
    "Thank you for holding, I am checking that for you now.",
    "Could you confirm the reference number one more time please.",
    "I have updated the note on the record and it is saved.",
    "The line is a little unclear, could you repeat the last part.",
    "That has gone through and you will get a message shortly.",
    "Let me look at the previous contact before I answer that.",
]
BABBLE_VOICES = ["en-gb", "en-us", "en-gb-x-rp", "en-029", "en-us-nyc", "en-gb-scotland"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def have_espeak() -> str | None:
    return shutil.which("espeak-ng")


def espeak_voices() -> set[str]:
    out = subprocess.run(["espeak-ng", "--voices"], capture_output=True, text=True).stdout
    names = set()
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) > 1:
            names.add(parts[1])
    return names


def render_segment(text: str, voice: str, speed: int, pitch: int, amplitude: int) -> np.ndarray:
    """One espeak-ng render, returned as float32 at TTS_SR in [-1, 1]."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)
    cmd = ["espeak-ng", "-v", voice, "-s", str(speed), "-p", str(max(0, min(99, pitch))),
           "-a", str(amplitude), "-w", str(path), text]
    subprocess.run(cmd, check=True, capture_output=True)
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1
        raw = w.readframes(w.getnframes())
        sr = w.getframerate()
    path.unlink(missing_ok=True)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if sr != TTS_SR:
        x = signal.resample_poly(x, TTS_SR, sr).astype(np.float32)
    return x


def telephony(x: np.ndarray, sr_in: int = TTS_SR) -> np.ndarray:
    """Band-limit to the telephony band and resample to 8 kHz."""
    sos = signal.butter(4, [BAND[0], BAND[1]], btype="bandpass", fs=sr_in, output="sos")
    y = signal.sosfilt(sos, x)
    g = np.gcd(int(sr_in), OUT_SR)
    return signal.resample_poly(y, OUT_SR // g, sr_in // g).astype(np.float32)


# --------------------------------------------------------------------------------
# Noise beds, synthesised
# --------------------------------------------------------------------------------


def pink(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.standard_normal(n).astype(np.float32)
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786], dtype=np.float32)
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400], dtype=np.float32)
    return signal.lfilter(b, a, white).astype(np.float32)


def bed_room_tone(n: int, rng: np.random.Generator) -> np.ndarray:
    """A quiet room: ventilation rumble, mains hum, nothing else."""
    y = pink(n, rng) * 0.6
    t = np.arange(n, dtype=np.float32) / OUT_SR
    for harm, amp in ((50.0, 0.25), (100.0, 0.12), (150.0, 0.05)):
        y += amp * np.sin(2 * np.pi * harm * t + rng.uniform(0, 6.28)).astype(np.float32)
    sos = signal.butter(2, 1200, btype="lowpass", fs=OUT_SR, output="sos")
    return signal.sosfilt(sos, y).astype(np.float32)


def bed_babble(n: int, rng: np.random.Generator, cache: dict) -> np.ndarray:
    """Contact-centre babble, summed from this set's own synthetic speech."""
    if "babble" not in cache:
        talkers = []
        for i, text in enumerate(BABBLE_TEXT):
            seg = render_segment(text, BABBLE_VOICES[i % len(BABBLE_VOICES)],
                                 150 + 7 * i, 40 + 6 * i, 100)
            talkers.append(telephony(seg))
        cache["babble"] = talkers
    talkers = cache["babble"]
    out = np.zeros(n, dtype=np.float32)
    for i, t in enumerate(talkers):
        rep = int(np.ceil((n + len(t)) / max(1, len(t))))
        stream = np.tile(t, rep)
        off = int(rng.integers(0, max(1, len(t))))
        out += stream[off:off + n] * float(rng.uniform(0.55, 1.0))
    sos = signal.butter(2, [250, 3200], btype="bandpass", fs=OUT_SR, output="sos")
    return signal.sosfilt(sos, out).astype(np.float32)


def bed_street(n: int, rng: np.random.Generator) -> np.ndarray:
    """Traffic and market noise, wind on the handset, occasional handset clicks."""
    brown = np.cumsum(rng.standard_normal(n).astype(np.float32)) / 60.0
    y = brown + pink(n, rng) * 0.8
    # vehicles passing: band-swept noise under a slow envelope
    for _ in range(max(1, n // (OUT_SR * 3))):
        start = int(rng.integers(0, max(1, n - OUT_SR)))
        length = int(rng.integers(OUT_SR // 2, OUT_SR * 2))
        length = min(length, n - start)
        if length <= 8:
            continue
        env = np.hanning(length).astype(np.float32) * float(rng.uniform(0.6, 1.4))
        band = signal.sosfilt(
            signal.butter(2, [float(rng.uniform(200, 500)), float(rng.uniform(900, 1800))],
                          btype="bandpass", fs=OUT_SR, output="sos"),
            rng.standard_normal(length).astype(np.float32))
        y[start:start + length] += band.astype(np.float32) * env
    # handset clicks
    for _ in range(max(1, n // (OUT_SR * 4))):
        pos = int(rng.integers(0, n - 40))
        y[pos:pos + 12] += rng.standard_normal(12).astype(np.float32) * 1.6
    sos = signal.butter(2, [150, 3400], btype="bandpass", fs=OUT_SR, output="sos")
    return signal.sosfilt(sos, y).astype(np.float32)


BEDS = {"room_tone": bed_room_tone, "babble": bed_babble, "street": bed_street}


def active_speech_power(x: np.ndarray, frame: int = 160) -> float:
    """Mean power over speech-active frames.

    A frame counts as active when its root-mean-square is above one hundredth of the
    loudest frame, which is 40 dB below peak. Measuring over active frames only keeps
    the ratio from drifting with the amount of silence in a turn.
    """
    n = (len(x) // frame) * frame
    if n == 0:
        return float(np.mean(x ** 2) + 1e-12)
    frames = x[:n].reshape(-1, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-20)
    active = frames[rms > (rms.max() / 100.0)]
    if active.size == 0:
        active = frames
    return float(np.mean(active ** 2) + 1e-12)


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, target_db: float) -> tuple[np.ndarray, float]:
    ps = active_speech_power(speech)
    pn = float(np.mean(noise ** 2) + 1e-12)
    gain = float(np.sqrt(ps / (pn * (10.0 ** (target_db / 10.0)))))
    mixed = speech + noise * gain
    peak = float(np.max(np.abs(mixed)))
    if peak > 0.97:
        mixed = mixed * (0.97 / peak)
    return mixed.astype(np.float32), gain


def active_mask(x: np.ndarray, frame: int = 160) -> np.ndarray:
    n = (len(x) // frame) * frame
    frames = x[:n].reshape(-1, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-20)
    return rms > (rms.max() / 100.0)


def measured_snr_db(mixed: np.ndarray, clean: np.ndarray, noise_scaled: np.ndarray,
                    frame: int = 160) -> float:
    """Measured on the delivered mix.

    The speech-active frames are taken from the noise-free turn, so that adding noise
    cannot change which frames count as speech. Speech power in those frames is the
    power of the delivered mix less the power of the noise bed at the level it was mixed
    at. Both are measured, neither is assumed.
    """
    n = (len(clean) // frame) * frame
    if n == 0:
        return float("nan")
    mask = active_mask(clean, frame)
    if not mask.any():
        return float("nan")
    mix_frames = mixed[:n].reshape(-1, frame)[mask]
    pn = float(np.mean(noise_scaled ** 2) + 1e-12)
    p_mix = float(np.mean(mix_frames ** 2))
    return float(10.0 * np.log10(max(p_mix - pn, 1e-12) / pn))


def write_wav(path: Path, x: np.ndarray) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(x, -1.0, 1.0)
    data = (pcm * 32767.0).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_SR)
        w.writeframes(data)
    return len(pcm) / OUT_SR


def check(spec_path: Path) -> int:
    exe = have_espeak()
    print("Honest Containment audio, environment check")
    print("")
    print(f"espeak-ng: {'found at ' + exe if exe else 'NOT FOUND'}")
    if not exe:
        print("  install: apt-get install -y espeak-ng")
        return 1
    voices = espeak_voices()
    need = sorted({v["voice"] for v in VOICES.values()} | set(BABBLE_VOICES))
    missing = [v for v in need if v not in voices]
    print(f"voices required: {', '.join(need)}")
    print(f"voices missing: {', '.join(missing) if missing else 'none'}")
    print("")
    print("Accent fidelity, per language condition:")
    for key, cfg in VOICES.items():
        print(f"  {key:26s} voice {cfg['voice']:6s} {cfg['fidelity']}")
        if cfg["substitution"]:
            print(f"      {cfg['substitution']}")
    print("")
    print("What this environment cannot produce, and the command that produces it:")
    print("  Native Indian English, Filipino English and Tagalog voices are not in")
    print("  espeak-ng. piper is installed here and its voice models are not: the model")
    print("  host is blocked by this sandbox's egress proxy, which answers 403 to")
    print("  CONNECT huggingface.co:443. On a machine with access:")
    print("      pip install piper-tts --break-system-packages")
    print("      python3 -m piper.download_voices <voice-key>   # verify the key list")
    print("      python3 tts.py --engine piper --voice-map piper-voices.json")
    print("  The piper engine hook is in render_segment_piper below. It raises until a")
    print("  voice map is supplied, so no run can silently fall back to espeak-ng and")
    print("  report the result as a native voice.")
    print("")
    if spec_path.exists():
        rows = [json.loads(l) for l in spec_path.open(encoding="utf-8")]
        turns = sum(len(r["turns"]) for r in rows)
        print(f"specification: {len(rows)} scenarios, {turns} caller turns to render")
    else:
        print(f"specification: {spec_path} not found, run generate.py first")
        return 1
    return 0


def render_segment_piper(text: str, voice_key: str) -> np.ndarray:
    raise NotImplementedError(
        "piper rendering needs a downloaded voice model. See tts.py --check for the "
        "command. This function is deliberately not given an espeak-ng fallback: a run "
        "must never report an approximated voice as a native one.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", help="render one scenario id")
    ap.add_argument("--keep-clean", action="store_true",
                    help="also write the noise-free turn as turn-NN.clean.wav")
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--engine", default="espeak-ng", choices=["espeak-ng", "piper"])
    ap.add_argument("--voice-map", help="json mapping of language condition to a piper "
                                        "voice key; required by --engine piper")
    args = ap.parse_args()

    spec_path = HERE / "audio-specs.jsonl"
    if args.check:
        raise SystemExit(check(spec_path))
    if args.engine == "piper":
        render_segment_piper("", args.voice_map or "")
    if not have_espeak():
        raise SystemExit("espeak-ng not found. Run `python3 tts.py --check`.")
    if not spec_path.exists():
        raise SystemExit("audio-specs.jsonl not found. Run generate.py first.")

    specs = [json.loads(l) for l in spec_path.open(encoding="utf-8")]
    if args.only:
        specs = [s for s in specs if s["scenario"] == args.only]
        if not specs:
            raise SystemExit(f"no specification for {args.only}")

    out_root = HERE / "audio"
    out_root.mkdir(exist_ok=True)
    cache: dict = {}
    rows = []
    for n, spec in enumerate(specs, start=1):
        sid = spec["scenario"]
        cond = spec["language_condition"]
        rng = np.random.default_rng(abs(hash((args.seed, sid))) % (2 ** 32))
        for turn in spec["turns"]:
            pieces = []
            voices_used = []
            for seg in turn["segments"]:
                key = f"{seg['language']}:{cond}"
                cfg = VOICES.get(key) or VOICES[f"en:{cond}"]
                emo = EMOTION.get(turn["emotion"], EMOTION["neutral"])
                audio = render_segment(seg["text"], cfg["voice"],
                                       cfg["speed"] + emo["speed"],
                                       cfg["pitch"] + emo["pitch"], cfg["amplitude"])
                audio = audio * float(10.0 ** (emo["gain_db"] / 20.0))
                pieces.append(audio)
                pieces.append(np.zeros(int(TTS_SR * 0.18), dtype=np.float32))
                voices_used.append({"language": seg["language"], "voice": cfg["voice"],
                                    "fidelity": cfg["fidelity"],
                                    "substitution": cfg["substitution"]})
            clean22 = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
            clean = telephony(clean22)
            peak = float(np.max(np.abs(clean)))
            if peak > 0:
                clean = clean * (0.72 / peak)

            bed_name = spec["noise_bed"]
            target = spec["target_snr_db"]
            path = out_root / sid / f"turn-{turn['index']:02d}.wav"
            if bed_name == "none" or target is None:
                mixed, gain, noise = clean, 0.0, np.zeros_like(clean)
                achieved = None
            else:
                maker = BEDS[bed_name]
                noise = (maker(len(clean), rng, cache) if bed_name == "babble"
                         else maker(len(clean), rng))
                mixed, gain = mix_at_snr(clean, noise, float(target))
                scale = float(np.max(np.abs(clean + noise * gain)))
                trim = (0.97 / scale) if scale > 0.97 else 1.0
                achieved = round(measured_snr_db(mixed, clean * trim, noise * gain * trim), 2)
            duration = write_wav(path, mixed)
            if args.keep_clean:
                write_wav(path.with_suffix(".clean.wav"), clean)
            rows.append({
                "scenario": sid,
                "turn": turn["index"],
                "path": str(path.relative_to(HERE)),
                "sample_rate_hz": OUT_SR,
                "duration_s": round(duration, 3),
                "language_condition": cond,
                "emotion": turn["emotion"],
                "voices": voices_used,
                "accent_fidelity": ("native" if all(v["fidelity"] == "native"
                                                    for v in voices_used) else "approximated"),
                "noise_level": spec["noise_level"],
                "noise_bed": bed_name,
                "target_snr_db": target,
                "measured_snr_db": achieved,
                "sha256": sha256_file(path),
                "synthetic": True,
                "engine": "espeak-ng",
            })
        if n % 20 == 0 or n == len(specs):
            print(f"{n}/{len(specs)} scenarios rendered")

    manifest = HERE / "audio-manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = sum(r["duration_s"] for r in rows)
    approx = sum(1 for r in rows if r["accent_fidelity"] == "approximated")
    print(f"files {len(rows)}, total audio {total/60:.1f} minutes")
    print(f"turns with at least one approximated voice: {approx} of {len(rows)}")
    if rows:
        by_level: dict[int, list[float]] = {}
        for r in rows:
            if r["measured_snr_db"] is not None:
                by_level.setdefault(r["noise_level"], []).append(r["measured_snr_db"])
        for lvl in sorted(by_level):
            v = by_level[lvl]
            print(f"noise level {lvl}: measured snr mean {sum(v)/len(v):.2f} dB, "
                  f"min {min(v):.2f}, max {max(v):.2f}, n={len(v)}")
    print(f"manifest {manifest}")


if __name__ == "__main__":
    main()
