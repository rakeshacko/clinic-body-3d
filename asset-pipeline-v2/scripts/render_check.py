"""
render_check.py — offline coherence + fit check for the extracted core.

Loads every GLB in out/ together and renders FRONT and SIDE orthographic views.
The SIDE view is the one that matters: depth poke-through (an organ sticking out
the chest or back) is invisible head-on and only shows in profile (SPEC §5.5).

  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/render_check.py

Skin is rendered translucent, each system an opaque glowing colour, so any organ
escaping the skin silhouette is obvious. Outputs: renders/front.png, renders/side.png
"""
import bpy, os, glob, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
RENDERS = os.path.join(ROOT, "renders")
os.makedirs(RENDERS, exist_ok=True)

# system -> (rgb, emission_strength); skin handled separately
COLORS = {
    "cardiovascular": ((0.90, 0.18, 0.18), 1.4),
    "respiratory":    ((0.30, 0.80, 0.92), 1.2),
    "digestive":      ((0.95, 0.58, 0.18), 1.2),
    "endocrine":      ((0.88, 0.30, 0.85), 1.6),
    "urinary":        ((0.96, 0.86, 0.25), 1.4),
    "nervous":        ((0.45, 0.52, 0.96), 1.2),
    "skeletal":       ((0.92, 0.90, 0.82), 0.5),
}
SKIN_RGBA = (0.60, 0.85, 0.92, 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = False
scene.render.resolution_x = 900
scene.render.resolution_y = 1350
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("w"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.045, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

def make_skin():
    m = bpy.data.materials.new("skin"); m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = SKIN_RGBA
    bsdf.inputs["Roughness"].default_value = 0.35
    if "Alpha" in bsdf.inputs: bsdf.inputs["Alpha"].default_value = 0.16
    m.blend_method = "BLEND"
    m.show_transparent_back = False
    return m

def make_organ(rgb, emit):
    m = bpy.data.materials.new("organ"); m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    if "Emission Color" in bsdf.inputs: bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    elif "Emission" in bsdf.inputs: bsdf.inputs["Emission"].default_value = (*rgb, 1.0)
    if "Emission Strength" in bsdf.inputs: bsdf.inputs["Emission Strength"].default_value = emit
    return m

def assign(objs, mat):
    for o in objs:
        if o.type != "MESH": continue
        o.data.materials.clear(); o.data.materials.append(mat)

# import each GLB, material by filename
for f in sorted(glob.glob(os.path.join(OUT, "*.glb"))):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    base = os.path.basename(f)
    if base == "body_shell.glb":
        assign(new, make_skin())
    else:
        sysid = base.replace("system_", "").replace(".glb", "")
        rgb, emit = COLORS.get(sysid, ((0.8, 0.8, 0.8), 1.0))
        assign(new, make_organ(rgb, emit))
print("RENDER: imported", len([o for o in bpy.data.objects if o.type == "MESH"]), "meshes", flush=True)

# lighting: key from front-top, fill from side
for loc, energy in [((0, -4, 3), 3.0), ((4, -2, 1), 1.5), ((-3, 3, 2), 1.0)]:
    l = bpy.data.lights.new("L", "SUN"); l.energy = energy
    ob = bpy.data.objects.new("L", l); scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

def camera(name, loc):
    cd = bpy.data.cameras.new(name); cd.type = "ORTHO"; cd.ortho_scale = 2.05
    ob = bpy.data.objects.new(name, cd); scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0.02)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob

# anterior = -Y after gltf round-trip; up = +Z
front = camera("front", (0, -4.0, 0.0))   # looks +Y at the body's front
side = camera("side", (4.0, 0.0, 0.0))    # looks -X across the body (profile)

for cam, name in [(front, "front"), (side, "side")]:
    scene.camera = cam
    scene.render.filepath = os.path.join(RENDERS, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDER: wrote", name + ".png", flush=True)
print("RENDER: DONE", flush=True)
