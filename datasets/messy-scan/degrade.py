#!/usr/bin/env python3
"""Messy Scan dataset v1.0 — degradation stage and dataset assembly.

Reads the clean renders in ``build/render/`` and applies the tier degradation that
``generate.py`` planned for each document. Every parameter is taken from the plan,
so a run is reproducible from the seed alone and the ground truth can state exactly
what was done to each page.

Tiers
-----
T1  clean digital PDF. The vector PDF from Chromium is copied unchanged and the
    lossless page PNGs are copied unchanged. No raster degradation at all.

T2  flatbed scan. Greyscale, paper tone (a scanner never returns pure white),
    small skew, scanner-lid edge shadow, gaussian blur, gaussian noise, dust
    specks, brightness and contrast drift, JPEG compression.

T3  phone photo. Perspective warp from the four corner offsets, in-plane rotation,
    the page placed on a desk background with a margin, a directional shadow
    gradient, a radial glare highlight, white-balance channel gains, blur, sensor
    noise, JPEG compression.

T4  fax quality with marks. Rubber stamps drawn over the text, drawn signatures,
    margin annotations, staple holes and an optional corner tear, skew, a
    round trip through a low fax resolution, noise, then a one-bit conversion by
    Floyd-Steinberg dithering or a hard threshold, salt-and-pepper speckle and
    fax scan-line dropouts. Saved as a one-bit PNG.

T5  mixed multi-page bundle. The document's own pages plus a cover sheet in a
    second language, plus one duplicated page, optionally reordered; each page
    gets one of the tier 2, 3 or 4 base effects; pages are rotated by 0, 90, 180
    or 270 degrees; the whole bundle is downscaled to a phone-messaging long edge
    and JPEG-compressed twice.

Annotations are drawn, not photographed: signatures are parametric strokes and
margin notes use an oblique typeface with per-character jitter and rotation. They
are a simulation of handwriting, not samples of anyone's handwriting.

Outputs
-------
    documents/<doc_id>/document.pdf     final artefact, one PDF per document
    documents/<doc_id>/page-NN.<ext>    final artefact, one image per page
    ground-truth.jsonl                  one line per document, all 1,000
    sample/                             the 50-document public split
    private/                            the 200-document held-out split

Container per tier: T1 PNG, T2/T3/T5 JPEG, T4 one-bit PNG. The extension is
recorded per page in the ground truth, along with the SHA-256 of every file.

Usage
-----
    python3 degrade.py                       # every document that has been rendered
    python3 degrade.py --only msc-po-in-0001
    python3 degrade.py --skip-existing

Licence: MIT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import DEFAULT_PLAN_PATH, load_documents  # noqa: E402

HERE = Path(__file__).resolve().parent
RENDER_DIR = HERE / "build" / "render"
DOCS_DIR = HERE / "documents"
GROUND_TRUTH = HERE / "ground-truth.jsonl"
SAMPLE_DIR = HERE / "sample"
PRIVATE_DIR = HERE / "private"

FONT_STAMP = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_HAND = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"

PAGE_EXT = {1: "png", 2: "jpg", 3: "jpg", 4: "png", 5: "jpg"}


# --------------------------------------------------------------------------- #
# Utilities                                                                   #
# --------------------------------------------------------------------------- #

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_rng(doc_id: str, page_index: int) -> np.random.Generator:
    digest = hashlib.sha256(f"degrade:{doc_id}:{page_index}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def to_np(img: Image.Image) -> np.ndarray:
    return np.asarray(img).astype(np.float32)


def to_img(arr: np.ndarray, mode: str = "RGB") -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode)


def jpeg_roundtrip(img: Image.Image, quality: int) -> Image.Image:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, subsampling=2)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def add_noise(arr: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    return arr + rng.normal(0.0, sigma, arr.shape).astype(np.float32)


# --------------------------------------------------------------------------- #
# Drawn marks (tier 4)                                                        #
# --------------------------------------------------------------------------- #

def draw_stamp(base: Image.Image, spec: dict) -> None:
    w, h = base.size
    text = spec["text"]
    scale = spec["scale"]
    size = max(int(0.030 * w * scale), 12)
    font = ImageFont.truetype(FONT_STAMP, size)
    pad = int(size * 0.55)
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    box = dummy.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    sw, sh = tw + 2 * pad, th + 2 * pad
    layer = Image.new("RGBA", (sw + 8, sh + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = spec["ink"]
    alpha = int(255 * spec["alpha"])
    rgb = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5)) + (alpha,)
    lw = max(2, size // 9)
    if spec["shape"] == "rect":
        d.rectangle([2, 2, sw + 2, sh + 2], outline=rgb, width=lw)
    elif spec["shape"] == "ellipse":
        d.ellipse([2, 2, sw + 2, sh + 2], outline=rgb, width=lw)
    else:
        d.rectangle([2, 2, sw + 2, sh + 2], outline=rgb, width=lw)
        d.rectangle([2 + lw * 2, 2 + lw * 2, sw + 2 - lw * 2, sh + 2 - lw * 2],
                    outline=rgb, width=max(1, lw // 2))
    d.text((pad + 2 - box[0], pad + 2 - box[1]), text, font=font, fill=rgb)
    layer = layer.rotate(spec["rotation_deg"], expand=True, resample=Image.BICUBIC)
    cx, cy = int(spec["cx"] * w), int(spec["cy"] * h)
    base.alpha_composite(layer, (max(0, cx - layer.width // 2), max(0, cy - layer.height // 2)))


def signature_points(rng: np.random.Generator, n: int = 300) -> np.ndarray:
    """Parametric signature stroke.

    A low-frequency loop plus two higher harmonics, with the pen speeding up along
    the stroke and the amplitude decaying towards the end. That produces something
    that reads as a scrawled signature rather than a waveform.
    """
    t = np.linspace(0.0, 1.0, n)
    ease = t ** rng.uniform(0.75, 1.25)          # pen speed varies along the stroke
    a = np.array([1.0, rng.uniform(0.22, 0.48), rng.uniform(0.10, 0.26)])
    f = np.array([rng.uniform(0.7, 1.5), rng.uniform(1.8, 3.2), rng.uniform(3.4, 5.4)])
    ph = rng.uniform(0, 2 * math.pi, 3)
    envelope = 1.0 - 0.45 * t
    y = sum(a[i] * np.sin(f[i] * 2 * math.pi * ease + ph[i]) for i in range(3)) * envelope
    y = y / (np.max(np.abs(y)) + 1e-6)
    x = ease + 0.03 * np.sin(2 * math.pi * ease * rng.uniform(0.5, 1.4))
    x = (x - x.min()) / (x.max() - x.min() + 1e-6)
    return np.stack([x, y * 0.46 + 0.5], axis=1)


def draw_signature(base: Image.Image, spec: dict) -> None:
    w, h = base.size
    rng = np.random.default_rng(spec["stroke_seed"])
    pts = signature_points(rng)
    sw = int(0.20 * w * spec["scale"])
    sh = int(0.055 * h * spec["scale"])
    layer = Image.new("RGBA", (sw + 8, sh + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = spec["ink"]
    rgb = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5)) + (235,)
    xy = [(4 + p[0] * sw, 4 + p[1] * sh) for p in pts]
    for i in range(len(xy) - 1):
        width = max(1, int(3 + 2 * math.sin(i / 11.0)))
        d.line([xy[i], xy[i + 1]], fill=rgb, width=width, joint="curve")
    tail = int(sw * 0.7)
    d.line([(4 + sw * 0.15, sh), (4 + tail, sh * 0.92)], fill=rgb, width=2)
    layer = layer.rotate(spec["rotation_deg"], expand=True, resample=Image.BICUBIC)
    cx, cy = int(spec["cx"] * w), int(spec["cy"] * h)
    base.alpha_composite(layer, (max(0, cx - layer.width // 2), max(0, cy - layer.height // 2)))


def draw_handwriting(base: Image.Image, spec: dict) -> None:
    """Margin annotation. An oblique face with per-character jitter and rotation.
    This simulates handwriting; it is not a sample of anyone's hand."""
    w, h = base.size
    rng = np.random.default_rng(spec["stroke_seed"])
    size = max(int(spec["size_frac"] * h), 14)
    font = ImageFont.truetype(FONT_HAND, size)
    ink = spec["ink"]
    rgb = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5)) + (230,)
    text = spec["text"]
    layer = Image.new("RGBA", (int(size * 0.75 * len(text)) + size * 2, size * 3), (0, 0, 0, 0))
    x = size // 2
    for ch in text:
        glyph = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((size // 4, size // 4), ch, font=font, fill=rgb)
        glyph = glyph.rotate(float(rng.uniform(-9, 9)), resample=Image.BICUBIC)
        layer.alpha_composite(glyph, (x, size // 2 + int(rng.uniform(-size * 0.16, size * 0.16))))
        adv = font.getlength(ch)
        x += int(adv * rng.uniform(0.86, 1.06))
    layer = layer.crop((0, 0, min(x + size, layer.width), layer.height))
    layer = layer.rotate(spec["rotation_deg"], expand=True, resample=Image.BICUBIC)
    px, py = int(spec["x"] * w), int(spec["y"] * h)
    px = min(px, max(0, w - layer.width))
    py = min(py, max(0, h - layer.height))
    base.alpha_composite(layer, (px, py))


def draw_staple(base: Image.Image, spec: dict) -> None:
    w, h = base.size
    off = spec["offset_frac"]
    d = ImageDraw.Draw(base)
    r = max(3, int(0.004 * w))
    for i in range(spec["holes"]):
        if spec["corner"] == "tl":
            cx, cy = int(off * w) + i * r * 4, int(off * w) + i * r * 2
        else:
            cx, cy = w - int(off * w) - i * r * 4, int(off * w) + i * r * 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(35, 35, 38, 255))
        d.ellipse([cx - r * 2, cy - r * 2, cx + r * 2, cy + r * 2],
                  outline=(120, 120, 124, 160), width=1)
    if spec["tear"]:
        size = int(0.055 * w)
        if spec["corner"] == "tl":
            poly = [(0, 0), (size, 0), (0, int(size * 0.8))]
        else:
            poly = [(w, 0), (w - size, 0), (w, int(size * 0.8))]
        d.polygon(poly, fill=(255, 255, 255, 255))
        d.line(poly[1:] + [poly[0]], fill=(150, 150, 150, 255), width=2)


# --------------------------------------------------------------------------- #
# Tier operations                                                             #
# --------------------------------------------------------------------------- #

def op_flatbed(img: Image.Image, p: dict, rng: np.random.Generator) -> Image.Image:
    grey = img.convert("L")
    arr = to_np(grey)
    arr = arr * (p["paper_grey"] / 255.0)
    img2 = to_img(arr, "L")
    img2 = img2.rotate(p["skew_deg"], expand=False, resample=Image.BICUBIC,
                       fillcolor=p["paper_grey"])
    if p["lid_shadow_px"] > 0:
        arr = to_np(img2)
        band = p["lid_shadow_px"] * 6
        ramp = np.linspace(0.55, 1.0, band, dtype=np.float32)
        side = int(rng.integers(0, 4))
        if side == 0:
            arr[:, :band] *= ramp[None, :]
        elif side == 1:
            arr[:, -band:] *= ramp[::-1][None, :]
        elif side == 2:
            arr[:band, :] *= ramp[:, None]
        else:
            arr[-band:, :] *= ramp[::-1][:, None]
        img2 = to_img(arr, "L")
    img2 = img2.filter(ImageFilter.GaussianBlur(p["blur_sigma"]))
    arr = to_np(img2)
    arr = (arr - 128.0) * p["contrast"] + 128.0 * p["brightness"]
    arr = add_noise(arr, p["gaussian_noise_sigma"], rng)
    h, w = arr.shape
    for _ in range(p["dust_specks"]):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(1, 4))
        arr[max(0, y - r):y + r, max(0, x - r):x + r] *= float(rng.uniform(0.15, 0.6))
    out = to_img(arr, "L").convert("RGB")
    return jpeg_roundtrip(out, p["jpeg_quality"])


def op_phone(img: Image.Image, p: dict, rng: np.random.Generator) -> Image.Image:
    arr = np.asarray(img.convert("RGB"))
    h, w = arr.shape[:2]
    o = p["perspective_offsets_frac"]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([
        [o[0] * w, o[1] * h],
        [w - o[2] * w, o[3] * h],
        [w - o[4] * w, h - o[5] * h],
        [o[6] * w, h - o[7] * h],
    ])
    m = cv2.getPerspectiveTransform(src, dst)
    desk = np.array(p["desk_tone"], dtype=np.uint8)
    warped = cv2.warpPerspective(arr, m, (w, h), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=tuple(int(c) for c in desk))
    page = Image.fromarray(warped).rotate(p["rotation_deg"], expand=False,
                                          resample=Image.BICUBIC,
                                          fillcolor=tuple(int(c) for c in desk))
    margin = p["margin_frac"]
    fw, fh = int(w * (1 + 2 * margin)), int(h * (1 + 2 * margin))
    frame = Image.new("RGB", (fw, fh), tuple(int(c) for c in desk))
    frame_arr = to_np(frame)
    frame_arr = add_noise(frame_arr, 4.0, rng)
    frame = to_img(frame_arr)
    frame.paste(page, (int(w * margin), int(h * margin)))

    arr = to_np(frame)
    fh2, fw2 = arr.shape[:2]
    yy, xx = np.mgrid[0:fh2, 0:fw2].astype(np.float32)
    s = p["shadow"]
    if s["axis"] == "x":
        t = xx / fw2
    elif s["axis"] == "y":
        t = yy / fh2
    else:
        t = (xx / fw2 + yy / fh2) / 2.0
    grad = 1.0 - s["strength"] * np.clip(1.0 - np.abs(t - s["centre"]) * 2.2, 0, 1)
    arr *= grad[:, :, None]

    g = p["glare"]
    gx, gy = g["cx"] * fw2, g["cy"] * fh2
    rad = g["radius_frac"] * max(fw2, fh2)
    d2 = (xx - gx) ** 2 + (yy - gy) ** 2
    glare = np.exp(-d2 / (2 * rad * rad)) * (g["intensity"] * 190.0)
    arr += glare[:, :, None]

    wb = p["white_balance"]
    arr[:, :, 0] *= wb["r"]
    arr[:, :, 1] *= wb["g"]
    arr[:, :, 2] *= wb["b"]

    out = to_img(arr).filter(ImageFilter.GaussianBlur(p["blur_sigma"]))
    arr = add_noise(to_np(out), p["gaussian_noise_sigma"], rng)
    return jpeg_roundtrip(to_img(arr), p["jpeg_quality"])


def op_fax(img: Image.Image, p: dict, rng: np.random.Generator,
           marks: bool = True) -> Image.Image:
    base = img.convert("RGBA")
    if marks:
        for spec in p.get("stamps", []):
            draw_stamp(base, spec)
        for spec in p.get("signatures", []):
            draw_signature(base, spec)
        for spec in p.get("handwriting", []):
            draw_handwriting(base, spec)
        if p.get("staple"):
            draw_staple(base, p["staple"])
    flat = Image.new("RGB", base.size, (255, 255, 255))
    flat.paste(base, mask=base.split()[3])
    flat = flat.rotate(p["skew_deg"], expand=False, resample=Image.BICUBIC,
                       fillcolor=(255, 255, 255))
    grey = flat.convert("L")

    fax_dpi = p["fax_dpi"]
    w, h = grey.size
    small = grey.resize((max(1, int(w * fax_dpi / 200)), max(1, int(h * fax_dpi / 200))),
                        Image.LANCZOS)
    arr = add_noise(to_np(small), p["pre_noise_sigma"], rng)
    small = to_img(arr, "L")
    if p["dither"] == "floyd_steinberg":
        bil = small.convert("1")
    else:
        bil = small.point(lambda v, t=p["threshold"]: 255 if v > t else 0).convert("1")
    arr = np.asarray(bil).astype(np.uint8)
    mask = rng.random(arr.shape) < p["speckle_density"]
    flip = rng.random(arr.shape) < 0.5
    arr[mask & flip] = 0
    arr[mask & ~flip] = 1
    for _ in range(p["line_dropout_rows"]):
        y = int(rng.integers(0, arr.shape[0]))
        arr[y:y + int(rng.integers(1, 3)), :] = 1
    bil = Image.fromarray((arr * 255).astype(np.uint8), "L").convert("1")
    return bil.resize((w, h), Image.NEAREST).convert("1")


BASE_EFFECT_DEFAULTS = {
    "flatbed": {"paper_grey": 244, "skew_deg": 0.9, "lid_shadow_px": 6, "blur_sigma": 0.5,
                "contrast": 1.02, "brightness": 1.0, "gaussian_noise_sigma": 4.0,
                "dust_specks": 26, "jpeg_quality": 84},
    "phone": {"perspective_offsets_frac": [0.02] * 8, "rotation_deg": 1.4,
              "shadow": {"axis": "x", "strength": 0.3, "centre": 0.5},
              "glare": {"cx": 0.5, "cy": 0.4, "radius_frac": 0.16, "intensity": 0.45},
              "blur_sigma": 1.0, "gaussian_noise_sigma": 5.0,
              "white_balance": {"r": 1.02, "g": 1.0, "b": 0.98},
              "desk_tone": [206, 198, 184], "margin_frac": 0.05, "jpeg_quality": 74},
    "fax": {"skew_deg": 1.3, "fax_dpi": 120, "pre_noise_sigma": 12.0,
            "dither": "floyd_steinberg", "threshold": 138, "speckle_density": 0.006,
            "line_dropout_rows": 2},
}


def degrade_pages(rec: dict, source_pages: list[Path]) -> list[Image.Image]:
    tier = rec["tier"]
    p = rec["degradation"]
    doc_id = rec["doc_id"]
    if tier == 1:
        return [Image.open(sp).convert("RGB") for sp in source_pages]
    if tier == 2:
        return [op_flatbed(Image.open(sp), p, page_rng(doc_id, i))
                for i, sp in enumerate(source_pages)]
    if tier == 3:
        return [op_phone(Image.open(sp), p, page_rng(doc_id, i))
                for i, sp in enumerate(source_pages)]
    if tier == 4:
        return [op_fax(Image.open(sp), p, page_rng(doc_id, i))
                for i, sp in enumerate(source_pages)]

    # tier 5: assemble the bundle
    out: list[Image.Image] = []
    for i, item in enumerate(p["bundle_plan"]):
        spec = item["of"] if item["source"] == "duplicate" else item
        if spec["source"] == "cover_note":
            src = source_pages[-1]
        else:
            src = source_pages[spec["index"]]
        page = Image.open(src)
        cfg = p["per_page"][i]
        rng = page_rng(doc_id, 100 + i)
        effect = cfg["base_effect"]
        params = dict(BASE_EFFECT_DEFAULTS[effect])
        if effect == "flatbed":
            img = op_flatbed(page, params, rng)
        elif effect == "phone":
            img = op_phone(page, params, rng)
        else:
            img = op_fax(page, params, rng, marks=False).convert("RGB")
        if cfg["rotation_deg"]:
            img = img.rotate(-cfg["rotation_deg"], expand=True)
        img = img.filter(ImageFilter.GaussianBlur(cfg["extra_blur_sigma"]))
        # Two resamples, as a forwarded phone image gets: the sending app shrinks
        # the capture, then the copy is scaled to the stored long edge.
        frac = p["downscale_frac"]
        img = img.resize((max(1, int(img.width * frac)), max(1, int(img.height * frac))),
                         Image.LANCZOS)
        long_edge = p["final_long_edge_px"]
        scale = long_edge / max(img.size)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                         Image.BILINEAR)
        img = jpeg_roundtrip(img, p["jpeg_quality_pass1"])
        img = jpeg_roundtrip(img, p["jpeg_quality_pass2"])
        out.append(img)
    return out


# --------------------------------------------------------------------------- #
# Writing artefacts                                                           #
# --------------------------------------------------------------------------- #

def write_document(rec: dict, pages: list[Image.Image], out_dir: Path,
                   clean_pdf: Path) -> dict:
    tier = rec["tier"]
    ext = PAGE_EXT[tier]
    out_dir.mkdir(parents=True, exist_ok=True)
    page_records = []
    for i, img in enumerate(pages, start=1):
        path = out_dir / f"page-{i:02d}.{ext}"
        if ext == "jpg":
            q = rec["degradation"].get("jpeg_quality_pass2",
                                       rec["degradation"].get("jpeg_quality", 85))
            img.convert("RGB").save(path, format="JPEG", quality=q, subsampling=2)
        elif tier == 4:
            img.convert("1").save(path, format="PNG", optimize=True)
        else:
            img.convert("RGB").save(path, format="PNG", optimize=True)
        entry = {"page": i, "path": str(path.relative_to(HERE)),
                 "width": img.width, "height": img.height,
                 "sha256": sha256_file(path), "bytes": path.stat().st_size}
        if tier == 5:
            # Which source page this bundle page came from, and how it was turned.
            entry["source"] = rec["degradation"]["bundle_plan"][i - 1]
            entry["rotation_deg"] = rec["degradation"]["per_page"][i - 1]["rotation_deg"]
            entry["base_effect"] = rec["degradation"]["per_page"][i - 1]["base_effect"]
        page_records.append(entry)

    pdf_path = out_dir / "document.pdf"
    if tier == 1:
        shutil.copyfile(clean_pdf, pdf_path)
        pdf_kind = "vector (Chromium print output, copied unchanged)"
    else:
        rgb = [p.convert("RGB") for p in pages]
        rgb[0].save(pdf_path, format="PDF", save_all=True, append_images=rgb[1:],
                    resolution=float(rec["degradation"]["render_dpi"]))
        pdf_kind = "raster (degraded page images, one per page)"
    return {
        "pdf": {"path": str(pdf_path.relative_to(HERE)), "sha256": sha256_file(pdf_path),
                "bytes": pdf_path.stat().st_size, "kind": pdf_kind},
        "pages": page_records,
        "page_container": ext,
        "page_count": len(pages),
    }


def copy_split(rec: dict, dest_root: Path) -> None:
    src = DOCS_DIR / rec["doc_id"]
    dst = dest_root / "documents" / rec["doc_id"]
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_render.json"))


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Degrade rendered Messy Scan documents "
                                             "and assemble the dataset.")
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN_PATH)
    ap.add_argument("--render-dir", type=Path, default=RENDER_DIR)
    ap.add_argument("--out", type=Path, default=DOCS_DIR)
    ap.add_argument("--ground-truth", type=Path, default=GROUND_TRUTH)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--shard", type=int, default=0, help="0-based shard index")
    ap.add_argument("--shards", type=int, default=1, help="number of parallel shards")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--no-splits", action="store_true",
                    help="skip materialising sample/ and private/")
    ap.add_argument("--progress-every", type=int, default=25)
    args = ap.parse_args(argv)

    records = load_documents(args.plan)
    wanted = set(args.only) if args.only else None
    started = time.time()
    done = skipped = missing = 0

    for i, rec in enumerate(records, start=1):
        if wanted and rec["doc_id"] not in wanted:
            continue
        if args.shards > 1 and (i - 1) % args.shards != args.shard:
            continue
        src_dir = args.render_dir / rec["doc_id"]
        n_src = len(rec["logical_pages"]) + (1 if rec["tier"] == 5 else 0)
        source_pages = [src_dir / f"page-{k + 1:02d}.png" for k in range(n_src)]
        clean_pdf = src_dir / "clean.pdf"
        if not clean_pdf.exists() or not all(sp.exists() for sp in source_pages):
            rec["render"] = None
            missing += 1
            continue
        out_dir = args.out / rec["doc_id"]
        if args.skip_existing and (out_dir / "document.pdf").exists() and \
                len(list(out_dir.glob("page-*"))) == rec["page_count"]:
            rec["render"] = json.loads((out_dir / "_render.json").read_text()) \
                if (out_dir / "_render.json").exists() else None
            if rec["render"]:
                skipped += 1
                continue
        pages = degrade_pages(rec, source_pages)
        if len(pages) != rec["page_count"]:
            raise RuntimeError(f'{rec["doc_id"]}: produced {len(pages)} pages, '
                               f'plan says {rec["page_count"]}')
        render_rec = write_document(rec, pages, out_dir, clean_pdf)
        (out_dir / "_render.json").write_text(json.dumps(render_rec, sort_keys=True))
        rec["render"] = render_rec
        done += 1
        if args.progress_every and done % args.progress_every == 0:
            rate = done / max(time.time() - started, 1e-6)
            print(f"  {done} degraded ({rate:.1f}/s), {i}/{len(records)} scanned", flush=True)

    with args.ground_truth.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    if args.shards > 1:
        print("shard run: ground truth and splits are only complete after a final pass "
              "with --shards 1 --skip-existing")

    if not args.no_splits:
        for split_name, root in (("public_sample", SAMPLE_DIR), ("private_holdout", PRIVATE_DIR)):
            root.mkdir(parents=True, exist_ok=True)
            subset = [r for r in records if r["split"] == split_name]
            with (root / "ground-truth.jsonl").open("w", encoding="utf-8") as fh:
                for rec in subset:
                    fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            copied = 0
            for rec in subset:
                if rec.get("render"):
                    copy_split(rec, root)
                    copied += 1
            print(f"{split_name}: {len(subset)} documents listed, {copied} artefact sets "
                  f"copied to {root.name}/")

    rendered = sum(1 for r in records if r.get("render"))
    print(json.dumps({
        "documents_in_plan": len(records),
        "degraded_this_run": done,
        "skipped_existing": skipped,
        "not_yet_rendered": missing,
        "with_artefacts": rendered,
        "seconds": round(time.time() - started, 1),
        "ground_truth": str(args.ground_truth),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
