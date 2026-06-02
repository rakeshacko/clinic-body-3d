"""
fit_dexa.py - bounded DXA-style body composition -> Anny preview parameters.

This is a visual anthropometry fit, not a tissue simulation. Anny's phenotype
axes are latent shape controls, so DXA values are treated as priors:
  - sex and age are direct, with age passed through Anny's own nonlinear mapping
  - BMI + total %fat drive the global weight shape
  - ALMI drives the global muscle shape only after adiposity damping. DXA lean
    mass is not visual muscular definition, especially in high-BMI bodies.
  - regional %fat drives bounded local girth/fat controls
  - a bounded calibration matches live HTML height/mass plus estimated waist
    and abdomen depth targets

Run:
  /tmp/annyenv/bin/python asset-pipeline-v2/scripts/fit_dexa.py
"""
import json
import math
import os

import torch
import anny
from anny.shape_distribution import SimpleShapeDistribution


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DXA = os.path.join(ROOT, "preview", "dxa_members.json")
OUT = os.path.join(ROOT, "preview", "fitted_params.json")

DISPLAY_DENSITY = 1040.0  # kg/m^3, matches preview/anny_preview.html measureBody()
torch.manual_seed(0)

print("loading Anny...", flush=True)
model = anny.create_fullbody_model(rig="default", topology="default", local_changes=True).eval()
dtype = model.dtype
anthro = anny.Anthropometry(model)
agemap = SimpleShapeDistribution(model).morphological_age_mapping
PHENO = list(model.phenotype_labels)
LOCAL = set(model.local_change_labels)
print("model dtype:", dtype, "| phenotypes:", PHENO, "| locals:", len(LOCAL), flush=True)


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def norm(x, lo, hi):
    return clamp((x - lo) / (hi - lo))


def logit(p):
    p = clamp(p, 1e-4, 1.0 - 1e-4)
    return math.log(p / (1.0 - p))


def sigmoid_param(v):
    return torch.sigmoid(v).clamp(1e-4, 1.0 - 1e-4)


def as_model_tensor(v):
    if torch.is_tensor(v):
        return v.reshape(1).to(dtype=dtype)
    return torch.tensor([v], dtype=dtype)


def local_set(name, value, locals_):
    if name in LOCAL and value > 0.015:
        locals_[name] = round(clamp(value), 2)


def dxa_shape_targets(member, priors):
    p = member["profile"]
    total = member["bodyComposition"]["total"]
    regions = member["bodyComposition"]["regions"]
    male = p["sex"] == "male"
    trunk_pf = regions["trunk"]["percentFat"]
    limb_pf = (
        regions["left_arm"]["percentFat"]
        + regions["right_arm"]["percentFat"]
        + regions["left_leg"]["percentFat"]
        + regions["right_leg"]["percentFat"]
    ) / 4.0
    centrality = clamp((trunk_pf - limb_pf + 4.0) / 12.0)
    if male:
        waist_cm = 76.0 + 1.80 * max(0.0, p["bmi"] - 20.0) + 6.0 * centrality
        abdomen_depth_cm = 22.0 + 0.70 * max(0.0, p["bmi"] - 22.0) + 2.8 * centrality
    else:
        waist_cm = 68.0 + 1.45 * max(0.0, p["bmi"] - 20.0) + 4.0 * centrality
        abdomen_depth_cm = 20.0 + 0.55 * max(0.0, p["bmi"] - 22.0) + 2.0 * centrality
    return {
        "waist_m": waist_cm / 100.0,
        "abdomen_depth_m": abdomen_depth_cm / 100.0,
        "centrality": centrality,
        "trunk_to_limb_pf": round(trunk_pf - limb_pf, 2),
    }


def dxa_priors(member):
    p = member["profile"]
    total = member["bodyComposition"]["total"]
    regions = member["bodyComposition"]["regions"]
    male = p["sex"] == "male"
    height_m = p["heightCm"] / 100.0

    gender = 0.0 if male else 1.0
    anny_age = float(
        agemap.morphological_to_anny_age(
            torch.tensor([float(p["ageYears"])], dtype=torch.float64)
        )[0]
    )

    fat_norm = norm(total["percentFat"], 10.0 if male else 18.0, 34.0 if male else 44.0)
    bmi_norm = norm(p["bmi"], 19.0 if male else 18.5, 36.0 if male else 38.0)
    weight = clamp(0.08 + 0.82 * (0.58 * bmi_norm + 0.42 * fat_norm), 0.04, 0.95)

    app_lean = sum(
        regions[r]["leanMassG"]
        for r in ("left_arm", "right_arm", "left_leg", "right_leg")
    ) / 1000.0
    almi = app_lean / (height_m * height_m)
    muscle_base = norm(almi, 6.0 if male else 5.0, 12.5 if male else 11.0)
    # High-BMI people often carry high absolute lean mass. That should not
    # render as high muscle definition when total adiposity is high.
    muscle = clamp(muscle_base * (1.0 - 0.65 * (fat_norm ** 1.25)), 0.03, 0.82)

    arm_pf = (regions["left_arm"]["percentFat"] + regions["right_arm"]["percentFat"]) / 2.0
    leg_pf = (regions["left_leg"]["percentFat"] + regions["right_leg"]["percentFat"]) / 2.0
    trunk_pf = regions["trunk"]["percentFat"]
    trunk_delta = clamp((trunk_pf - total["percentFat"] + 8.0) / 16.0)
    limb_pf = (arm_pf + leg_pf) / 2.0
    centrality = clamp((trunk_pf - limb_pf + 4.0) / 12.0)
    leg_delta = clamp((leg_pf - total["percentFat"] + 8.0) / 16.0)
    arm = norm(arm_pf, 16.0 if male else 24.0, 44.0 if male else 50.0)
    leg = norm(leg_pf, 16.0 if male else 24.0, 44.0 if male else 50.0)
    trunk = norm(trunk_pf, 18.0 if male else 25.0, 44.0 if male else 50.0)

    locals_ = {}
    local_set("measure-upperarm-circ-incr", 0.08 + 0.28 * arm, locals_)
    local_set("l-upperarm-fat-incr", 0.05 + 0.30 * arm, locals_)
    local_set("r-upperarm-fat-incr", 0.05 + 0.30 * arm, locals_)
    local_set("l-lowerarm-fat-incr", 0.03 + 0.18 * arm, locals_)
    local_set("r-lowerarm-fat-incr", 0.03 + 0.18 * arm, locals_)

    local_set("measure-thigh-circ-incr", 0.08 + 0.36 * leg, locals_)
    local_set("l-upperleg-fat-incr", 0.06 + 0.34 * leg, locals_)
    local_set("r-upperleg-fat-incr", 0.06 + 0.34 * leg, locals_)
    local_set("l-lowerleg-fat-incr", 0.04 + 0.22 * leg, locals_)
    local_set("r-lowerleg-fat-incr", 0.04 + 0.22 * leg, locals_)
    local_set("buttocks-volume-incr", 0.10 + (0.22 if male else 0.34) * leg_delta, locals_)

    local_set("measure-waist-circ-incr", 0.06 + 0.42 * trunk, locals_)
    local_set("measure-hips-circ-incr", 0.08 + (0.30 * leg_delta if male else 0.46 * leg_delta), locals_)
    local_set("measure-underbust-circ-incr", 0.04 + 0.24 * trunk, locals_)
    local_set("measure-frontchest-dist-incr", 0.03 + 0.18 * trunk, locals_)
    local_set("torso-scale-horiz-incr", 0.06 + 0.30 * trunk, locals_)
    local_set("torso-scale-depth-incr", 0.04 + 0.36 * trunk_delta, locals_)
    local_set("hip-scale-depth-incr", 0.04 + 0.28 * max(trunk_delta, centrality * 0.65), locals_)
    local_set("hip-scale-horiz-incr", 0.04 + (0.16 if male else 0.26) * leg_delta, locals_)
    local_set("hip-trans-forward", 0.03 + 0.16 * centrality, locals_)
    local_set("pelvis-tone-incr", 0.02 + 0.16 * centrality, locals_)
    local_set("stomach-navel-out", 0.04 + 0.30 * trunk_delta, locals_)
    local_set("stomach-pregnant-incr", 0.02 + (0.18 if male else 0.25) * centrality * trunk, locals_)

    if not male:
        local_set("measure-bust-circ-incr", 0.12 + 0.34 * trunk, locals_)
        local_set("breast-volume-vert-up", 0.18 + 0.24 * fat_norm, locals_)

    return {
        "gender": gender,
        "age": clamp(anny_age),
        "weight": weight,
        "muscle": muscle,
        "height": 0.5,
        "proportions": 0.5,
        "locals": locals_,
        "debug": {
            "almi": round(almi, 2),
            "fat_norm": round(fat_norm, 3),
            "bmi_norm": round(bmi_norm, 3),
            "arm": round(arm, 3),
            "leg": round(leg, 3),
            "trunk": round(trunk, 3),
            "centrality": round(centrality, 3),
        },
    }


def abdomen_depth(rest_vertices):
    pts = rest_vertices[0]
    z = pts[:, 2]
    zc = z.min() + (z.max() - z.min()) * 0.54
    keep = (z >= zc - 0.035) & (z <= zc + 0.035)
    s = pts[keep]
    x = s[:, 0]
    center = torch.median(x)
    s = s[(x - center).abs() <= 0.38]
    y = s[:, 1]
    if y.numel() < 20:
        return torch.tensor(float("nan"), dtype=dtype)
    return torch.quantile(y, 0.95) - torch.quantile(y, 0.05)


def mesh_measures(params):
    pk = {
        k: as_model_tensor(params[k])
        for k in ("gender", "age", "weight", "muscle", "height", "proportions")
    }
    lk = {k: as_model_tensor(v) for k, v in params["locals"].items()}
    rest = model(phenotype_kwargs=pk, local_changes_kwargs=lk)["rest_vertices"]
    volume = anthro.volume(rest)
    height = anthro.height(rest)
    waist = anthro.waist_circumference(rest)
    abd_depth = abdomen_depth(rest)
    return height, volume, waist, abd_depth


def fit(member):
    p = member["profile"]
    params = dxa_priors(member)
    shape_targets = dxa_shape_targets(member, params)
    target_h = p["heightCm"] / 100.0
    target_v = p["weightKg"] / DISPLAY_DENSITY

    train_keys = ("weight", "muscle", "height")
    raw = {
        k: torch.tensor([logit(params[k])], dtype=dtype, requires_grad=True)
        for k in train_keys
    }
    raw_loc = {
        k: torch.tensor([logit(v)], dtype=dtype, requires_grad=True)
        for k, v in params["locals"].items()
    }
    opt = torch.optim.Adam(list(raw.values()) + list(raw_loc.values()), lr=0.035)

    base = dict(params)
    for _ in range(260):
        opt.zero_grad()
        trial = dict(base)
        for k in train_keys:
            trial[k] = sigmoid_param(raw[k])
        trial["locals"] = {k: sigmoid_param(v) for k, v in raw_loc.items()}
        h, v, waist, abd_depth = mesh_measures(trial)
        loss = 36.0 * ((h - target_h) / target_h) ** 2
        loss = loss + 12.0 * ((v - target_v) / target_v) ** 2
        loss = loss + 5.0 * ((waist - shape_targets["waist_m"]) / shape_targets["waist_m"]) ** 2
        loss = loss + 7.0 * ((abd_depth - shape_targets["abdomen_depth_m"]) / shape_targets["abdomen_depth_m"]) ** 2
        loss = loss + 1.25 * (trial["weight"] - params["weight"]) ** 2
        loss = loss + 3.00 * (trial["muscle"] - params["muscle"]) ** 2
        loss = loss + 4.00 * torch.relu(trial["muscle"] - params["muscle"] - 0.06) ** 2
        loss = loss + 0.20 * (trial["height"] - 0.5) ** 2
        for k, local_value in trial["locals"].items():
            target = torch.tensor([params["locals"][k]], dtype=dtype)
            loss = loss + 0.35 * (local_value - target) ** 2
        loss.sum().backward()
        opt.step()

    for k in train_keys:
        params[k] = float(sigmoid_param(raw[k]).detach())
    params["locals"] = {
        k: round(float(sigmoid_param(v).detach()), 2)
        for k, v in raw_loc.items()
        if float(sigmoid_param(v).detach()) > 0.015
    }

    with torch.no_grad():
        h, v, waist, abd_depth = mesh_measures(params)
        h_m = float(h)
        v_m = float(v)
        waist_m = float(waist)
        abd_depth_m = float(abd_depth)
        mass = v_m * DISPLAY_DENSITY
        bmi = mass / (h_m * h_m)

    return {
        "member": member["memberId"],
        "sex": p["sex"],
        "target": {
            "H": p["heightCm"],
            "kg": p["weightKg"],
            "bmi": p["bmi"],
            "V_L": round(target_v * 1000.0, 1),
        },
        "achieved": {
            "H": round(h_m * 100.0, 1),
            "kg": round(mass, 1),
            "bmi": round(bmi, 1),
            "V_L": round(v_m * 1000.0, 1),
            "waist": round(waist_m * 100.0, 1),
            "abdomenDepth": round(abd_depth_m * 100.0, 1),
        },
        "targets": {
            "waist": round(shape_targets["waist_m"] * 100.0, 1),
            "abdomenDepth": round(shape_targets["abdomen_depth_m"] * 100.0, 1),
            "centrality": round(shape_targets["centrality"], 3),
            "trunkToLimbFat": shape_targets["trunk_to_limb_pf"],
        },
        "params": {
            k: round(params[k], 3)
            for k in ("gender", "age", "weight", "muscle", "height", "proportions")
        },
        "locals": params["locals"],
        "debug": params["debug"],
    }


data = json.load(open(DXA))
fitted = {}
print(f"\n{'member':28} {'sex':6} target H/kg/BMI      achieved H/kg/BMI     params", flush=True)
for member in data["members"]:
    result = fit(member)
    target = result["target"]
    achieved = result["achieved"]
    params = result["params"]
    print(
        f"FIT {result['member']:26} {result['sex']:6} "
        f"{target['H']:.0f}/{target['kg']:.0f}/{target['bmi']:.1f}   ->   "
        f"{achieved['H']:.0f}/{achieved['kg']:.0f}/{achieved['bmi']:.1f}    "
        f"g{params['weight']:.2f} m{params['muscle']:.2f} h{params['height']:.2f} "
        f"age{params['age']:.2f} loc{result['locals']}",
        flush=True,
    )
    fitted[result["member"]] = {
        **params,
        "locals": result["locals"],
        "achieved": result["achieved"],
        "targets": result["targets"],
        "debug": result["debug"],
    }

json.dump(fitted, open(OUT, "w"), indent=2)
print("WROTE", OUT, flush=True)
print("DONE", flush=True)
