"""
spike_param_skin.py — parametric skin (MPFB2 / MakeHuman lineage == Anny) + Z-Anatomy core.

Tests the inversion: a PARAMETRIC body as the skin envelope, with the fixed Z-Anatomy
organ core registered inside it ONCE (a torso depth-fit), then body type + age vary the
skin OUTWARD so organs stay inside. MPFB2 is the proven-headless stand-in for Anny (same
CC0 MakeHuman blendshape lineage); swap to Anny's calibrated targets once it's confirmed.

  blender -b -P scripts/spike_param_skin.py
Out: renders/param_<body>_{side,front}.png   (side = the poke-through test)
"""
import bpy, sys, os, glob, importlib
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
RENDERS = os.path.join(ROOT, "renders")
MPFB_ZIP = os.path.join(os.path.dirname(ROOT), "asset-pipeline", "sources", "mpfb", "mpfb_ext.zip")
MPFB_MODULES = ("bl_ext.user_default.mpfb", "bl_ext.blender_org.mpfb")
TARGET_H = 1.8

def log(*a): print("PSK:", *a, flush=True)

def load_mpfb():
    for mod in MPFB_MODULES:
        try:
            bpy.ops.preferences.addon_enable(module=mod)
            return importlib.import_module(mod + ".services.humanservice").HumanService
        except Exception: pass
    if not os.path.isfile(MPFB_ZIP):
        log("FATAL: mpfb zip missing", MPFB_ZIP); sys.exit(20)
    bpy.ops.extensions.package_install_files(filepath=MPFB_ZIP, repo="user_default", enable_on_install=True)
    for mod in MPFB_MODULES:
        try:
            bpy.ops.preferences.addon_enable(module=mod)
            return importlib.import_module(mod + ".services.humanservice").HumanService
        except Exception as e: log("enable err", repr(e))
    log("FATAL: mpfb load failed"); sys.exit(21)

def sel(obj):
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def bake_evaluated(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), preserve_all_data_layers=False, depsgraph=deps)
    obj.modifiers.clear(); obj.data = me

def wbounds(obj):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        for i in range(3): mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx

def torso_y_center(obj, mn, ext):
    z0, z1, xl, cx = mn.z + 0.5*ext.z, mn.z + 0.82*ext.z, 0.1*ext.z, mn.x + 0.5*ext.x
    ys = []
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        if z0 <= w.z <= z1 and abs(w.x - cx) <= xl: ys.append(w.y)
    return (min(ys) + max(ys)) * 0.5 if ys else (mn.y + 0.5*ext.y)

def normalize(obj):
    """Height -> 1.8, centre width/height on bbox, depth on the TORSO core (no inflate hacks)."""
    mn, mx = wbounds(obj); ext = mx - mn; s = TARGET_H / ext.z
    center = Vector(((mn.x+mx.x)/2, torso_y_center(obj, mn, ext), (mn.z+mx.z)/2))
    obj.matrix_world = Matrix.Diagonal((s, s, s, 1.0)) @ Matrix.Translation(-center) @ obj.matrix_world
    sel(obj); bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)

def build_body(HS, macros):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    macro = {"gender":0.5,"age":0.5,"muscle":0.5,"weight":0.5,"proportions":0.5,
             "height":0.5,"cupsize":0.5,"firmness":0.5,
             "race":{"asian":0.34,"caucasian":0.33,"african":0.33}}
    macro.update(macros)
    bm = HS.create_human(mask_helpers=True, detailed_helpers=False, extra_vertex_groups=False,
                         feet_on_ground=True, scale=0.1, macro_detail_dict=macro)
    bake_evaluated(bm)
    for o in list(bpy.data.objects):          # drop eyes/teeth/etc -> body only
        if o.type == "MESH" and o is not bm: bpy.data.objects.remove(o, do_unlink=True)
    normalize(bm); bm.name = "skin"
    return bm

def import_organs():
    objs = []
    for f in sorted(glob.glob(os.path.join(OUT, "system_*.glb"))):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=f)
        objs += [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    org = bpy.context.view_layer.objects.active
    sel(org); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    org.name = "organs"
    return org

def torso_depth(obj, zlo=-0.10, zhi=0.35, xl=0.15):
    ys = []
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        if zlo <= w.z <= zhi and abs(w.x) <= xl: ys.append(w.y)
    return (max(ys) - min(ys)) if ys else 0.0

# ---------- materials + render ----------
def skin_mat():
    m = bpy.data.materials.new("skin"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.60, 0.85, 0.92, 1)
    b.inputs["Roughness"].default_value = 0.35
    if "Alpha" in b.inputs: b.inputs["Alpha"].default_value = 0.16
    m.blend_method = "BLEND"; m.show_transparent_back = False; return m

def organ_mat():
    m = bpy.data.materials.new("org"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; c = (0.95, 0.45, 0.28)
    b.inputs["Base Color"].default_value = (*c, 1)
    if "Emission Color" in b.inputs: b.inputs["Emission Color"].default_value = (*c, 1)
    if "Emission Strength" in b.inputs: b.inputs["Emission Strength"].default_value = 0.55
    b.inputs["Roughness"].default_value = 0.5; return m

def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 820, 1300
    sc.render.image_settings.file_format = "PNG"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.045, 1)
    for loc, e in [((0,-4,3),3.0), ((4,-2,1),1.5), ((-3,3,2),1.0)]:
        l = bpy.data.lights.new("L","SUN"); l.energy = e
        ob = bpy.data.objects.new("L", l); sc.collection.objects.link(ob); ob.location = loc
        ob.rotation_euler = (Vector((0,0,0)) - Vector(loc)).to_track_quat("-Z","Y").to_euler()
    def cam(loc):
        cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 2.05
        ob = bpy.data.objects.new("c", cd); sc.collection.objects.link(ob); ob.location = loc
        ob.rotation_euler = (Vector((0,0,0.02)) - Vector(loc)).to_track_quat("-Z","Y").to_euler(); return ob
    return cam((4,0,0)), cam((0,-4,0))

def render(cam, path):
    sc = bpy.context.scene; sc.camera = cam; sc.render.filepath = path
    bpy.ops.render.render(write_still=True); log("wrote", os.path.basename(path))

# ---------- run ----------
HS = load_mpfb()
BODIES = {
    "lean":    {"gender":0.9, "age":0.50, "weight":0.12, "muscle":0.45},
    "average": {"gender":0.9, "age":0.50, "weight":0.50, "muscle":0.50},
    "heavy":   {"gender":0.9, "age":0.55, "weight":0.90, "muscle":0.45},
    "older":   {"gender":0.9, "age":0.85, "weight":0.60, "muscle":0.35},
}
fit_s = None
for name in ["lean", "average", "heavy", "older"]:
    skin = build_body(HS, BODIES[name])
    sd = torso_depth(skin)
    org = import_organs()
    od = torso_depth(org)
    if fit_s is None:                               # register once, against the leanest body
        fit_s = min(sd/od, 1.0) * 0.96 if od > 0 else 1.0
        log(f"register: lean skin torso-depth={sd:.3f} organ depth={od:.3f} -> organ DEPTH scale={fit_s:.3f}")
    org.data.transform(Matrix.Diagonal((1.0, fit_s, 1.0, 1.0)))   # depth-only fit, about origin
    skin.data.materials.clear(); skin.data.materials.append(skin_mat())
    org.data.materials.clear(); org.data.materials.append(organ_mat())
    side, front = setup_scene()
    log(f"{name}: skin torso-depth={sd:.3f}")
    render(side, os.path.join(RENDERS, f"param_{name}_side.png"))
    if name in ("lean", "heavy"):
        render(front, os.path.join(RENDERS, f"param_{name}_front.png"))
log("DONE")
