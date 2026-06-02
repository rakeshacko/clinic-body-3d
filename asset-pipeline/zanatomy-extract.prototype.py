import bpy, sys, math
from mathutils import Vector, Matrix

BLEND = "/tmp/zanat/Z-Anatomy/Startup.blend"
OUT = "/Users/rakeshverma/code/acko/clinic-body-3d/public/models"
TARGET_HEIGHT = 1.8

# (system id, source collection, tri budget, exclude-name-substrings for NC/irrelevant)
JOBS = [
    ("skeletal", "1: Skeletal system", 90000, []),
    ("nervous",  "7: Nervous system & Sense organs", 80000,
        # CC-BY-NC inner ear (Dundee) -> exclude before any commercial use
        ["cochlea","vestibul","semicircular","labyrinth","tympan","malleus",
         "incus","stapes","auditory","ampulla","spiral organ","eardrum","ossicle"]),
]
INCLUDE_TYPES = {'MESH', 'CURVE'}   # curves = nerves/vessels modelled as bevelled tubes

def log(*a): print("ZX:", *a, flush=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)

# Z-Anatomy ships with most collections disabled in the view layer; enable everything so
# bpy.ops selection/convert/join can see the geometry.
def enable_all(lc):
    lc.exclude = False
    lc.hide_viewport = False
    try: lc.collection.hide_viewport = False
    except Exception: pass
    for ch in lc.children:
        enable_all(ch)
enable_all(bpy.context.view_layer.layer_collection)
for o in bpy.data.objects:
    o.hide_viewport = False
    try: o.hide_set(False)
    except Exception: pass

def coll(name):
    return bpy.data.collections.get(name)

def mesh_objs(c, excludes):
    out=[]
    for o in c.all_objects:
        if o.type not in INCLUDE_TYPES: continue
        nm=o.name.lower()
        if any(x in nm for x in excludes): continue
        out.append(o)
    return out

# ---- global reference transform from the full skeleton (a whole-body proxy) ----
skel = coll("1: Skeletal system")
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for o in skel.all_objects:
    if o.type!='MESH': continue
    for cnr in o.bound_box:
        w=o.matrix_world @ Vector(cnr)
        for i in range(3):
            mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
ext=mx-mn
height=max(ext)              # Blender Z up
scale=TARGET_HEIGHT/height
center=(mn+mx)*0.5
REF = Matrix.Diagonal((scale,scale,scale,1.0)) @ Matrix.Translation(-center)
log(f"skeleton bounds ext={[round(e,2) for e in ext]} height={height:.2f} scale={scale:.4f} center={[round(c,2) for c in center]}")

def tri(o): return sum(max(0,len(p.vertices)-2) for p in o.data.polygons)

for sysid, collname, budget, excludes in JOBS:
    c=coll(collname)
    if not c: log("MISSING collection", collname); continue
    objs=mesh_objs(c, excludes)
    bpy.ops.object.select_all(action='DESELECT')
    n=0
    for o in objs:
        try:
            o.hide_set(False); o.hide_viewport=False; o.select_set(True); n+=1
        except Exception: pass
    if n==0: log("no objs", sysid); continue
    bpy.context.view_layer.objects.active = objs[0]
    # apply modifiers by converting to mesh, then join
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    obj=bpy.context.view_layer.objects.active
    raw=tri(obj)
    # apply global ref transform
    obj.matrix_world = REF @ obj.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # decimate to budget
    if raw>budget:
        m=obj.modifiers.new("d","DECIMATE"); m.ratio=budget/raw
        bpy.ops.object.modifier_apply(modifier=m.name)
    obj.name=obj.data.name=f"system_{sysid}"
    # bounds after transform
    mn2=Vector((1e9,)*3); mx2=Vector((-1e9,)*3)
    for v in obj.data.vertices:
        w=obj.matrix_world@v.co
        for i in range(3): mn2[i]=min(mn2[i],w[i]); mx2[i]=max(mx2[i],w[i])
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    path=f"{OUT}/system_{sysid}.glb"
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
        export_apply=True, export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6, export_yup=True)
    log(f"{sysid}: objs={n} raw={raw:,} -> final={tri(obj):,} "
        f"y[{mn2[2]:+.2f},{mx2[2]:+.2f}](Zup) -> {path}")
log("DONE")
