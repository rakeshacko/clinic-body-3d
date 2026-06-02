"""
bake_morph.py — bake the procedural outward body-type morph into the skin GLB
as a real 'weight' morph target (shape key), so a runtime (three.js / drei
morphTargetInfluences) can scrub lean<->heavy live.

Same displacement field as spike_skin_morph.py, baked at MAX_WEIGHT into a shape
key; influence 0..1 then interpolates skin-hugging-core -> heavy.

  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/bake_morph.py
Out: out/body_shell_morph.glb  (no Draco: morph targets + Draco can be flaky in loaders)
"""
import bpy, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
MAX_WEIGHT = 0.16

bpy.ops.wm.read_factory_settings(use_empty=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, "body_shell.glb"))
skin = [o for o in bpy.data.objects if o not in before and o.type == "MESH"][0]

def smooth(x, a, b):
    if x <= a: return 0.0
    if x >= b: return 1.0
    t = (x - a) / (b - a); return t * t * (3 - 2 * t)

def vprofile(z):
    belly = math.exp(-((z - 0.03) / 0.26) ** 2)
    base = 0.35 * math.exp(-((z - (-0.02)) / 0.5) ** 2)
    head = 1.0 - smooth(z, 0.55, 0.78)
    shins = smooth(z, -0.78, -0.45)
    return max(0.0, (belly + base)) * head * shins

mw = skin.matrix_world
# basis + 'weight' shape keys
skin.shape_key_add(name="Basis", from_mix=False)
key = skin.shape_key_add(name="weight", from_mix=False)
for i, v in enumerate(skin.data.vertices):
    w = mw @ v.co
    r = Vector((w.x, w.y, 0.0)); rl = r.length
    direction = r / rl if rl > 1e-5 else Vector((0, -1, 0))
    p = vprofile(w.z)
    damp = 1.0 - 0.7 * smooth(abs(w.x), 0.20, 0.32)
    disp = direction * (p * damp)
    disp.y += -0.45 * p * damp
    key.data[i].co = v.co + disp * MAX_WEIGHT
key.value = 0.0

bpy.ops.object.select_all(action="DESELECT")
skin.select_set(True); bpy.context.view_layer.objects.active = skin
path = os.path.join(OUT, "body_shell_morph.glb")
bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
    export_morph=True, export_draco_mesh_compression_enable=False, export_yup=True)
print("BAKE: wrote", path, "verts", len(skin.data.vertices), flush=True)
print("BAKE: DONE", flush=True)
