"""
Verify that fitted organ/system GLBs remain inside the Anny shell envelope.

Run with Blender:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/verify_body_fit.py

This is a geometric smoke test for the visualization fit. It is not a medical/anatomical
validation. It checks representative body presets by:
  1. fetching the Anny mesh for the preset,
  2. converting it into the app's body space,
  3. loading each compressed GLB system via Blender,
  4. applying the same coarse organ-fit transform used by src/bodyFit.ts,
  5. ensuring transformed system vertices sit inside the shell's vertical slice envelope.
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import bpy
from mathutils import Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANNY_URL = os.environ.get("VITE_ANNY_URL", "http://localhost:8765").rstrip("/")
SYSTEM_IDS = (
    "cardiovascular",
    "respiratory",
    "digestive",
    "endocrine",
    "urinary",
    "nervous",
    "skeletal",
)


@dataclass(frozen=True)
class Transform:
    position: tuple[float, float, float]
    scale: tuple[float, float, float]


DEFAULT_ORGAN_FIT = {
    "heightResponse": 1.0,
    "torsoResponse": 0.8,
    "depthResponse": 0.55,
    "placementResponse": 1.0,
}

PRESETS = [
    {
        "id": "male-central",
        "params": {
            "gender": 0.0,
            "age": 0.78,
            "height": 0.42,
            "weight": 0.66,
            "muscle": 0.26,
            "proportions": 0.5,
            "torsoWidth": 0.58,
            "torsoDepth": 0.62,
            "abdomen": 0.72,
            "hips": 0.42,
            "centrality": 0.95,
        },
    },
    {
        "id": "male-athletic",
        "params": {
            "gender": 0.0,
            "age": 0.78,
            "height": 0.56,
            "weight": 0.26,
            "muscle": 0.46,
            "proportions": 0.56,
            "torsoWidth": 0.55,
            "torsoDepth": 0.45,
            "abdomen": 0.18,
            "hips": 0.45,
            "centrality": 0.25,
        },
    },
    {
        "id": "female-lean",
        "params": {
            "gender": 1.0,
            "age": 0.78,
            "height": 0.32,
            "weight": 0.23,
            "muscle": 0.2,
            "proportions": 0.54,
            "torsoWidth": 0.42,
            "torsoDepth": 0.35,
            "abdomen": 0.18,
            "hips": 0.5,
            "centrality": 0.2,
        },
    },
    {
        "id": "female-high-adiposity",
        "params": {
            "gender": 1.0,
            "age": 0.8,
            "height": 0.42,
            "weight": 0.9,
            "muscle": 0.18,
            "proportions": 0.5,
            "torsoWidth": 0.72,
            "torsoDepth": 0.7,
            "abdomen": 0.86,
            "hips": 0.7,
            "centrality": 0.76,
        },
    },
    {
        "id": "short-average",
        "params": {
            "gender": 0.5,
            "age": 0.8,
            "height": 0.12,
            "weight": 0.45,
            "muscle": 0.25,
            "proportions": 0.44,
            "torsoWidth": 0.5,
            "torsoDepth": 0.5,
            "abdomen": 0.45,
            "hips": 0.45,
            "centrality": 0.45,
        },
    },
    {
        "id": "tall-average",
        "params": {
            "gender": 0.5,
            "age": 0.8,
            "height": 0.86,
            "weight": 0.48,
            "muscle": 0.28,
            "proportions": 0.58,
            "torsoWidth": 0.52,
            "torsoDepth": 0.5,
            "abdomen": 0.42,
            "hips": 0.48,
            "centrality": 0.35,
        },
    },
]


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def mild(value: float, lo: float, hi: float, response: float) -> float:
    target = lo + (hi - lo) * clamp01(value)
    return 1.0 + (target - 1.0) * clamp01(response)


def compute_system_fit(system_id: str, params: dict[str, float], tuning: dict[str, float]) -> Transform:
    p = {k: clamp01(float(v)) for k, v in params.items()}
    height = mild(p["height"], 0.78, 1.22, tuning["heightResponse"])
    torso_x = mild(p["torsoWidth"], 0.94, 1.1, tuning["torsoResponse"])
    chest_depth = mild(p["torsoDepth"], 0.94, 1.08, tuning["depthResponse"])
    abdomen_depth = mild(p["abdomen"], 0.96, 1.08, tuning["depthResponse"] * 0.45)
    hip_x = mild(p["hips"], 0.94, 1.08, tuning["torsoResponse"] * 0.55)
    torso_y = mild(p["proportions"], 0.95, 1.07, tuning["heightResponse"] * 0.6)
    y_offset = (height - 1.0) * 0.16 * tuning["placementResponse"]
    pelvis_offset = (height - 1.0) * -0.08 * tuning["placementResponse"]
    abdomen_forward = (p["centrality"] - 0.5) * 0.035 * tuning["placementResponse"]
    internal_depth_offset = -0.11 * tuning["placementResponse"]
    digestive_depth_offset = -0.185 * tuning["placementResponse"]
    pelvis_depth_offset = -0.18 * tuning["placementResponse"]
    head_depth_offset = -0.2 * tuning["placementResponse"]

    if system_id == "cardiovascular":
        return Transform((0.0, y_offset - 0.02, internal_depth_offset), (torso_x * 0.92, height * 0.86, chest_depth * 0.9))
    if system_id == "respiratory":
        return Transform((0.0, y_offset - 0.03, internal_depth_offset), (torso_x * 0.94, torso_y * 0.78, chest_depth * 0.92))
    if system_id == "digestive":
        return Transform(
            (0.0, pelvis_offset - 0.005, digestive_depth_offset + abdomen_forward * 0.35),
            (max(torso_x, hip_x) * 0.8, torso_y * height * 0.96, abdomen_depth * 0.72),
        )
    if system_id == "endocrine":
        return Transform((0.0, y_offset, internal_depth_offset), (torso_x, height, chest_depth))
    if system_id == "urinary":
        return Transform((0.0, pelvis_offset - 0.015, pelvis_depth_offset + abdomen_forward * 0.4), (hip_x, height * 0.98, abdomen_depth))
    if system_id == "nervous":
        return Transform((0.0, y_offset - 0.01, head_depth_offset), (height * 0.9, height * 0.96, height * 0.9))
    if system_id == "skeletal":
        return Transform((0.0, 0.0, pelvis_depth_offset), (torso_x * 0.8, height * 0.95, chest_depth * 0.8))
    raise ValueError(system_id)


def anny_query(params: dict[str, float]) -> str:
    p = {k: clamp01(float(v)) for k, v in params.items()}
    q = {
        "gender": p["gender"],
        "age": p["age"],
        "height": p["height"],
        "weight": p["weight"],
        "muscle": p["muscle"],
        "proportions": p["proportions"],
        "measure-waist-circ-incr": 0.06 + 0.42 * p["abdomen"],
        "torso-scale-horiz-incr": 0.06 + 0.3 * p["torsoWidth"],
        "torso-scale-depth-incr": 0.04 + 0.36 * p["torsoDepth"],
        "measure-underbust-circ-incr": 0.04 + 0.24 * p["torsoWidth"],
        "measure-frontchest-dist-incr": 0.03 + 0.18 * p["torsoDepth"],
        "measure-hips-circ-incr": 0.08 + 0.38 * p["hips"],
        "hip-scale-horiz-incr": 0.04 + 0.24 * p["hips"],
        "hip-scale-depth-incr": 0.04 + 0.28 * max(p["torsoDepth"], p["centrality"] * 0.65),
        "hip-trans-forward": 0.03 + 0.16 * p["centrality"],
        "pelvis-tone-incr": 0.02 + 0.16 * p["centrality"],
        "stomach-navel-out": 0.04 + 0.3 * p["abdomen"],
        "stomach-pregnant-incr": 0.02 + 0.22 * p["centrality"] * p["abdomen"],
        "measure-thigh-circ-incr": 0.08 + 0.22 * p["weight"],
        "l-upperleg-fat-incr": 0.05 + 0.26 * p["weight"],
        "r-upperleg-fat-incr": 0.05 + 0.26 * p["weight"],
        "measure-upperarm-circ-incr": 0.08 + 0.18 * max(p["weight"], p["muscle"]),
        "l-upperarm-fat-incr": 0.04 + 0.22 * p["weight"],
        "r-upperarm-fat-incr": 0.04 + 0.22 * p["weight"],
    }
    if p["gender"] > 0.55:
        q["measure-bust-circ-incr"] = 0.12 + 0.3 * p["torsoWidth"]
        q["breast-volume-vert-up"] = 0.16 + 0.2 * p["weight"]
    return urllib.parse.urlencode({k: f"{clamp01(v):.3f}" for k, v in q.items()})


def fetch_anny_vertices(params: dict[str, float]) -> list[tuple[float, float, float]]:
    url = f"{ANNY_URL}/mesh?{anny_query(params)}"
    try:
        data = urllib.request.urlopen(url, timeout=20).read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Anny server unavailable at {ANNY_URL}: {e}") from e

    floats = memoryview(data).cast("f")
    verts = []
    min_x = min_y = min_z = math.inf
    max_x = max_y = max_z = -math.inf
    for i in range(0, len(floats), 3):
        x = float(floats[i])
        y = float(floats[i + 2])
        z = -float(floats[i + 1])
        verts.append((x, y, z))
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        min_z, max_z = min(min_z, z), max(max_z, z)

    low_torso = min_y + (max_y - min_y) * 0.25
    high_torso = min_y + (max_y - min_y) * 0.8
    torso = [(x, z) for x, y, z in verts if low_torso <= y <= high_torso]
    torso_x = sorted(x for x, _ in torso)
    torso_z = sorted(z for _, z in torso)

    def median(values: list[float], fallback: float) -> float:
        if not values:
            return fallback
        return values[len(values) // 2]

    cx = median(torso_x, (min_x + max_x) / 2.0)
    cy = (min_y + max_y) / 2.0 + 0.02
    cz = median(torso_z, (min_z + max_z) / 2.0)
    return [(x - cx, y - cy, z - cz) for x, y, z in verts]


def load_system_vertices(system_id: str) -> list[tuple[float, float, float]]:
    path = os.path.join(ROOT, "public", "models", f"system_{system_id}.glb")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=path)

    verts = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for v in obj.data.vertices:
            p = obj.matrix_world @ v.co
            # Blender import is Z-up; app space is Y-up.
            verts.append((float(p.x), float(p.z), float(p.y)))
    if not verts:
        raise RuntimeError(f"No vertices loaded for {system_id}")
    return verts


def transform_vertex(v: tuple[float, float, float], t: Transform) -> tuple[float, float, float]:
    return (
        v[0] * t.scale[0] + t.position[0],
        v[1] * t.scale[1] + t.position[1],
        v[2] * t.scale[2] + t.position[2],
    )


def build_slices(shell: list[tuple[float, float, float]], bins: int = 72) -> tuple[list[dict[str, float]], float, float]:
    min_y = min(v[1] for v in shell)
    max_y = max(v[1] for v in shell)
    step = (max_y - min_y) / bins
    slices = [
        {"min_x": math.inf, "max_x": -math.inf, "min_z": math.inf, "max_z": -math.inf, "count": 0}
        for _ in range(bins)
    ]
    for x, y, z in shell:
        idx = max(0, min(bins - 1, int((y - min_y) / step)))
        s = slices[idx]
        s["min_x"], s["max_x"] = min(s["min_x"], x), max(s["max_x"], x)
        s["min_z"], s["max_z"] = min(s["min_z"], z), max(s["max_z"], z)
        s["count"] += 1
    return slices, min_y, step


def verify_inside_shell(
    preset_id: str,
    system_id: str,
    transformed: list[tuple[float, float, float]],
    slices: list[dict[str, float]],
    min_y: float,
    step: float,
) -> dict[str, float]:
    # GLB systems are stylized/curated and can be close to the shell. The margin is a
    # visualization tolerance, not a clinical clearance.
    margin_x = 0.08 if system_id == "skeletal" else 0.045
    margin_z = 0.08 if system_id == "skeletal" else 0.055
    outside = 0
    checked = 0

    for x, y, z in transformed:
        idx = int((y - min_y) / step)
        if idx < 0 or idx >= len(slices):
            outside += 1
            checked += 1
            continue
        # Expand one bin above/below to avoid false failures at sparse shell slices.
        group = slices[max(0, idx - 1) : min(len(slices), idx + 2)]
        group = [s for s in group if s["count"] > 8]
        if not group:
            outside += 1
            checked += 1
            continue
        min_x = min(s["min_x"] for s in group) - margin_x
        max_x = max(s["max_x"] for s in group) + margin_x
        min_z = min(s["min_z"] for s in group) - margin_z
        max_z = max(s["max_z"] for s in group) + margin_z
        checked += 1
        if x < min_x or x > max_x or z < min_z or z > max_z:
            outside += 1

    outside_ratio = outside / max(1, checked)
    allowed = 0.025 if system_id == "skeletal" else 0.01
    if outside_ratio > allowed:
        raise AssertionError(
            f"{preset_id}/{system_id}: {outside_ratio:.3%} vertices outside shell envelope "
            f"(allowed {allowed:.3%})"
        )
    return {"checked": checked, "outside": outside, "outsideRatio": outside_ratio}


def main() -> None:
    system_vertices = {system_id: load_system_vertices(system_id) for system_id in SYSTEM_IDS}
    results = {}
    for preset in PRESETS:
        shell = fetch_anny_vertices(preset["params"])
        slices, min_y, step = build_slices(shell)
        preset_results = {}
        for system_id, verts in system_vertices.items():
            fit = compute_system_fit(system_id, preset["params"], DEFAULT_ORGAN_FIT)
            transformed = [transform_vertex(v, fit) for v in verts]
            preset_results[system_id] = verify_inside_shell(
                preset["id"], system_id, transformed, slices, min_y, step
            )
        results[preset["id"]] = preset_results
        max_ratio = max(v["outsideRatio"] for v in preset_results.values())
        print(f"PASS {preset['id']}: max outside ratio {max_ratio:.3%}")

    print(json.dumps(results, indent=2))
    print("PASS body-fit shell enclosure verifier")


if __name__ == "__main__":
    main()
