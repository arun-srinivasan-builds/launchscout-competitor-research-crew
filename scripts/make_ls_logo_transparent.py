"""Derive a transparent-background LS logo from the supplied artwork (static/ls_logo.png).

Faithful cleanup only: no lettering is redrawn. Solid letter pixels are kept as supplied;
antialiased edge pixels are un-blended from the off-white background (alpha from coverage,
colour = the letter colour), and everything else (background, blurred ghost letters, soft
document smudges) becomes transparent. The original file is left untouched.

Run:  .venv\Scripts\python scripts\make_ls_logo_transparent.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "static" / "ls_logo.png"
TARGET = ROOT / "static" / "ls_logo_transparent.png"

SOLID_LUMA = 110  # solid maroon/navy letter pixels are far darker than any ghost artefact
EDGE_PIXELS = 2  # antialiased edges are at most this far from a solid pixel
MIN_ALPHA = 0.06
PAD_FRACTION = 0.03


def _luma(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _dilate(mask: np.ndarray, steps: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(steps):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        grown[1:, 1:] |= out[:-1, :-1]
        grown[:-1, :-1] |= out[1:, 1:]
        grown[1:, :-1] |= out[:-1, 1:]
        grown[:-1, 1:] |= out[1:, :-1]
        out = grown
    return out


def render() -> tuple[Image.Image, dict[str, object]]:
    """Pure derivation: (transparent image, measurements). Writes nothing."""
    image = Image.open(SOURCE).convert("RGB")
    rgb = np.asarray(image).astype(np.float64)
    h, w, _ = rgb.shape
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
    background = np.median(corners, axis=0)
    bg_luma = float(_luma(background))
    luma = _luma(rgb)

    solid = luma < SOLID_LUMA
    reddish = (rgb[..., 0] - rgb[..., 2]) > 25
    maroon_seed = solid & reddish
    navy_seed = solid & ~reddish
    maroon = np.median(rgb[maroon_seed], axis=0)
    navy = np.median(rgb[navy_seed], axis=0)

    region = _dilate(solid, EDGE_PIXELS)
    # class of each region pixel: its own hue where clear, otherwise the nearer solid class
    diff = rgb[..., 0] - rgb[..., 2]
    is_maroon = np.where(np.abs(diff) > 6, diff > 0, False)
    maroon_near = _dilate(maroon_seed, EDGE_PIXELS)
    navy_near = _dilate(navy_seed, EDGE_PIXELS)
    ambiguous = np.abs(diff) <= 6
    is_maroon = np.where(ambiguous, maroon_near & ~navy_near, is_maroon)

    letter_luma = np.where(is_maroon, _luma(maroon), _luma(navy))
    alpha = np.clip((bg_luma - luma) / np.maximum(bg_luma - letter_luma, 1.0), 0.0, 1.0)
    alpha = np.where(region, alpha, 0.0)
    alpha = np.where(alpha < MIN_ALPHA, 0.0, alpha)

    solid_pixels = alpha >= 0.995
    letter_rgb = np.where(is_maroon[..., None], maroon, navy)
    out_rgb = np.where(solid_pixels[..., None], rgb, letter_rgb)

    rgba = np.dstack([np.clip(out_rgb, 0, 255), alpha * 255.0]).round().astype(np.uint8)
    ys, xs = np.where(alpha > 0.02)
    pad = int(round(PAD_FRACTION * max(xs.max() - xs.min(), ys.max() - ys.min())))
    box = (
        max(0, xs.min() - pad),
        max(0, ys.min() - pad),
        min(w, xs.max() + 1 + pad),
        min(h, ys.max() + 1 + pad),
    )
    result = Image.fromarray(rgba, "RGBA").crop(box)
    return result, {
        "source_size": (w, h),
        "background": tuple(int(v) for v in background),
        "maroon": tuple(int(v) for v in maroon),
        "navy": tuple(int(v) for v in navy),
        "crop_box": tuple(int(v) for v in box),
        "output_size": result.size,
    }


def build() -> dict[str, object]:
    result, info = render()
    result.save(TARGET, optimize=True)
    return info


if __name__ == "__main__":
    for key, value in build().items():
        print(f"{key}: {value}")  # noqa: T201 - command-line tool output
