#!/usr/bin/env python3
"""Phase 0.3b — body-type skin shells via MakeHuman (MPFB2), Blender headless.

Run with:  blender -b -P 03b_build_shells.py

Generates a small library of frosted-skin envelopes for different body types
(gender / age / weight / build) using MPFB2's CC0 MakeHuman base mesh + morph
targets. Each shell is normalized into the SAME body-space the organ systems use
(bbox center -> origin, height -> TARGET_HEIGHT, y-up), so the fixed organ GLBs
still sit in the torso while only the skin envelope changes. Exports one
Draco-compressed GLB per body type to ../public/models/shell_<type>.glb.

MPFB2 is installed as a Blender extension (4.2+/5.x). The extension zip is built
by 01_fetch.sh into sources/mpfb/mpfb_ext.zip; falls back to /tmp/mpfb_ext.zip.

Fails loudly (sys.exit non-zero) if MPFB2 can't be loaded or a shell ends up empty
— we do not emit a placeholder body silently.
"""
import bpy, sys, math, importlib, os
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
OUT = (HERE / "../public/models").resolve()
MPFB_ZIP_CANDIDATES = [
    HERE / "sources/mpfb/mpfb_ext.zip",
    Path("/tmp/mpfb_ext.zip"),
]
MPFB_MODULES = ("bl_ext.user_default.mpfb", "bl_ext.blender_org.mpfb")

TARGET_HEIGHT = 1.8        # must match 03_build_glb.py so organs align
SHELL_TRI_TARGET = 45_000  # frosted envelope; low detail is fine
# At 1.8m the MakeHuman torso is ~0.27 deep front-back vs the BodyParts3D reference body's
# ~0.30, so the fixed organ set (sized for the reference) pokes out the chest/back by 1-3cm.
# Inflate the shell's DEPTH axis only to envelope the organs. Invisible from the front (the
# primary camera view); only affects the profile, where it reads as normal body depth.
DEPTH_INFLATE = 1.32

# Body-type library. Macro values are MakeHuman sliders (0..1). All shells are
# normalized to TARGET_HEIGHT, so the `height` macro only nudges proportions.
BODY_TYPES = {
    "neutral":      {"gender": 0.50, "age": 0.50, "weight": 0.50, "muscle": 0.50, "height": 0.50, "cupsize": 0.50},
    "female-young": {"gender": 0.06, "age": 0.40, "weight": 0.48, "muscle": 0.42, "height": 0.42, "cupsize": 0.60},
    "male-heavy":   {"gender": 0.94, "age": 0.58, "weight": 0.86, "muscle": 0.45, "height": 0.58, "cupsize": 0.50},
    "female-older": {"gender": 0.12, "age": 0.80, "weight": 0.56, "muscle": 0.34, "height": 0.46, "cupsize": 0.50},
}


def log(*a):
    print(*a, flush=True)


def load_mpfb():
    """Enable MPFB2 (installing the extension from zip if needed). Returns HumanService."""
    for mod in MPFB_MODULES:
        try:
            bpy.ops.preferences.addon_enable(module=mod)
            hs = importlib.import_module(mod + ".services.humanservice")
            log(f"  MPFB2 already installed, enabled {mod}")
            return hs.HumanService
        except Exception:
            pass

    zip_path = next((p for p in MPFB_ZIP_CANDIDATES if p.is_file()), None)
    if not zip_path:
        log(f"FATAL: MPFB2 extension zip not found. Looked in: {[str(p) for p in MPFB_ZIP_CANDIDATES]}")
        log("       Run 01_fetch.sh to build it (clones makehumancommunity/mpfb2 + zips the extension).")
        sys.exit(20)

    log(f"  installing MPFB2 extension from {zip_path}")
    bpy.ops.extensions.package_install_files(
        filepath=str(zip_path), repo="user_default", enable_on_install=True)
    for mod in MPFB_MODULES:
        try:
            bpy.ops.preferences.addon_enable(module=mod)
            hs = importlib.import_module(mod + ".services.humanservice")
            log(f"  enabled {mod}")
            return hs.HumanService
        except Exception as e:
            log(f"  enable {mod} -> {e!r}")
    log("FATAL: MPFB2 installed but could not be enabled/imported.")
    sys.exit(21)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bake_evaluated(obj):
    """MakeHuman morphs are shape keys, which block modifier_apply. Bake the
    evaluated mesh (flattens shape-key mix AND visible modifiers, incl. the
    'Hide helpers' MASK) into a clean mesh with no shape keys or modifiers."""
    deps = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(deps)
    new_me = bpy.data.meshes.new_from_object(
        eval_obj, preserve_all_data_layers=False, depsgraph=deps)
    old_me = obj.data
    obj.modifiers.clear()
    obj.data = new_me
    if old_me.users == 0:
        bpy.data.meshes.remove(old_me)


def tri_count(obj):
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


def world_bounds(obj):
    mn = Vector((math.inf,) * 3)
    mx = Vector((-math.inf,) * 3)
    for corner in obj.bound_box:
        w = obj.matrix_world @ Vector(corner)
        mn = Vector((min(mn[i], w[i]) for i in range(3)))
        mx = Vector((max(mx[i], w[i]) for i in range(3)))
    return mn, mx


def torso_depth_center(obj, mn, ext):
    """Front-back (Blender Y) center of the TORSO core, ignoring limbs/head.

    The organs are anchored to depth ~0, so we must wrap them with the torso — not the
    whole-body bbox. MakeHuman's arms/head/buttocks skew the full-body depth center
    behind the torso, which pushes organs out through the chest. Sample vertices in the
    hips→shoulders band and near the midline (excludes the abducted arms)."""
    z0 = mn.z + 0.50 * ext.z   # ~hip level
    z1 = mn.z + 0.82 * ext.z   # ~shoulder level
    xlim = 0.12 * ext.z        # central column only -> excludes arms
    cx = mn.x + 0.5 * ext.x
    mw = obj.matrix_world
    ys = []
    for v in obj.data.vertices:
        w = mw @ v.co
        if z0 <= w.z <= z1 and abs(w.x - cx) <= xlim:
            ys.append(w.y)
    return (min(ys) + max(ys)) * 0.5 if ys else (mn.y + 0.5 * ext.y)


def normalize(obj):
    """Scale to TARGET_HEIGHT; center width(X) + height(Z) on the full body, but center
    depth(Y) on the TORSO core so the organs (anchored at depth ~0) sit inside the chest."""
    mn, mx = world_bounds(obj)
    extent = mx - mn
    height = max(extent.x, extent.y, extent.z)   # Blender Z (up) is tallest
    scale = TARGET_HEIGHT / height if height > 0 else 1.0
    cy = torso_depth_center(obj, mn, extent)
    center = Vector(((mn.x + mx.x) * 0.5, cy, (mn.z + mx.z) * 0.5))
    # Per-axis pivot scale about `center`: v' = S * (v - center). Depth (Blender Y) is
    # inflated so the skin envelopes the fixed organ set; width/height use plain scale.
    S = Matrix.Diagonal((scale, scale * DEPTH_INFLATE, scale, 1.0))
    obj.matrix_world = S @ Matrix.Translation(-center) @ obj.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
    return extent, scale


def decimate(obj, target):
    tris = tri_count(obj)
    if tris <= target:
        return
    ratio = target / tris
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    m = obj.modifiers.new("decimate", "DECIMATE")
    m.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=m.name)


def base_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.75, 0.86, 0.88, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.5
    return mat


def export_glb(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_yup=True,
    )


def build_one(HumanService, type_name, macros):
    reset_scene()
    macro = {
        "gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5,
        "proportions": 0.5, "height": 0.5, "cupsize": 0.5, "firmness": 0.5,
        "race": {"asian": 0.34, "caucasian": 0.33, "african": 0.33},
    }
    macro.update(macros)
    bm = HumanService.create_human(
        mask_helpers=True, detailed_helpers=False, extra_vertex_groups=False,
        feet_on_ground=True, scale=0.1, macro_detail_dict=macro)
    # flatten shape-key morphs + collapse the "Hide helpers" MASK -> body only
    bake_evaluated(bm)
    raw = tri_count(bm)
    if raw == 0:
        log(f"FATAL: shell '{type_name}' produced zero geometry.")
        sys.exit(22)
    # MakeHuman's anterior faces Blender -Y, which export_yup maps to glTF +Z — the
    # same anterior direction as the organ GLBs and toward the scene camera. So no
    # rotation is needed; rotating here would flip the body front-to-back.
    extent, scale = normalize(bm)
    decimate(bm, SHELL_TRI_TARGET)
    bm.data.materials.clear()
    bm.data.materials.append(base_material(f"mat_shell_{type_name}"))
    bm.name = bm.data.name = f"shell_{type_name}"
    out = OUT / f"shell_{type_name}.glb"
    export_glb(bm, out)
    log(f"  shell_{type_name}: raw={raw:,} tris -> {tri_count(bm):,} tris  "
        f"extent={tuple(round(e,2) for e in extent)} scale={scale:.4f}  -> {out.name}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flagged_path = HERE / "flagged_sources.json"
    if flagged_path.is_file():
        import json
        if "mpfb-makehuman" in set(json.loads(flagged_path.read_text()).get("flagged", [])):
            log("MakeHuman/MPFB2 flagged by license audit; skipping shell generation.")
            sys.exit(0)
    HumanService = load_mpfb()
    log(f"==> building {len(BODY_TYPES)} body-type shells")
    for type_name, macros in BODY_TYPES.items():
        build_one(HumanService, type_name, macros)
    log("==> shell build complete")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        log(f"FATAL: unhandled error in 03b_build_shells: {e}")
        sys.exit(1)
