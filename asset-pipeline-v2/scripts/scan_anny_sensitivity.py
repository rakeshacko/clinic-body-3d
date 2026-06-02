"""
scan_anny_sensitivity.py - measure how Anny local controls affect body metrics.

The output is intentionally empirical. It perturbs each body-relevant local
change and records observable mesh deltas: height, volume, waist circumference,
and approximate torso/limb slice widths/depths. Use this to choose mapper
controls by measured effect instead of by parameter name.

Run:
  /tmp/annyenv/bin/python asset-pipeline-v2/scripts/scan_anny_sensitivity.py
"""
import json
import math
import os
import re

import torch
import anny


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FITTED = os.path.join(ROOT, "preview", "fitted_params.json")
OUT_JSON = os.path.join(ROOT, "out", "anny_sensitivity.json")
OUT_MD = os.path.join(ROOT, "out", "anny_sensitivity.md")

DISPLAY_DENSITY = 1040.0
PERTURB = 0.35

BODY_RE = re.compile(
    r"arm|leg|thigh|calf|knee|ankle|wrist|neck|head-fat|head-age|"
    r"head-scale|hip|pelvis|stomach|torso|waist|bust|breast|buttock|"
    r"underbust|chest|shoulder|bulge",
    re.I,
)
EXCLUDE_RE = re.compile(r"eye|ear|mouth|nose|chin|cheek|forehead|eyebrow", re.I)


print("loading Anny...", flush=True)
model = anny.create_fullbody_model(rig="default", topology="default", local_changes=True).eval()
dtype = model.dtype
anthro = anny.Anthropometry(model)
PHENO = list(model.phenotype_labels)
LOCALS = list(model.local_change_labels)


def tensor(v):
    return torch.tensor([float(v)], dtype=dtype)


def vertices(phenos, locals_):
    pk = {k: tensor(phenos.get(k, 0.5)) for k in PHENO}
    lk = {k: tensor(v) for k, v in locals_.items()}
    with torch.no_grad():
        return model(phenotype_kwargs=pk, local_changes_kwargs=lk)["rest_vertices"]


def pct(vals, q):
    if vals.numel() == 0:
        return float("nan")
    return float(torch.quantile(vals, q))


def slice_box(v, z_frac, band=0.035, central_limit=None):
    pts = v[0]
    z = pts[:, 2]
    zmin, zmax = float(z.min()), float(z.max())
    zc = zmin + (zmax - zmin) * z_frac
    keep = (z >= zc - band) & (z <= zc + band)
    s = pts[keep]
    if s.shape[0] < 20:
        return {"width_cm": float("nan"), "depth_cm": float("nan")}
    if central_limit is not None:
        x = s[:, 0]
        center = torch.median(x)
        # Exclude arms/hands from torso slices. The old wide 0.38m cutoff made
        # arm-width controls look like abdomen controls in the sensitivity scan.
        s = s[(x - center).abs() <= central_limit]
        if s.shape[0] < 20:
            return {"width_cm": float("nan"), "depth_cm": float("nan")}
    x = s[:, 0]
    y = s[:, 1]
    return {
        "width_cm": (pct(x, 0.95) - pct(x, 0.05)) * 100.0,
        "depth_cm": (pct(y, 0.95) - pct(y, 0.05)) * 100.0,
    }


def metrics(v):
    volume = float(anthro.volume(v))
    height = float(anthro.height(v))
    waist = float(anthro.waist_circumference(v))
    chest = slice_box(v, 0.66, central_limit=0.30)
    abdomen = slice_box(v, 0.54, central_limit=0.28)
    hip = slice_box(v, 0.45, central_limit=0.34)
    thigh = slice_box(v, 0.33)
    upper_arm = slice_box(v, 0.58)
    return {
        "height_cm": height * 100.0,
        "volume_l": volume * 1000.0,
        "mass_kg": volume * DISPLAY_DENSITY,
        "bmi": volume * DISPLAY_DENSITY / (height * height),
        "waist_circ_cm": waist * 100.0,
        "chest_width_cm": chest["width_cm"],
        "chest_depth_cm": chest["depth_cm"],
        "abdomen_width_cm": abdomen["width_cm"],
        "abdomen_depth_cm": abdomen["depth_cm"],
        "hip_width_cm": hip["width_cm"],
        "hip_depth_cm": hip["depth_cm"],
        "thigh_width_cm": thigh["width_cm"],
        "thigh_depth_cm": thigh["depth_cm"],
        "upper_arm_width_cm": upper_arm["width_cm"],
        "upper_arm_depth_cm": upper_arm["depth_cm"],
    }


def base_params():
    bases = {
        "neutral_male": {
            "gender": 0.0,
            "age": 0.8,
            "weight": 0.5,
            "muscle": 0.45,
            "height": 0.4,
            "proportions": 0.5,
            "locals": {},
        },
        "neutral_female": {
            "gender": 1.0,
            "age": 0.8,
            "weight": 0.5,
            "muscle": 0.25,
            "height": 0.4,
            "proportions": 0.5,
            "locals": {},
        },
    }
    if os.path.exists(FITTED):
        fitted = json.load(open(FITTED))
        if "male-central-adiposity" in fitted:
            f = fitted["male-central-adiposity"]
            bases["male_central_adiposity"] = {
                k: f[k] for k in ("gender", "age", "weight", "muscle", "height", "proportions")
            }
            bases["male_central_adiposity"]["locals"] = f.get("locals", {})
    return bases


def scan_base(name, base):
    candidates = [l for l in LOCALS if BODY_RE.search(l) and not EXCLUDE_RE.search(l)]
    base_v = vertices(base, base.get("locals", {}))
    base_m = metrics(base_v)
    rows = []
    for label in candidates:
        local = dict(base.get("locals", {}))
        local[label] = min(1.0, max(PERTURB, local.get(label, 0.0) + PERTURB))
        m = metrics(vertices(base, local))
        delta = {k: round(m[k] - base_m[k], 3) for k in base_m}
        rows.append(
            {
                "label": label,
                "base": name,
                "delta": delta,
                "score": round(sum(abs(v) for v in delta.values() if math.isfinite(v)), 3),
            }
        )
    return {"base_metrics": {k: round(v, 3) for k, v in base_m.items()}, "rows": rows}


def top(rows, metric, limit=12):
    return sorted(rows, key=lambda r: abs(r["delta"][metric]), reverse=True)[:limit]


os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
all_results = {}
for name, base in base_params().items():
    print("scanning", name, flush=True)
    all_results[name] = scan_base(name, base)

json.dump(all_results, open(OUT_JSON, "w"), indent=2)

lines = ["# Anny Local-Control Sensitivity", ""]
for name, result in all_results.items():
    rows = result["rows"]
    lines += [f"## {name}", "", "Base metrics:", ""]
    for k, v in result["base_metrics"].items():
        lines.append(f"- `{k}`: {v}")
    for metric in ("waist_circ_cm", "abdomen_depth_cm", "abdomen_width_cm", "hip_width_cm", "chest_depth_cm", "thigh_width_cm"):
        lines += ["", f"Top `{metric}` movers:", ""]
        for row in top(rows, metric):
            lines.append(f"- `{row['label']}`: {row['delta'][metric]:+.2f}")
    lines.append("")

open(OUT_MD, "w").write("\n".join(lines))
print("WROTE", OUT_JSON)
print("WROTE", OUT_MD)
