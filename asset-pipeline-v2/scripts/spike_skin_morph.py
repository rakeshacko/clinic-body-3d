"""
spike_skin_morph.py — the real de-risk (SPEC's 'still unsolved' body-type problem).

Tests whether body type can be a PROCEDURAL outward-only morph on the one coherent
Z-Anatomy skin, instead of a foreign MakeHuman body (which needs the depth-inflate
hack) or a hand-sculpted blendshape (hard on patchwork topology).

Idea: displace each skin vertex radially outward from the vertical body axis,
weighted by a belly-centred vertical profile (+ a forward belly bias, + limb damping).
Outward-only => organs can never escape. Topology-free => works on the 248-patch skin.

Renders the SIDE profile (the decisive view) at increasing 'weight' with the fixed
Z-Anatomy core inside, so we can judge realism AND containment in one shot.

  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/spike_skin_morph.py
"""
import bpy, os, glob, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
RENDERS = os.path.join(ROOT, "renders")
os.makedirs(RENDERS, exist_ok=True)

COLORS = {
    "cardiovascular": ((0.90, 0.18, 0.18), 1.4), "respiratory": ((0.30, 0.80, 0.92), 1.2),
    "digestive": ((0.95, 0.58, 0.18), 1.2), "endocrine": ((0.88, 0.30, 0.85), 1.6),
    "urinary": ((0.96, 0.86, 0.25), 1.4), "nervous": ((0.45, 0.52, 0.96), 1.2),
    "skeletal": ((0.92, 0.90, 0.82), 0.5),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 820, 1300
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.045, 1.0)

def organ_mat(rgb, emit):
    m = bpy.data.materials.new("o"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    if "Emission Color" in b.inputs: b.inputs["Emission Color"].default_value = (*rgb, 1.0)
    if "Emission Strength" in b.inputs: b.inputs["Emission Strength"].default_value = emit
    return m

def skin_mat():
    m = bpy.data.materials.new("skin"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.60, 0.85, 0.92, 1.0)
    b.inputs["Roughness"].default_value = 0.35
    if "Alpha" in b.inputs: b.inputs["Alpha"].default_value = 0.17
    m.blend_method = "BLEND"; m.show_transparent_back = False
    return m

skin_obj = None
for f in sorted(glob.glob(os.path.join(OUT, "*.glb"))):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    base = os.path.basename(f)
    if base == "body_shell.glb":
        for o in new: o.data.materials.clear(); o.data.materials.append(skin_mat())
        skin_obj = new[0] if new else None
    else:
        sysid = base.replace("system_", "").replace(".glb", "")
        rgb, emit = COLORS.get(sysid, ((0.8,)*3, 1.0))
        mat = organ_mat(rgb, emit)
        for o in new: o.data.materials.clear(); o.data.materials.append(mat)

assert skin_obj, "no skin"

# ---- precompute per-vertex outward offset (for weight=1) in the skin's local space ----
# Imported gltf is Z-up in Blender; body centred x≈0,y≈0, z∈[-0.9,0.9], anterior -Y.
mw = skin_obj.matrix_world
basis = [v.co.copy() for v in skin_obj.data.vertices]

def vprofile(z):
    # belly-centred bulge (peak ~navel) + smaller hip/seat baseline; fades at head/shins
    belly = math.exp(-((z - 0.03) / 0.26) ** 2)
    base = 0.35 * math.exp(-((z - (-0.02)) / 0.5) ** 2)
    head = 1.0 - smooth(z, 0.55, 0.78)          # fade above mid-chest->head
    shins = smooth(z, -0.78, -0.45)             # fade below knee
    return max(0.0, (belly + base)) * head * shins

def smooth(x, a, b):
    if x <= a: return 0.0
    if x >= b: return 1.0
    t = (x - a) / (b - a); return t * t * (3 - 2 * t)

offsets = []
for co in basis:
    w = mw @ co                                  # world (== local here, identity-ish)
    r = Vector((w.x, w.y, 0.0))
    rl = r.length
    direction = r / rl if rl > 1e-5 else Vector((0, -1, 0))
    p = vprofile(w.z)
    # limb damp: reduce on arms/hands (|x| large)
    damp = 1.0 - 0.7 * smooth(abs(w.x), 0.20, 0.32)
    disp = direction * (p * damp)
    disp.y += -0.45 * p * damp                   # belly protrudes forward (anterior = -Y)
    offsets.append(disp)

def set_weight(amt):
    me = skin_obj.data
    for i, v in enumerate(me.vertices):
        v.co = basis[i] + offsets[i] * amt
    me.update()

# lighting
for loc, e in [((0, -4, 3), 3.0), ((4, -2, 1), 1.5), ((-3, 3, 2), 1.0)]:
    l = bpy.data.lights.new("L", "SUN"); l.energy = e
    ob = bpy.data.objects.new("L", l); scene.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

def camera(loc):
    cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 2.05
    ob = bpy.data.objects.new("c", cd); scene.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0.02)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob
side = camera((4.0, 0.0, 0.0))
front = camera((0, -4.0, 0.0))

def render(cam, path):
    scene.camera = cam; scene.render.filepath = path
    bpy.ops.render.render(write_still=True); print("SPIKE: wrote", os.path.basename(path), flush=True)

# weight sweep: 0 (skin hugs core) -> heavier (outward only)
for amt, tag in [(0.0, "lean"), (0.085, "mid"), (0.16, "heavy")]:
    set_weight(amt)
    render(side, os.path.join(RENDERS, f"morph_{tag}_side.png"))
set_weight(0.16); render(front, os.path.join(RENDERS, "morph_heavy_front.png"))
print("SPIKE: DONE", flush=True)
