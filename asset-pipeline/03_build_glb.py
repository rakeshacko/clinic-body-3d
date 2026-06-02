#!/usr/bin/env python3
"""Phase 0.3 — Blender headless build.

Run with:  blender -b -P 03_build_glb.py

For each body system in fma-to-system.json (minus any source flagged by 02), import the
referenced BodyParts3D STLs, join them into ONE mesh named `system_<id>`, register all
systems to a common body-space transform (derived from the skin shell bounds so organs sit
where they belong), decimate so the combined system triangle count stays within budget, apply
a neutral base material, and export one Draco-compressed GLB per system to ../public/models/.
The skin shell (FMA7163) is exported separately as body_shell.glb.

Fails loudly (sys.exit non-zero) if a system ends up with zero geometry or an STL referenced
by the map is missing — we do not emit an empty/partial system silently.
"""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
STL_DIR = HERE / "sources/bodyparts3d/assets/BodyParts3D_data/stl"
OUT = (HERE / "../public/models").resolve()
MAP = HERE / "fma-to-system.json"
FLAGGED = HERE / "flagged_sources.json"
SHELL_FMA = "FMA7163"

TARGET_HEIGHT = 1.8          # body height in scene units (three.js); matches registry framing
SYSTEM_TRI_BUDGET = 150_000  # combined triangles across all system GLBs (04 enforces this)
SHELL_TRI_TARGET = 45_000    # skin shell decimated separately (frosted, low detail is fine)


def log(*a):
    print(*a, flush=True)


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for b in list(block):
            try:
                block.remove(b)
            except Exception:
                pass


def import_stl(path: Path):
    before = set(bpy.data.objects)
    # Blender 4.0+/5.x native importer.
    bpy.ops.wm.stl_import(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    return new


def join_objects(objs, name):
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def tri_count(obj):
    me = obj.data
    return sum(max(0, len(p.vertices) - 2) for p in me.polygons)


def world_bounds(objs):
    mn = Vector((math.inf,) * 3)
    mx = Vector((-math.inf,) * 3)
    for o in objs:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    return mn, mx


def apply_transform(obj, scale, offset):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.location = (obj.location - offset) * scale
    obj.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)


def decimate(obj, ratio):
    if ratio >= 0.999:
        return
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
        bsdf.inputs["Base Color"].default_value = (0.8, 0.82, 0.85, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def assign_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def export_glb(obj, path: Path):
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fmap = json.loads(MAP.read_text())
    flagged = set(json.loads(FLAGGED.read_text()).get("flagged", [])) if FLAGGED.exists() else set()
    if "bodyparts3d" in flagged:
        log("FATAL: bodyparts3d flagged by license audit; refusing to build geometry.")
        sys.exit(2)

    reset_scene()

    missing = []
    built = {}   # id -> joined object (pre-transform)

    # ---- import + join shell ----
    shell_path = STL_DIR / f"{SHELL_FMA}.stl"
    if not shell_path.is_file():
        log(f"FATAL: skin shell STL missing: {shell_path}")
        sys.exit(3)
    shell_parts = import_stl(shell_path)
    shell = join_objects(shell_parts, "body_shell")
    log(f"  body_shell: {tri_count(shell):,} tris (raw)")

    # ---- import + join each system ----
    for sysid, items in fmap["systems"].items():
        objs = []
        for it in items:
            p = STL_DIR / f"{it['fma']}.stl"
            if not p.is_file():
                missing.append(f"{sysid}:{it['fma']}")
                continue
            objs.extend(import_stl(p))
        if not objs:
            log(f"FATAL: system '{sysid}' produced zero geometry (all STLs missing).")
            sys.exit(4)
        obj = join_objects(objs, f"system_{sysid}")
        built[sysid] = obj
        log(f"  system_{sysid}: {tri_count(obj):,} tris (raw), parts={len(items)}")

    if missing:
        log(f"  WARNING: {len(missing)} referenced STL(s) missing, skipped: {missing}")

    # ---- common body-space transform from shell bounds ----
    mn, mx = world_bounds([shell])
    extent = mx - mn
    height = max(extent.z, extent.y, extent.x)  # tallest axis = body height
    scale = TARGET_HEIGHT / height if height > 0 else 1.0
    center = (mn + mx) * 0.5
    log(f"  shell bounds extent={tuple(round(e,1) for e in extent)} height={height:.1f} -> scale={scale:.5f}")

    for obj in [shell, *built.values()]:
        apply_transform(obj, scale, center)

    # ---- decimate systems to combined budget ----
    sys_total = sum(tri_count(o) for o in built.values())
    ratio = min(1.0, SYSTEM_TRI_BUDGET / sys_total) if sys_total > 0 else 1.0
    log(f"  system tris (scaled) total={sys_total:,} budget={SYSTEM_TRI_BUDGET:,} -> decimate ratio={ratio:.4f}")
    for obj in built.values():
        decimate(obj, ratio)

    # shell decimate separately
    shell_tris = tri_count(shell)
    shell_ratio = min(1.0, SHELL_TRI_TARGET / shell_tris) if shell_tris > 0 else 1.0
    decimate(shell, shell_ratio)

    # ---- material + export ----
    for sysid, obj in built.items():
        assign_material(obj, base_material(f"mat_{sysid}"))
        export_glb(obj, OUT / f"system_{sysid}.glb")
        log(f"  exported system_{sysid}.glb  ({tri_count(obj):,} tris)")

    assign_material(shell, base_material("mat_shell"))
    export_glb(shell, OUT / "body_shell.glb")
    log(f"  exported body_shell.glb  ({tri_count(shell):,} tris)")

    log("==> build complete")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        log(f"FATAL: unhandled error in 03_build_glb: {e}")
        sys.exit(1)
