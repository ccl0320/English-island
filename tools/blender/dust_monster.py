"""Build the Dust monster (Island 1, stage 1) as a low-poly GLB with animations.

Run headless:  python3 tools/blender/dust_monster.py models/m11-dust.glb
(needs `pip install bpy`, Blender as a Python module) or inside Blender:
blender -b -P tools/blender/dust_monster.py -- models/m11-dust.glb

Conventions the game relies on (see MODELS in index.html):
- +Z faces the camera/player, feet on y=0, about 1 unit tall.
- Materials are named; the game greys them out and washes the colour back in.
- Meshes named face_grumpy / face_happy are toggled by the game.
- Animations (NLA tracks): idle, walk, laugh, hurt, color_up.
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector

out = sys.argv[-1] if sys.argv[-1].endswith('.glb') else 'm11-dust.glb'
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = 30

def mat(name, rgb, rough=.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    return m

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)

M = {k: mat(k, srgb(v), r) for k, v, r in [
    ('fluff', '#F7A8BC', .9), ('fluff_dark', '#E9849F', .9), ('feet', '#F08AA6', .7),
    ('eye', '#3A2420', .35), ('mouth', '#C2405A', .6), ('cheek', '#FF8FA0', .9), ('white', '#FFFFFF', .4)]}

def link(o):
    scn.collection.objects.link(o); return o

def ico(name, r, loc, sub=2, m=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc
    if m: me.materials.append(m)
    return o

def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True

# ---- body: a cloud of puffs merged into one surface ----
puffs = [ico('core', .42, (0, .52, 0), 3)]
for i in range(34):
    th = random.uniform(0, 2 * math.pi); ph = math.acos(random.uniform(-.75, .95))
    d = .40
    p = Vector((math.sin(ph) * math.cos(th) * d, .52 + math.cos(ph) * d * .92, math.sin(ph) * math.sin(th) * d))
    if p.z > .3 and abs(p.x) < .3 and p.y > .3:  # keep the face area smooth
        continue
    puffs.append(ico('puff%d' % i, random.uniform(.15, .23), p, 2))
for o in puffs: o.select_set(True)
bpy.context.view_layer.objects.active = puffs[0]
bpy.ops.object.join()
body = puffs[0]; body.name = 'body'
rm = body.modifiers.new('remesh', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = .035
dc = body.modifiers.new('dec', 'DECIMATE'); dc.ratio = .1
apply_all(body)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)  # local == world from here on
body.data.materials.append(M['fluff']); body.data.materials.append(M['fluff_dark'])
for p in body.data.polygons:   # darker fluff underneath, a cheap baked-AO look
    p.material_index = 1 if p.center.y < .28 else 0
smooth(body)
# Blender is Z-up; we build in Y-up numbers then rotate at the end via root.

# ---- curly tuft on top ----
cu = bpy.data.curves.new('tuft', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .055; cu.bevel_resolution = 2
cu.resolution_u = 6
sp = cu.splines.new('BEZIER'); pts = [(0, .88, 0), (.02, 1.06, 0), (.16, 1.14, 0), (.24, 1.06, 0)]
sp.bezier_points.add(len(pts) - 1)
for bp, p in zip(sp.bezier_points, pts):
    bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
sp.bezier_points[-1].radius = .5
tuft = link(bpy.data.objects.new('tuft', cu))
bpy.context.view_layer.objects.active = tuft; tuft.select_set(True)
bpy.ops.object.convert(target='MESH'); tuft = bpy.context.view_layer.objects.active
tuft.data.materials.append(M['fluff']); smooth(tuft)

# ---- feet ----
feet = []
for s in (-1, 1):
    f = ico('foot_' + ('L' if s < 0 else 'R'), .11, (s * .2, .07, .12), 2, M['feet'])
    f.scale = (1, .65, 1.25); smooth(f); feet.append(f)

# ---- faces (front = +z in our Y-up numbers) ----
def eye(name, x, y, z, m, sx=.07, sy=.09, sz=.035):
    e = ico(name, 1, (x, y, z), 2, m); e.scale = (sx, sy, sz); smooth(e); return e

def arc(name, x, y, z, w, up, m, th=.026):
    """a little curved bar: smile (up=False) or closed happy eye / eyebrow."""
    c = bpy.data.curves.new(name, 'CURVE'); c.dimensions = '3D'; c.bevel_depth = th; c.bevel_resolution = 1
    s = c.splines.new('BEZIER'); s.bezier_points.add(2)
    k = .06 if up else -.06
    for bp, p in zip(s.bezier_points, [(x - w, y, z), (x, y + k, z + .015), (x + w, y, z)]):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = link(bpy.data.objects.new(name, c))
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH'); o = bpy.context.view_layer.objects.active
    o.data.materials.append(m); return o

def join(name, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name; return o

from mathutils.bvhtree import BVHTree
_bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
def fz(x, y):
    """z of the body's front surface at (x, y), so face parts sit on the fluff."""
    hit = _bvh.ray_cast(Vector((x, y, 3)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] else .8
grumpy = join('face_grumpy', [
    eye('eL', -.15, .6, fz(-.15, .6) - .012, M['eye']), eye('eR', .15, .6, fz(.15, .6) - .012, M['eye']),
    eye('gL', -.135, .62, fz(-.135, .62) + .012, M['white'], .024, .027, .012), eye('gR', .165, .62, fz(.165, .62) + .012, M['white'], .024, .027, .012),
    arc('browL', -.16, .73, fz(-.16, .73) - .005, .07, False, M['eye'], .018), arc('browR', .16, .73, fz(.16, .73) - .005, .07, False, M['eye'], .018),
    arc('frown', 0, .42, fz(0, .42) - .005, .07, True, M['eye'], .02)])
# tilt brows inward to look grumpy
happy = join('face_happy', [
    arc('hL', -.15, .6, fz(-.15, .6) - .005, .08, True, M['eye']), arc('hR', .15, .6, fz(.15, .6) - .005, .08, True, M['eye']),
    eye('mouth', 0, .43, fz(0, .43) - .01, M['mouth'], .11, .075, .03),
    eye('ckL', -.27, .49, fz(-.27, .49) - .008, M['cheek'], .08, .05, .02), eye('ckR', .27, .49, fz(.27, .49) - .008, M['cheek'], .08, .05, .02)])
for o in (grumpy, happy):
    smooth(o)

# convert every object from our Y-up numbers to Blender Z-up: (x, y, z) -> (x, -z, y)
def yup_to_zup(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for v in o.data.vertices:
        x, y, z = v.co; v.co = (x, -z, y)
    o.data.update()
parts = [body, tuft, grumpy, happy] + feet
for o in parts: yup_to_zup(o)

# ---- armature: root > body > tuft ; root > foot_L / foot_R ----
ad = bpy.data.armatures.new('rig'); rig = link(bpy.data.objects.new('dust_rig', ad))
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def bone(n, h, t, parent=None):
    b = ad.edit_bones.new(n); b.head = h; b.tail = t
    if parent: b.parent = ad.edit_bones[parent]
    return b
bone('root', (0, 0, 0), (0, 0, .2))
bone('body', (0, 0, .1), (0, 0, .6), 'root')
bone('tuft', (0, 0, .9), (0, 0, 1.05), 'body')
bone('foot_L', (-.2, -.12, .07), (-.2, -.12, .2), 'root')
bone('foot_R', (.2, -.12, .07), (.2, -.12, .2), 'root')
bpy.ops.object.mode_set(mode='OBJECT')

def parent_to_bone(o, bn):
    mw = o.matrix_world.copy()
    o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bn
    o.matrix_world = mw
for o, bn in [(body, 'body'), (grumpy, 'body'), (happy, 'body'), (tuft, 'tuft'), (feet[0], 'foot_L'), (feet[1], 'foot_R')]:
    parent_to_bone(o, bn)

# ---- animations ----
pb = rig.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
rig.animation_data_create()

def key(t, **kw):
    for spec, v in kw.items():
        bn, prop = spec.split('__')
        b = pb[bn]
        if prop == 'loc': b.location = v
        elif prop == 'rot': b.rotation_euler = [math.radians(a) for a in v]
        elif prop == 'scl': b.scale = v
        b.keyframe_insert({'loc': 'location', 'rot': 'rotation_euler', 'scl': 'scale'}[prop], frame=t)

def clip(name, frames):
    act = bpy.data.actions.new(name); rig.animation_data.action = act
    for b in pb:
        b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)
    for t, kw in frames:
        key(t, **kw)
    tr = rig.animation_data.nla_tracks.new(); tr.name = name
    tr.strips.new(name, int(frames[0][0]), act)
    rig.animation_data.action = None

Z = (0, 0, 0); ONE = (1, 1, 1)
# note: pose-space of a bone pointing +Z: local Y is up the bone. scale (x, y, z) -> y stretches tall.
clip('idle', [(1, dict(body__scl=ONE, tuft__rot=(0, 0, 8))),
              (15, dict(body__scl=(1.05, .94, 1.05), tuft__rot=(0, 0, -8))),
              (30, dict(body__scl=ONE, tuft__rot=(0, 0, 8)))])
clip('walk', [(1, dict(root__loc=Z, foot_L__loc=(0, .06, 0), foot_R__loc=Z, body__rot=(0, 0, 4))),
              (8, dict(root__loc=(0, .05, 0), foot_L__loc=Z, foot_R__loc=(0, .06, 0), body__rot=(0, 0, -4))),
              (16, dict(root__loc=Z, foot_L__loc=(0, .06, 0), foot_R__loc=Z, body__rot=(0, 0, 4)))])
clip('laugh', [(1, dict(root__loc=Z, body__rot=(0, 0, 0), body__scl=ONE)),
               (5, dict(root__loc=(0, .18, 0), body__rot=(0, 0, 10), body__scl=(.95, 1.08, .95))),
               (10, dict(root__loc=Z, body__rot=(0, 0, -10), body__scl=(1.08, .92, 1.08))),
               (15, dict(root__loc=(0, .18, 0), body__rot=(0, 0, 10), body__scl=(.95, 1.08, .95))),
               (20, dict(root__loc=Z, body__rot=(0, 0, 0), body__scl=ONE))])
clip('hurt', [(1, dict(body__rot=Z, body__scl=ONE, root__loc=Z)),
              (4, dict(body__rot=(-18, 0, 0), body__scl=(1.15, .8, 1.15), root__loc=(0, 0, -.12))),
              (10, dict(body__rot=(6, 0, 0), body__scl=(.95, 1.06, .95), root__loc=(0, 0, -.08))),
              (16, dict(body__rot=Z, body__scl=ONE, root__loc=Z))])
clip('color_up', [(1, dict(root__loc=Z, root__rot=Z, body__scl=ONE)),
                  (6, dict(root__loc=Z, root__rot=Z, body__scl=(1.15, .8, 1.15))),
                  (14, dict(root__loc=(0, .55, 0), root__rot=(0, 180, 0), body__scl=(.9, 1.15, .9))),
                  (22, dict(root__loc=(0, 0, 0), root__rot=(0, 360, 0), body__scl=(1.12, .86, 1.12))),
                  (28, dict(root__loc=Z, root__rot=(0, 360, 0), body__scl=ONE))])
for b in pb:
    b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)

tris = sum(len(o.data.polygons) for o in scn.objects if o.type == 'MESH')
print('faces', tris)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animation_mode='NLA_TRACKS',
                          export_apply=True, export_yup=True, export_def_bones=False)
print('wrote', out)
