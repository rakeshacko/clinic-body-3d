# DXA to Anny Body Parameter Mapping

## Purpose

This document explains how the prototype maps DXA-style regional body-composition data into
Anny parametric body controls.

The mapping is used to create a plausible patient-specific outer body shape for the 3D review
experience. It is a visual anthropometry fit, not a tissue simulation and not a diagnostic
model. DXA composition values are treated as shape priors, then a bounded optimization step
adjusts Anny controls so the generated mesh approximately matches the member's height, mass,
waist estimate, and abdomen-depth estimate.

Primary implementation:

- Mapping and fitting script: `asset-pipeline-v2/scripts/fit_dexa.py`
- Demo DXA payloads: `asset-pipeline-v2/preview/dxa_members.json`
- Fitted output used by the preview: `asset-pipeline-v2/preview/fitted_params.json`
- Live mesh server: `asset-pipeline-v2/anny_server.py`
- Browser preview fallback mapping: `asset-pipeline-v2/preview/anny_preview.html`

## Input Data

Each member has two input groups.

`profile`:

- `ageYears`
- `sex`
- `heightCm`
- `weightKg`
- `bmi`

`bodyComposition.total`:

- `fatMassG`
- `leanMassG`
- `percentFat`

`bodyComposition.regions`:

- `head`
- `left_arm`
- `right_arm`
- `trunk`
- `left_leg`
- `right_leg`

Each region contains:

- `fatMassG`
- `leanMassG`
- `percentFat`

The current demo payloads are synthetic DXA-style samples. They are useful for validating
the visual behavior but should not be treated as clinical records.

## Output Parameters

The mapping writes Anny global phenotype controls:

- `gender`
- `age`
- `weight`
- `muscle`
- `height`
- `proportions`

It also writes bounded local shape controls under `locals`, for example:

- `measure-waist-circ-incr`
- `measure-hips-circ-incr`
- `measure-thigh-circ-incr`
- `measure-upperarm-circ-incr`
- `torso-scale-horiz-incr`
- `torso-scale-depth-incr`
- `hip-scale-depth-incr`
- `stomach-navel-out`
- `stomach-pregnant-incr`
- limb fat controls such as `l-upperleg-fat-incr`

Only local controls supported by the loaded Anny model are emitted. Values below `0.015`
are dropped to avoid tiny, visually meaningless changes.

## Mapping Overview

The mapping has two stages.

1. Build heuristic priors from DXA fields.
2. Optimize a small subset of Anny controls against measurable body targets.

The priors determine the direction of the fit: sex, age, global adiposity, apparent muscle,
and regional fat distribution. The optimization step keeps the generated mesh closer to the
member's height and mass while still respecting the visual priors.

## Normalization

Most DXA-derived quantities are mapped into Anny's `0..1` parameter range with a bounded
normalization:

```txt
norm(x, lo, hi) = clamp((x - lo) / (hi - lo), 0, 1)
```

Sex-specific ranges are used because the same value has different visual meaning across
male and female bodies.

Examples:

```txt
male total fat percent:   10..34 -> 0..1
female total fat percent: 18..44 -> 0..1

male BMI:                 19..36 -> 0..1
female BMI:               18.5..38 -> 0..1

male ALMI:                6..12.5 -> 0..1
female ALMI:              5..11 -> 0..1
```

## Global Phenotype Priors

### Gender

`gender` is mapped directly from profile sex:

```txt
male   -> 0.0
female -> 1.0
```

This follows Anny's convention in the current model.

### Age

Chronological age is not passed linearly. The fitting script uses Anny's own morphological
age mapping:

```txt
ageYears -> SimpleShapeDistribution(model).morphological_age_mapping -> Anny age
```

The browser preview mirrors this with a hand-coded anchor table so the slider reads in
rough chronological years while still driving Anny's nonlinear age axis.

### Weight Shape

The global `weight` shape is driven by a blend of BMI and total body-fat percentage:

```txt
fat_norm = norm(total.percentFat, sex_specific_fat_low, sex_specific_fat_high)
bmi_norm = norm(profile.bmi, sex_specific_bmi_low, sex_specific_bmi_high)

weight = clamp(0.08 + 0.82 * (0.58 * bmi_norm + 0.42 * fat_norm), 0.04, 0.95)
```

BMI receives slightly more weight because it reflects overall body scale, while total fat
percentage refines how adipose the shape should look.

### Muscle Shape

The global `muscle` shape is based on appendicular lean mass index, then damped by adiposity.

Appendicular lean mass is computed from arms and legs:

```txt
appendicular_lean_kg =
  (left_arm.leanMassG + right_arm.leanMassG +
   left_leg.leanMassG + right_leg.leanMassG) / 1000

ALMI = appendicular_lean_kg / height_m^2
```

Then:

```txt
muscle_base = norm(ALMI, sex_specific_almi_low, sex_specific_almi_high)
muscle = clamp(muscle_base * (1 - 0.65 * fat_norm^1.25), 0.03, 0.82)
```

The damping is intentional. DXA lean mass is not the same thing as visible muscle definition.
Higher-BMI bodies often have high absolute lean mass, but that should not render as a
bodybuilder-like visual shape when total adiposity is high.

### Height and Proportions

The heuristic prior starts with:

```txt
height = 0.5
proportions = 0.5
```

`height` is then optimized during the fitting step. `proportions` currently stays neutral.

## Regional Fat and Local Shape Priors

The local controls use regional percent-fat values.

Arm fat:

```txt
arm_pf = average(left_arm.percentFat, right_arm.percentFat)
arm = norm(arm_pf, male ? 16 : 24, male ? 44 : 50)
```

Leg fat:

```txt
leg_pf = average(left_leg.percentFat, right_leg.percentFat)
leg = norm(leg_pf, male ? 16 : 24, male ? 44 : 50)
```

Trunk fat:

```txt
trunk_pf = trunk.percentFat
trunk = norm(trunk_pf, male ? 18 : 25, male ? 44 : 50)
```

Distribution deltas:

```txt
trunk_delta = clamp((trunk_pf - total.percentFat + 8) / 16)
leg_delta = clamp((leg_pf - total.percentFat + 8) / 16)

limb_pf = average(arm_pf, leg_pf)
centrality = clamp((trunk_pf - limb_pf + 4) / 12)
```

`centrality` is the main abdominal-adiposity signal. It increases when trunk fat is high
relative to limb fat.

## Local Control Examples

The following are representative mappings from `fit_dexa.py`.

Upper body and arms:

```txt
measure-upperarm-circ-incr = 0.08 + 0.28 * arm
l-upperarm-fat-incr        = 0.05 + 0.30 * arm
r-upperarm-fat-incr        = 0.05 + 0.30 * arm
l-lowerarm-fat-incr        = 0.03 + 0.18 * arm
r-lowerarm-fat-incr        = 0.03 + 0.18 * arm
```

Lower body and legs:

```txt
measure-thigh-circ-incr = 0.08 + 0.36 * leg
l-upperleg-fat-incr     = 0.06 + 0.34 * leg
r-upperleg-fat-incr     = 0.06 + 0.34 * leg
l-lowerleg-fat-incr     = 0.04 + 0.22 * leg
r-lowerleg-fat-incr     = 0.04 + 0.22 * leg
buttocks-volume-incr    = 0.10 + (male ? 0.22 : 0.34) * leg_delta
```

Torso and abdomen:

```txt
measure-waist-circ-incr       = 0.06 + 0.42 * trunk
measure-underbust-circ-incr   = 0.04 + 0.24 * trunk
measure-frontchest-dist-incr  = 0.03 + 0.18 * trunk
torso-scale-horiz-incr        = 0.06 + 0.30 * trunk
torso-scale-depth-incr        = 0.04 + 0.36 * trunk_delta
stomach-navel-out             = 0.04 + 0.30 * trunk_delta
stomach-pregnant-incr         = 0.02 + (male ? 0.18 : 0.25) * centrality * trunk
```

Pelvis and hips:

```txt
measure-hips-circ-incr = 0.08 + (male ? 0.30 : 0.46) * leg_delta
hip-scale-depth-incr   = 0.04 + 0.28 * max(trunk_delta, centrality * 0.65)
hip-scale-horiz-incr   = 0.04 + (male ? 0.16 : 0.26) * leg_delta
hip-trans-forward      = 0.03 + 0.16 * centrality
pelvis-tone-incr       = 0.02 + 0.16 * centrality
```

Female-only chest controls:

```txt
measure-bust-circ-incr = 0.12 + 0.34 * trunk
breast-volume-vert-up  = 0.18 + 0.24 * fat_norm
```

## Anthropometric Targets

The fitting step uses real profile fields and derived visual targets.

Direct targets:

```txt
target_height_m = profile.heightCm / 100
target_volume_m3 = profile.weightKg / DISPLAY_DENSITY
```

`DISPLAY_DENSITY` is `1040 kg/m^3`, matching the browser preview's approximate
mesh-to-mass conversion.

Derived waist and abdomen-depth targets:

```txt
centrality = clamp((trunk_percent_fat - limb_percent_fat + 4) / 12)
```

Male:

```txt
waist_cm = 76 + 1.80 * max(0, BMI - 20) + 6.0 * centrality
abdomen_depth_cm = 22 + 0.70 * max(0, BMI - 22) + 2.8 * centrality
```

Female:

```txt
waist_cm = 68 + 1.45 * max(0, BMI - 20) + 4.0 * centrality
abdomen_depth_cm = 20 + 0.55 * max(0, BMI - 22) + 2.0 * centrality
```

These are visual calibration targets. They are not measured DXA outputs. They give the
optimizer a stronger torso-shape signal than height and mass alone.

## Optimization

After priors are created, the script optimizes:

- global `weight`
- global `muscle`
- global `height`
- every emitted local control

The optimizer is Adam with a learning rate of `0.035` for `260` iterations.

The optimized values are parameterized through logits and sigmoid so they stay in `0..1`.
This prevents the fit from leaving Anny's valid control range.

The loss combines:

- height error
- body-volume error
- waist-circumference error
- abdomen-depth error
- regularization back toward the original `weight` prior
- stronger regularization back toward the original `muscle` prior
- penalty if optimized `muscle` rises more than `0.06` above its prior
- mild regularization toward neutral `height`
- local-control regularization back toward local priors

Conceptually:

```txt
loss =
  36.00 * height_error^2 +
  12.00 * volume_error^2 +
   5.00 * waist_error^2 +
   7.00 * abdomen_depth_error^2 +
   1.25 * weight_prior_error^2 +
   3.00 * muscle_prior_error^2 +
   4.00 * excess_muscle_error^2 +
   0.20 * height_neutral_error^2 +
   0.35 * sum(local_prior_error^2)
```

Height is weighted most heavily because a body that is visibly the wrong height breaks trust
quickly. Muscle is regularized strongly because the DXA lean-mass signal can otherwise push
the visual body toward unrealistically muscular shapes.

## Mesh Measurements Used by the Fit

During optimization, the script generates Anny rest vertices and measures:

- height: `anny.Anthropometry(model).height(rest_vertices)`
- volume: `anny.Anthropometry(model).volume(rest_vertices)`
- waist circumference: `anny.Anthropometry(model).waist_circumference(rest_vertices)`
- abdomen depth: custom slice-based measurement around the mid-abdomen

The abdomen-depth helper selects a horizontal slice around the abdominal region and measures
front-back depth using robust quantiles.

## Output File Shape

`fitted_params.json` stores one entry per member:

```json
{
  "member-id": {
    "gender": 0.0,
    "age": 0.814,
    "weight": 0.658,
    "muscle": 0.257,
    "height": 0.366,
    "proportions": 0.5,
    "locals": {
      "measure-waist-circ-incr": 0.28
    },
    "achieved": {
      "H": 174.9,
      "kg": 95.1,
      "bmi": 31.1,
      "V_L": 91.4,
      "waist": 105.3,
      "abdomenDepth": 30.6
    },
    "targets": {
      "waist": 101.8,
      "abdomenDepth": 31.1,
      "centrality": 1.0,
      "trunkToLimbFat": 8.27
    },
    "debug": {
      "almi": 9.24,
      "fat_norm": 0.821,
      "bmi_norm": 0.706,
      "arm": 0.373,
      "leg": 0.386,
      "trunk": 0.65,
      "centrality": 1.0
    }
  }
}
```

The preview page uses this fitted output when available. If no fitted params exist for a
member, it falls back to the heuristic browser-side mapping.

## How to Regenerate Fitted Parameters

The fitting script expects the Anny environment used by the preview server.

```bash
/tmp/annyenv/bin/python asset-pipeline-v2/scripts/fit_dexa.py
```

The script reads:

```txt
asset-pipeline-v2/preview/dxa_members.json
```

and writes:

```txt
asset-pipeline-v2/preview/fitted_params.json
```

## Interpretation for the Doctor Review Product

The generated body should be described as a personalized body-shape visualization based on
screening and body-composition data.

It should not be described as:

- a clinical reconstruction
- an exact DXA-derived body model
- patient-specific internal anatomy
- a diagnostic organ-position model

When organ/system meshes are fit inside the Anny shell, they should follow coarse external
body-space transforms only: height, torso width, torso depth, hip/pelvis position, and abdomen
profile. That is appropriate for patient communication, but not for anatomy measurement.

## Known Limitations

- DXA does not provide a full 3D surface scan.
- DXA lean mass does not equal visible muscle definition.
- Regional percent-fat values are coarse; they do not encode exact fat distribution.
- Waist and abdomen-depth targets are derived calibration estimates, not DXA measurements.
- Anny controls are latent shape controls. A parameter value is not a direct clinical unit.
- The fitting objective prioritizes believable visualization over exact anthropometry.
- Internal organs are not patient-specific. Any organ fitting should remain approximate.

## Future Improvements

- Add real waist or circumference measurements when available.
- Add front/side photo or depth-camera landmarks to constrain torso depth and silhouette.
- Store confidence bands for each fitted parameter.
- Calibrate sex-specific and age-specific normalization ranges against a real cohort.
- Fit organ/system transforms from stable body landmarks once those landmarks are available
  from the Anny mesh or a registered template.
