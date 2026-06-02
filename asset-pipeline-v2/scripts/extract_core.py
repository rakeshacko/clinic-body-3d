"""
extract_core.py — Phase 1 of the converged architecture (see docs/SPEC.md §5).

Extract the INVARIANT CORE (skin envelope + 7 organ systems) from the single
Z-Anatomy body, normalized ONCE. Because every part comes from one body and gets
the SAME transform, organs-stay-inside-skin is guaranteed by construction — none
of the per-system centering / depth-inflation hacks from the old multi-body path.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/extract_core.py

Outputs: asset-pipeline-v2/out/{body_shell,system_*}.glb + manifest.json
This folder is intentionally separate from the live asset-pipeline/ + public/models/.
"""
import bpy, bmesh, os, json, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # asset-pipeline-v2/
OUT = os.path.join(ROOT, "out")
MAP = os.path.join(ROOT, "zanatomy-to-system.json")
BLEND = "/tmp/zanat/Z-Anatomy/Startup.blend"

def log(*a): print("CORE:", *a, flush=True)

if not os.path.exists(BLEND):
    log("MISSING blend:", BLEND, "- extract Z-Anatomy.zip from sources/z-anatomy first.")
    sys.exit(1)
os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(MAP))

bpy.ops.wm.open_mainfile(filepath=BLEND)

# Z-Anatomy ships most collections disabled in the view layer; enable + unhide all
# so bpy.ops selection / convert / join can see the geometry.
def enable_all(lc):
    lc.exclude = False
    lc.hide_viewport = False
    try: lc.collection.hide_viewport = False
    except Exception: pass
    for ch in lc.children: enable_all(ch)
enable_all(bpy.context.view_layer.layer_collection)
for o in bpy.data.objects:
    o.hide_viewport = False
    try: o.hide_set(False)
    except Exception: pass

DROP_SUF = tuple(cfg["drop_suffixes"])
REPRO = [s.lower() for s in cfg["repro_exclude_substrings"]]
NC = [s.lower() for s in cfg["nc_exclude_substrings"]]
ART = [s.lower() for s in cfg.get("artifact_exclude_substrings", [])]
TARGET_H = cfg["target_height"]
# Generous body envelope (normalized space) for the outlier-vertex backstop.
# Real anatomy: skin x~±0.36, y~±0.15, z~±0.90. Anything well beyond is an atlas artifact.
CLIP = {"x": 0.60, "y": 0.45, "z": 1.15}

def tris(o):
    return sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) if (o.type == "MESH" and o.data) else 0

def dropped(name):
    nm = name.lower()
    if name.endswith(DROP_SUF): return True
    if any(r in nm for r in REPRO): return True
    if any(a in nm for a in ART): return True
    return False

def clip_outliers(obj):
    """Delete vertices well outside the body envelope (atlas construction-curve strays)."""
    me = obj.data
    bm = bmesh.new(); bm.from_mesh(me)
    doomed = [v for v in bm.verts
              if abs(v.co.x) > CLIP["x"] or abs(v.co.y) > CLIP["y"] or abs(v.co.z) > CLIP["z"]]
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(me); bm.free()
    return len(doomed)

def coll(name): return bpy.data.collections.get(name)

def coll_objs(cname):
    c = coll(cname)
    if not c:
        log("MISSING collection", cname); return []
    out = []
    for o in c.all_objects:
        if o.type not in {"MESH", "CURVE"}: continue
        if dropped(o.name): continue
        if o.type == "MESH" and tris(o) == 0: continue   # landmark/empty patches
        out.append(o)
    return out

# ---- ONE global normalize transform, from the skin (full-body surface) ----
skin_cfg = cfg["skin"]
skin_excl = [s.lower() for s in skin_cfg.get("exclude_substrings", [])]
def skin_keep(o):
    nm = o.name.lower()
    return not any(s in nm for s in skin_excl)

skin_objs = [o for o in coll_objs(skin_cfg["collection"]) if skin_keep(o)]
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for o in skin_objs:
    for cnr in o.bound_box:
        w = o.matrix_world @ Vector(cnr)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ext = mx - mn
scale = TARGET_H / ext.z                      # Blender Z is vertical
center = (mn + mx) * 0.5
REF = Matrix.Diagonal((scale, scale, scale, 1.0)) @ Matrix.Translation(-center)
log(f"skin bbox ext=({ext.x:.2f},{ext.y:.2f},{ext.z:.2f}) scale={scale:.4f} "
    f"center=({center.x:.2f},{center.y:.2f},{center.z:.2f}) [Blender Z-up]")

# ---- assignment for the mixed Visceral collection (4 systems in one) ----
def build_visceral_assignment():
    src = cfg["systems"]  # those with "from"
    priority = cfg["_visceral_priority"]
    rules = {k: [s.lower() for s in src[k]["include_substrings"]] for k in priority}
    fromcoll = src[priority[0]]["from"]
    assign = {k: [] for k in priority}
    unmatched = []
    for o in coll_objs(fromcoll):
        nm = o.name.lower()
        placed = False
        for k in priority:
            if any(s in nm for s in rules[k]):
                assign[k].append(o.name); placed = True; break
        if not placed: unmatched.append(o.name)
    if unmatched:
        log(f"visceral unmatched ({len(unmatched)}):", ", ".join(unmatched[:20]),
            "..." if len(unmatched) > 20 else "")
    return assign

visceral = build_visceral_assignment()

# ---- gather object NAMES per target up front (join is destructive) ----
def names_for(sysid, spec):
    if "collections" in spec:
        objs = []
        for cn in spec["collections"]:
            objs += coll_objs(cn)
        if spec.get("apply_nc_exclude"):
            objs = [o for o in objs if not any(n in o.name.lower() for n in NC)]
        return [o.name for o in objs]
    if "from" in spec:
        return list(visceral.get(sysid, []))
    return []

plan = {}  # target -> (names, budget, license_flags)
plan["body_shell"] = ([o.name for o in skin_objs], skin_cfg["budget"], [])
for sysid, spec in cfg["systems"].items():
    nm = names_for(sysid, spec)
    plan["system_" + sysid] = (nm, spec["budget"],
                               [s.lower() for s in spec.get("license_flag_substrings", [])])

# ---- extract one target: convert curves -> mesh, join, normalize, decimate, export ----
def world_bounds(obj):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx

def extract(target, names, budget, flags):
    objs = [bpy.data.objects.get(n) for n in names]
    objs = [o for o in objs if o is not None]
    if not objs:
        log("SKIP", target, "(no objects)"); return None
    bpy.ops.object.select_all(action="DESELECT")
    flagged = []
    for o in objs:
        try: o.hide_set(False)
        except Exception: pass
        o.hide_viewport = False
        if o.type == "CURVE" and o.data.bevel_depth == 0 and o.data.bevel_object is None:
            o.data.bevel_depth = 0.0012      # give wire vessels/nerves tube volume
            o.data.bevel_resolution = 1
        o.select_set(True)
        if any(f in o.name.lower() for f in flags): flagged.append(o.name)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    raw = tris(obj)
    obj.matrix_world = REF @ obj.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    clipped = clip_outliers(obj)
    if raw > budget:
        m = obj.modifiers.new("d", "DECIMATE"); m.ratio = budget / raw
        bpy.ops.object.modifier_apply(modifier=m.name)
    obj.name = obj.data.name = target
    mn, mx = world_bounds(obj)
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT, target + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
        export_apply=True, export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6, export_yup=True)
    rec = {"target": target, "objects": len(objs), "raw_tris": raw, "final_tris": tris(obj),
           "clipped_verts": clipped,
           "bbox_min": [round(v, 3) for v in mn], "bbox_max": [round(v, 3) for v in mx],
           "license_flags": flagged}
    log(f"{target}: objs={len(objs)} raw={raw:,} -> final={tris(obj):,} clip={clipped} "
        f"z[{mn.z:+.2f},{mx.z:+.2f}] x[{mn.x:+.2f},{mx.x:+.2f}] y[{mn.y:+.2f},{mx.y:+.2f}]"
        + (f"  ⚠FLAG:{flagged}" if flagged else ""))
    return rec

# body_shell first so it exists, then the 7 systems
manifest = {"target_height": TARGET_H, "results": []}
order = ["body_shell"] + ["system_" + k for k in cfg["systems"].keys()]
for t in order:
    names, budget, flags = plan[t]
    rec = extract(t, names, budget, flags)
    if rec: manifest["results"].append(rec)

total = sum(r["final_tris"] for r in manifest["results"] if r["target"] != "body_shell")
manifest["systems_total_tris"] = total
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
log(f"systems total tris = {total:,} (app budget is 150k — curation pass later)")
log("DONE")
