"""Build the English Island characters as low-poly GLB files.

    pip install bpy                     # Blender as a Python module (5.x)
    python3 tools/blender/build_models.py models/          # all models
    python3 tools/blender/build_models.py models/ m22-sheep hero-girl   # some

The Dust monster has its own older script (dust_monster.py).

Conventions the game relies on (MODELS / modelMonster / modelHero in index.html):
- Front is glTF +Z, feet on y=0. Size does not matter: the game scales by height.
- Materials are named; monsters are greyed out by the game and washed back to colour.
- Monster meshes face_grumpy / face_happy are toggled by the game.
- Monster clips: idle, walk, laugh, hurt, color_up.   Hero clips: idle, walk, cast, cheer, hurt.
  Pip clips: idle, flap.
- Parts are rigidly parented to bones (no skinning): cheap on phones.

Inside this file every position is written Y-up like the game: (x, up, front).
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finish as FIN

C = bpy.context
TAU = math.pi * 2


def P(x, y, z):
    """game/Y-up (x, up, front) -> Blender Z-up."""
    return Vector((x, -z, y))


def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


class Model:
    def __init__(self, name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        C.scene.render.fps = 30
        self.name = name; self.mats = {}; self.parts = []  # (obj, bone)
        self.bones = []
        self.fin = None  # finishing pass: {'details': {mat: (kind, strength)}, 'rough': {mat: r}}

    # ---------- materials ----------
    def m(self, name, hexc=None, rough=.8):
        if name in self.mats: return self.mats[name]
        mt = bpy.data.materials.new(name); mt.use_nodes = True
        b = mt.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*srgb(hexc), 1)
        b.inputs['Roughness'].default_value = rough
        self.mats[name] = mt; return mt

    # ---------- mesh helpers (all take Y-up numbers) ----------
    def _obj(self, name, bm, mat, bone, smooth=True):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); C.scene.collection.objects.link(o)
        if mat is not None:
            me.materials.append(mat)
        for p in me.polygons: p.use_smooth = smooth
        if bone: self.parts.append((o, bone))
        return o

    def ball(self, name, r, pos, mat, bone='body', scale=(1, 1, 1), sub=2, smooth=True):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
        sx, sy, sz = scale
        for v in bm.verts:
            x, y, z = v.co.x * r * sx, v.co.z * r * sy, -v.co.y * r * sz  # icosphere is symmetric; map to y-up scale
            v.co = P(pos[0] + x, pos[1] + y, pos[2] + z)
        return self._obj(name, bm, mat, bone, smooth)

    def lathe(self, name, prof, mat, bone='body', seg=16, pos=(0, 0, 0), axis='y', smooth=True, cap=True):
        """prof = [(radius, height), ...] bottom to top, spun around the up axis (or x / z)."""
        bm = bmesh.new(); rings = []
        for r, h in prof:
            ring = []
            for i in range(seg):
                a = i / seg * TAU; x, z = math.cos(a) * r, math.sin(a) * r
                if axis == 'y': q = (x, h, z)
                elif axis == 'x': q = (h, x, z)
                else: q = (x, z, h)
                ring.append(bm.verts.new(P(pos[0] + q[0], pos[1] + q[1], pos[2] + q[2])))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                bm.faces.new((a[i], a[j], b[j], b[i]))
        if cap:
            for ring, flip in ((rings[0], True), (rings[-1], False)):
                if len(set(tuple(v.co) for v in ring)) > 2:
                    f = bm.faces.new(ring[::-1] if flip else ring)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._obj(name, bm, mat, bone, smooth)

    def cyl(self, name, r, h, pos, mat, bone='body', seg=12, axis='y', r2=None):
        r2 = r if r2 is None else r2
        return self.lathe(name, [(r, -h / 2), (r2, h / 2)], mat, bone, seg, pos, axis, smooth=False)

    def rbox(self, name, size, pos, mat, bone='body', bevel=.04, segs=2):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=bevel, segments=segs, affect='EDGES') if bevel else None
        w, h, d = size
        for v in bm.verts:
            x, y, z = v.co.x, v.co.z, -v.co.y
            # keep bevel radius roughly constant: scale the flat part only
            v.co = P(pos[0] + x * w, pos[1] + y * h, pos[2] + z * d)
        return self._obj(name, bm, mat, bone, smooth=True)

    def tube(self, name, pts, rad, mat, bone='body', taper=None, res=6, bev=2):
        cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = rad
        cu.bevel_resolution = bev; cu.resolution_u = res; cu.use_fill_caps = True
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for i, (bp, p) in enumerate(zip(sp.bezier_points, pts)):
            bp.co = P(*p); bp.handle_left_type = bp.handle_right_type = 'AUTO'
            if taper: bp.radius = taper[i]
        o = bpy.data.objects.new(name, cu); C.scene.collection.objects.link(o)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); C.view_layer.objects.active = o
        bpy.ops.object.convert(target='MESH'); o = C.view_layer.objects.active
        o.data.materials.clear(); o.data.materials.append(mat)
        for p in o.data.polygons: p.use_smooth = True
        if bone: self.parts.append((o, bone))
        return o

    def flat(self, name, pts2d, depth, pos, mat, bone='body', plane='xy', rot_y=0):
        """an extruded outline (x, y) in the front plane, `depth` thick."""
        bm = bmesh.new(); vs = []
        for x, y in pts2d:
            vs.append(bm.verts.new((x, y, 0)))
        f = bm.faces.new(vs)
        ex = bmesh.ops.extrude_face_region(bm, geom=[f])
        for v in [e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)]:
            v.co.z += depth
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ca, sa = math.cos(rot_y), math.sin(rot_y)
        for v in bm.verts:
            x, y, z = v.co.x, v.co.y, v.co.z - depth / 2
            if plane == 'xz': x, y, z = x, z, y
            x, z = x * ca + z * sa, -x * sa + z * ca
            v.co = P(pos[0] + x, pos[1] + y, pos[2] + z)
        return self._obj(name, bm, mat, bone, smooth=False)

    def remesh(self, o, voxel=.035, ratio=.12):
        rm = o.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel
        dc = o.modifiers.new('dc', 'DECIMATE'); dc.ratio = ratio
        C.view_layer.objects.active = o
        for md in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
        for p in o.data.polygons: p.use_smooth = True
        return o

    def join(self, name, objs, bone='body'):
        objs = [o for o in objs if o]
        for o in objs:
            self.parts = [(a, b) for a, b in self.parts if a != o]
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        C.view_layer.objects.active = objs[0]; bpy.ops.object.join()
        o = C.view_layer.objects.active; o.name = name; o.data.name = name
        if bone: self.parts.append((o, bone))
        return o

    def surface(self, o):
        """returns fz(x, y): the front surface (+z) of o at (x, y)."""
        dg = C.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(o, dg)
        mw = o.matrix_world.copy()
        def fz(x, y, start=3):
            hit = bvh.ray_cast(P(x, y, start), P(0, 0, -1) - P(0, 0, 0))
            if hit[0] is None: return .3
            w = mw @ hit[0]
            return -w.y
        return fz

    def faces(self, fz, cx, cy, s=1., eye='#3A2420', mouth='#C2405A', cheek='#FF8FA0', mood='grumpy',
              sleepy=False, spread=.15, tongue=False):
        """adds face_grumpy and face_happy (both on the body bone)."""
        E = self.m('eye', eye, .35); W = self.m('white', '#FFFFFF', .4)
        Mo = self.m('mouth', mouth, .6); Ck = self.m('cheek', cheek, .9)
        dx = spread * s
        def on(x, y, d=0): return (x, y, fz(x, y) + d)
        def arc(nm, x, y, w, up, th=.026 * s, lift=0):
            k = (.06 if up else -.06) * s
            z0 = fz(x - w, y) - .005; z1 = fz(x, y + k) + .01; z2 = fz(x + w, y) - .005
            return self.tube(nm, [(x - w, y, z0), (x, y + k, z1), (x + w, y, z2)], th, E, None, res=4, bev=1)
        def brow(nm, x, y, w, inward):
            a = (x - w, y + (.03 * s if inward < 0 else -.02 * s)); b = (x + w, y + (.03 * s if inward > 0 else -.02 * s))
            return self.tube(nm, [(a[0], a[1], fz(*a) - .003), (b[0], b[1], fz(*b) - .003)], .02 * s, E, None, res=1, bev=1)
        g = []
        if sleepy:
            for sx in (-1, 1):
                x = sx * dx
                g.append(self.ball('w' + str(sx), .075 * s, on(x, cy, -.03 * s), W, None, (1, .9, .5)))
                g.append(self.ball('p' + str(sx), .035 * s, on(x, cy - .01 * s, .01 * s), E, None, (1, 1, .6)))
                g.append(self.ball('lid' + str(sx), .078 * s, on(x, cy + .015 * s, -.02 * s), self.m('lid', '#8C8C8C'), None, (1.05, .55, .55)))
        else:
            for sx in (-1, 1):
                x = sx * dx
                g.append(self.ball('e' + str(sx), .07 * s, on(x, cy, -.018 * s), E, None, (1, 1.25, .5)))
                g.append(self.ball('g' + str(sx), .024 * s, on(x + .015 * s, cy + .03 * s, .006 * s), W, None, (1, 1.1, .5)))
                g.append(brow('b' + str(sx), x, cy + .14 * s, .065 * s, -sx))
        g.append(arc('frown', cx, cy - .17 * s, .075 * s, True))
        if tongue:
            g.append(self.ball('tg', .05 * s, on(cx + .02 * s, cy - .22 * s, -.01 * s), Mo, None, (1, 1.2, .5)))
        self.join('face_grumpy', g)
        h = [arc('hL', -dx, cy, .08 * s, True), arc('hR', dx, cy, .08 * s, True),
             self.ball('mo', .1 * s, on(cx, cy - .16 * s, -.02 * s), Mo, None, (1.1, .8, .35)),
             self.ball('ckL', .075 * s, on(-dx - .11 * s, cy - .1 * s, -.012 * s), Ck, None, (1, .6, .3)),
             self.ball('ckR', .075 * s, on(dx + .11 * s, cy - .1 * s, -.012 * s), Ck, None, (1, .6, .3))]
        self.join('face_happy', h)

    # ---------- rig + animation ----------
    def rig(self, bones):
        """bones: [(name, head(yup), parent)]; every bone points up, 0.15 long."""
        ad = bpy.data.armatures.new('rig'); rig = bpy.data.objects.new(self.name + '_rig', ad)
        C.scene.collection.objects.link(rig); C.view_layer.objects.active = rig
        bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for n, h, par in bones:
            b = ad.edit_bones.new(n); b.head = P(*h); b.tail = P(h[0], h[1] + .15, h[2])
            if par: b.parent = ad.edit_bones[par]
        bpy.ops.object.mode_set(mode='OBJECT')
        self.r = rig
        for b in rig.pose.bones: b.rotation_mode = 'XYZ'
        rig.animation_data_create()
        # merge parts per bone into one mesh (fewer draw calls)
        by = {}
        for o, bn in self.parts: by.setdefault(bn, []).append(o)
        for bn, objs in by.items():
            keep = [o for o in objs if o.name.startswith('face_')]
            rest = [o for o in objs if o not in keep]
            if len(rest) > 1:
                bpy.ops.object.select_all(action='DESELECT')
                for o in rest: o.select_set(True)
                C.view_layer.objects.active = rest[0]; bpy.ops.object.join()
                rest = [C.view_layer.objects.active]; rest[0].name = bn + '_mesh'
            for o in rest + keep:
                mw = o.matrix_world.copy(); o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bn; o.matrix_world = mw
        return rig

    def clip(self, name, frames):
        """frames: [(frame, {'bone.loc': (x,up,front), 'bone.rot': (deg about x, y(up), z(front)), 'bone.scl': (x,up,front)})].
        Bones point up with roll 0, so bone-local X, Y, Z are exactly game x, up, front."""
        pb = self.r.pose.bones; act = bpy.data.actions.new(name); self.r.animation_data.action = act
        for b in pb: b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)
        for t, kw in frames:
            for spec, v in kw.items():
                bn, prop = spec.split('.'); b = pb[bn]
                if prop == 'loc':
                    b.location = (v[0], v[1], v[2]); b.keyframe_insert('location', frame=t)
                elif prop == 'rot':
                    b.rotation_euler = [math.radians(a) for a in v]; b.keyframe_insert('rotation_euler', frame=t)
                else:
                    b.scale = (v[0], v[1], v[2]); b.keyframe_insert('scale', frame=t)
        tr = self.r.animation_data.nla_tracks.new(); tr.name = name
        tr.strips.new(name, int(frames[0][0]), act); self.r.animation_data.action = None

    def export(self, path):
        for b in self.r.pose.bones: b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)
        C.view_layer.update()
        meshes = [o for o in C.scene.objects if o.type == 'MESH']
        n = sum(len(o.data.polygons) for o in meshes)
        if self.fin is not None:
            size = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
            rough = dict(FACE_ROUGH); rough.update(self.fin.get('rough', {}))
            FIN.finish(meshes, self.mats, size, self.fin.get('details', {}), rough, self.fin.get('ao', .75), tiles=self.fin.get('tiles', 6),
                       occluders=[o for o in meshes if not o.name.startswith('face_')])
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_animation_mode='NLA_TRACKS',
                                  export_apply=True, export_yup=True, export_def_bones=False, **FIN.GLTF_KW)
        FIN.slim_glb(path)
        print('%-14s %5d faces %6.1f KB' % (self.name, n, os.path.getsize(path) / 1024))


# glossy, wet-looking eyes and mouths on every model
FACE_ROUGH = {'eye': .12, 'white': .18, 'iris': .15, 'mouth': .45, 'tongue': .4, 'shine': .1, 'drop': .05}


# ======================= monsters =======================
MON_BONES = lambda top=1.0, arm=(.4, .5), foot=(.2, .07): [
    ('root', (0, 0, 0), None), ('body', (0, .1, 0), 'root'), ('top', (0, top, 0), 'body'),
    ('arm_L', (-arm[0], arm[1], 0), 'body'), ('arm_R', (arm[0], arm[1], 0), 'body'),
    ('foot_L', (-foot[0], foot[1], .1), 'root'), ('foot_R', (foot[0], foot[1], .1), 'root')]
Z = (0, 0, 0); ONE = (1, 1, 1)


def monster_clips(M, float_=False, arms=12):
    """the same five clips as the Dust monster, plus arm waves. float_: no feet, hovers."""
    f = .08 if float_ else 0
    M.clip('idle', [(1, {'body.scl': ONE, 'top.rot': (0, 0, 8), 'root.loc': (0, f, 0), 'arm_L.rot': (0, 0, arms), 'arm_R.rot': (0, 0, -arms)}),
                    (15, {'body.scl': (1.04, .95, 1.04), 'top.rot': (0, 0, -8), 'root.loc': (0, f * 2.2, 0), 'arm_L.rot': (0, 0, -arms), 'arm_R.rot': (0, 0, arms)}),
                    (30, {'body.scl': ONE, 'top.rot': (0, 0, 8), 'root.loc': (0, f, 0), 'arm_L.rot': (0, 0, arms), 'arm_R.rot': (0, 0, -arms)})])
    M.clip('walk', [(1, {'root.loc': (0, f, 0), 'foot_L.loc': (0, .06, 0), 'foot_R.loc': Z, 'body.rot': (0, 0, 4), 'arm_L.rot': (25, 0, 0), 'arm_R.rot': (-25, 0, 0)}),
                    (8, {'root.loc': (0, f + .05, 0), 'foot_L.loc': Z, 'foot_R.loc': (0, .06, 0), 'body.rot': (0, 0, -4), 'arm_L.rot': (-25, 0, 0), 'arm_R.rot': (25, 0, 0)}),
                    (16, {'root.loc': (0, f, 0), 'foot_L.loc': (0, .06, 0), 'foot_R.loc': Z, 'body.rot': (0, 0, 4), 'arm_L.rot': (25, 0, 0), 'arm_R.rot': (-25, 0, 0)})])
    up = {'arm_L.rot': (0, 0, -50), 'arm_R.rot': (0, 0, 50)}
    M.clip('laugh', [(1, {'root.loc': (0, f, 0), 'body.rot': Z, 'body.scl': ONE, 'arm_L.rot': Z, 'arm_R.rot': Z}),
                     (5, {'root.loc': (0, f + .18, 0), 'body.rot': (0, 0, 10), 'body.scl': (.95, 1.08, .95), **up}),
                     (10, {'root.loc': (0, f, 0), 'body.rot': (0, 0, -10), 'body.scl': (1.08, .92, 1.08), 'arm_L.rot': Z, 'arm_R.rot': Z}),
                     (15, {'root.loc': (0, f + .18, 0), 'body.rot': (0, 0, 10), 'body.scl': (.95, 1.08, .95), **up}),
                     (20, {'root.loc': (0, f, 0), 'body.rot': Z, 'body.scl': ONE, 'arm_L.rot': Z, 'arm_R.rot': Z})])
    M.clip('hurt', [(1, {'body.rot': Z, 'body.scl': ONE, 'root.loc': (0, f, 0)}),
                    (4, {'body.rot': (-18, 0, 0), 'body.scl': (1.15, .8, 1.15), 'root.loc': (0, f, -.12)}),
                    (10, {'body.rot': (6, 0, 0), 'body.scl': (.95, 1.06, .95), 'root.loc': (0, f, -.08)}),
                    (16, {'body.rot': Z, 'body.scl': ONE, 'root.loc': (0, f, 0)})])
    M.clip('color_up', [(1, {'root.loc': (0, f, 0), 'root.rot': Z, 'body.scl': ONE, 'arm_L.rot': Z, 'arm_R.rot': Z}),
                        (6, {'root.loc': (0, f, 0), 'root.rot': Z, 'body.scl': (1.15, .8, 1.15)}),
                        (14, {'root.loc': (0, f + .55, 0), 'root.rot': (0, 180, 0), 'body.scl': (.9, 1.15, .9), **up}),
                        (22, {'root.loc': (0, f, 0), 'root.rot': (0, 360, 0), 'body.scl': (1.12, .86, 1.12), 'arm_L.rot': Z, 'arm_R.rot': Z}),
                        (28, {'root.loc': (0, f, 0), 'root.rot': (0, 360, 0), 'body.scl': ONE})])


def feet(M, mat, x=.2, r=.11, z=.12, y=.07):
    for s, n in ((-1, 'foot_L'), (1, 'foot_R')):
        M.ball(n, r, (s * x, y, z), mat, n, (1, .65, 1.25))


def m12_sock():
    M = Model('m12-sock'); random.seed(12)
    red, cream = M.m('red', '#EE5A5F'), M.m('cream', '#FBE9D7')
    # leg: stripes by height
    prof = [(.0, .18), (.24, .2), (.27, .3), (.28, .5), (.28, .7), (.29, .9), (.29, 1.0)]
    leg = M.lathe('leg', prof, red, 'body', seg=20)
    leg.data.materials.append(cream)
    for p in leg.data.polygons:
        p.material_index = 0 if int((p.center.z - .2) / .14) % 2 else 1
    cuff = M.lathe('cuff', [(.3, .98), (.33, 1.0), (.33, 1.16), (.3, 1.2), (.0, 1.2)], red, 'top', seg=20)
    for i in range(10):  # ribs
        a = i / 10 * TAU
        M.cyl('rib%d' % i, .022, .2, (math.cos(a) * .33, 1.08, math.sin(a) * .33), M.m('red_dark', '#D9464C'), 'top', 6)
    foot = M.lathe('heel', [(.0, -.3), (.2, -.27), (.25, -.1), (.25, .08), (.2, .22), (0, .27)], red, 'body', seg=16, pos=(-.12, .24, .08), axis='x')
    toe = M.ball('toe', .22, (-.36, .23, .1), cream, 'body', (1, .9, 1))
    feet(M, M.m('red_dark', '#D9464C'), .14, .1, .18)
    fz = M.surface(leg)
    M.faces(fz, 0, .68, 1., tongue=True, sleepy=True)
    M.rig(MON_BONES(1.0))
    monster_clips(M, arms=0)
    M.fin = {'details': {'red': ('knit', .8), 'cream': ('knit', .8), 'red_dark': ('knit', .6)}, 'rough': {'red': .95, 'cream': .95}}
    return M


def m13_cushion():
    M = Model('m13-cushion'); random.seed(13)
    y, yd = M.m('yellow', '#F6C744'), M.m('yellow_dark', '#E3AC2A')
    body = M.rbox('pillow', (.95, .74, .36), (0, .62, 0), y, 'body', bevel=.16, segs=4)
    for v in body.data.vertices:  # puff the middle out: a cushion, not a box
        x, h = v.co.x / .5, (v.co.z - .62) / .4
        k = max(0, 1 - x * x) * max(0, 1 - h * h)
        v.co.y *= 1 + 1.1 * k
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, yy = sx * .5, .62 + sy * .38
            M.ball('knot%d%d' % (sx, sy), .06, (x, yy, 0), yd, 'body')
            M.lathe('tassel%d%d' % (sx, sy), [(.03, 0), (.07, -.12), (.06, -.2), (0, -.21)], yd, 'body', 8,
                    (x + sx * .06, yy + (.0 if sy > 0 else .0), 0))
    for sx in (-1, 1):  # little arms
        M.ball('arm', .09, (sx * .52, .5, .05), yd, 'arm_L' if sx < 0 else 'arm_R', (.8, 1, .8))
    feet(M, yd, .25, .1, .05)
    fz = M.surface(body)
    M.faces(fz, 0, .72, 1.05, spread=.17)
    M.rig(MON_BONES(1.0, (.3, .45)))
    monster_clips(M)
    M.fin = {'details': {'yellow': ('cloth', .6), 'yellow_dark': ('cloth', .5)}, 'rough': {'yellow': .9}}
    return M


def m14_balloon():
    M = Model('m14-balloon'); random.seed(14)
    bl, bd = M.m('blue', '#5CB8F0'), M.m('blue_dark', '#3B93D6')
    body = M.ball('balloon', .46, (0, 1.0, 0), bl, 'body', (1, 1.05, 1), sub=3)
    M.ball('shine', .07, (.2, 1.25, .37), M.m('shine', '#DFF3FF', .2), 'body', (1, 1.3, .5))
    M.lathe('knot', [(.0, .48), (.08, .5), (.05, .56), (.0, .6)], bd, 'body', 10)
    M.tube('string', [(0, .5, 0), (.08, .35, .02), (-.05, .2, 0), (.06, .06, 0)], .015, bd, 'top', res=6)
    wing = [(0, 0), (.32, .16), (.38, .02), (.3, -.02), (.26, -.1), (.17, -.06), (.1, -.13), (0, -.06)]
    for sx, bn in ((-1, 'arm_L'), (1, 'arm_R')):
        pts = [(x * sx, yy) for x, yy in wing]
        if sx < 0: pts = pts[::-1]
        M.flat('wing', pts, .04, (sx * .4, 1.02, -.05), bd, bn)
    fz = M.surface(body)
    M.faces(fz, 0, 1.06, 1.0)
    M.rig([('root', (0, 0, 0), None), ('body', (0, .5, 0), 'root'), ('top', (0, .5, 0), 'body'),
           ('arm_L', (-.4, 1.02, 0), 'body'), ('arm_R', (.4, 1.02, 0), 'body'),
           ('foot_L', (-.1, .1, 0), 'root'), ('foot_R', (.1, .1, 0), 'root')])
    monster_clips(M, float_=True, arms=25)
    M.fin = {'details': {'blue': ('rubber', .15), 'blue_dark': ('rubber', .15)}, 'rough': {'blue': .22, 'blue_dark': .3}}
    return M


def m21_hay():
    M = Model('m21-hay'); random.seed(21)
    hy, hd, hl = M.m('hay', '#F2C14E'), M.m('hay_dark', '#D9A033'), M.m('hay_light', '#FBE29A')
    body = M.lathe('bale', [(0, -.45), (.36, -.45), (.4, -.4), (.42, 0), (.4, .4), (.36, .45), (0, .45)], hy, 'body', 18, (0, .5, 0), 'x')
    for sx in (-1, 1):
        M.tube('spiral%d' % sx, [(sx * .455, .5 + .2 * math.sin(a) * (a / 12), .2 * math.cos(a) * (a / 12)) for a in [i * .9 for i in range(1, 14)]],
               .02, hd, 'body', res=3, bev=1)
    for x in (-.22, .22):
        M.lathe('strap', [(.425, -.03), (.435, 0), (.425, .03)], hl, 'body', 18, (x, .5, 0), 'x', cap=False)
    for i in range(26):
        a = random.uniform(0, TAU); x = random.uniform(-.4, .4)
        if math.sin(a) > .35 and abs(x) < .3: continue  # face
        d = Vector((0, math.cos(a), math.sin(a)))
        base = (x, .5 + d.y * .4, d.z * .4); tip = (x + random.uniform(-.08, .08), .5 + d.y * .55, d.z * .55)
        M.tube('straw%d' % i, [base, tip], .012, hd, 'top' if d.y > .5 else 'body', [1, .4], res=1, bev=0)
    feet(M, M.m('hoof', '#C9853A'), .25, .1, .12)
    fz = M.surface(body)
    M.faces(fz, 0, .58, 1.0)
    M.rig(MON_BONES(.9))
    monster_clips(M, arms=0)
    M.fin = {'details': {'hay': ('straw', .9), 'hay_dark': ('straw', .8), 'hay_light': ('straw', .6)}, 'rough': {'hay': .9}}
    return M


def m22_sheep():
    M = Model('m22-sheep'); random.seed(22)
    wool, face, horn = M.m('wool', '#FBF3E8'), M.m('face', '#F7C2B4'), M.m('horn', '#B98A55')
    puffs = [M.ball('core', .42, (0, .55, -.05), wool, None, sub=3)]
    for i in range(30):
        th = random.uniform(0, TAU); ph = math.acos(random.uniform(-.7, .95))
        p = (math.sin(ph) * math.cos(th) * .42, .55 + math.cos(ph) * .38, -.05 + math.sin(ph) * math.sin(th) * .42)
        if p[2] > .2 and abs(p[0]) < .28 and .35 < p[1] < .8: continue
        puffs.append(M.ball('p%d' % i, random.uniform(.14, .2), p, wool, None))
    body = M.remesh(M.join('wool', puffs, 'body'))
    fc = M.ball('faceplate', .27, (0, .55, .3), face, 'body', (1.05, .9, .5), sub=3)
    for sx in (-1, 1):
        pts = [(sx * (.28 + .12 * math.sin(a)), .78 + .14 * math.cos(a) * (1 - a / 9), .12 + .02 * a) for a in [i * .6 for i in range(0, 11)]]
        M.tube('horn%d' % sx, pts, .06, horn, 'top', [1 - i * .06 for i in range(11)], res=3)
    feet(M, M.m('hoof', '#A07850'), .2, .09, .1)
    fz = M.surface(fc)
    M.faces(fz, 0, .58, .85, spread=.12)
    M.rig(MON_BONES(.9))
    monster_clips(M, arms=0)
    M.fin = {'details': {'wool': ('wool', .6), 'face': ('skin', .25), 'horn': ('leather', .7)}, 'rough': {'wool': .98, 'horn': .45}}
    return M


def m23_mud():
    M = Model('m23-mud'); random.seed(23)
    mud, md = M.m('mud', '#9B6A45'), M.m('mud_dark', '#7A4F31')
    parts = [M.lathe('mound', [(.0, 0), (.5, .02), (.52, .1), (.45, .3), (.36, .6), (.2, .82), (0, .87)], mud, None, 20)]
    for i in range(9):
        a = i / 9 * TAU + random.uniform(-.2, .2)
        parts.append(M.ball('drip%d' % i, random.uniform(.1, .15), (math.cos(a) * .48, .06, math.sin(a) * .48), mud, None, (1.4, .5, 1.4)))
    body = M.remesh(M.join('mud', parts, 'body'), .03, .15)
    for i in range(4):
        a = random.uniform(0, TAU)
        M.ball('splat%d' % i, .06, (math.cos(a) * .72, .015, math.sin(a) * .72), md, 'root', (1.3, .25, 1.3))
    leaf = M.ball('leaf', .26, (0, .88, 0), M.m('leaf', '#5DBB63'), 'top', (1, .12, .8))
    M.tube('vein', [(-.18, .9, 0), (.18, .91, 0)], .012, M.m('leaf_dark', '#3E9A4A'), 'top', res=2, bev=1)
    M.ball('drop', .05, (.22, .55, .36), M.m('drop', '#D8F0FF', .1), 'body', (1, 1.3, .8))
    fz = M.surface(body)
    M.faces(fz, 0, .48, .95)
    M.rig(MON_BONES(.86))
    monster_clips(M, arms=0)
    M.fin = {'details': {'mud': ('mud', .7), 'mud_dark': ('mud', .6), 'leaf': ('skin', .3)}, 'rough': {'mud': .32, 'mud_dark': .3, 'leaf': .5}}
    return M


def m24_fruit():
    M = Model('m24-fruit'); random.seed(24)
    g, gd = M.m('pear', '#A8D65A'), M.m('pear_dark', '#86B840')
    prof = [(0, .06), (.3, .09), (.42, .22), (.45, .38), (.38, .58), (.26, .76), (.2, .92), (.12, 1.02), (0, 1.05)]
    body = M.lathe('pear', prof, g, 'body', 22)
    M.cyl('stem', .035, .2, (0, 1.12, 0), M.m('stem', '#8A5A33'), 'top', 6)
    M.ball('leaf', .17, (.15, 1.16, 0), M.m('leaf', '#4FAE4F'), 'top', (1.2, .12, .55))
    feet(M, gd, .16, .08, .1, .05)
    fz = M.surface(body)
    M.faces(fz, 0, .42, .95, spread=.14)
    M.rig(MON_BONES(1.02))
    monster_clips(M, arms=0)
    M.fin = {'details': {'pear': ('skin', .35), 'pear_dark': ('skin', .3), 'stem': ('straw', .5)}, 'rough': {'pear': .42, 'leaf': .5}}
    return M


# ======================= heroes =======================
HERO_BONES = [('root', (0, 0, 0), None), ('hips', (0, .5, 0), 'root'), ('torso', (0, .53, 0), 'hips'),
              ('head', (0, .95, 0), 'torso'), ('cape', (0, .9, -.06), 'torso'),
              ('arm_L', (-.155, .86, 0), 'torso'), ('arm_R', (.155, .86, 0), 'torso'),
              ('leg_L', (-.085, .5, 0), 'hips'), ('leg_R', (.085, .5, 0), 'hips')]


def cut(o, keep):
    """delete the faces of o whose centre (in game x, up, front numbers) fails keep(x, y, z)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        if not keep(c.x, c.z, -c.y): dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(o.data); bm.free()
    for m in o.data.materials: m.use_backface_culling = False
    return o


def hero(kind):
    """Amy / the boy hero, after Jerry's turnaround sheet (2026-11-04). Proportions are measured off the
    front view (feet 0 .. cap top 1.45): boot top .25, shorts hem .39, tunic hem .51, belt .65, shoulders .88,
    chin .99, eyes 1.10. Red newsboy cap with a pom and two side puffs, brown hair with a fringe and side
    locks (low pigtails with red ties for the girl), mustard hooded capelet open at the front with a gold
    brooch, blue tunic, cream shirt, brown belt + gold buckle + pouch, beige shorts, chunky cuffed boots,
    arms held a little out (A pose)."""
    girl = kind == 'girl'
    M = Model('hero-' + kind); random.seed(7)
    skin, hair, hair_l = M.m('skin', '#F6CDB0', .75), M.m('hair', '#8E5534', .65), M.m('hair_light', '#A86A40', .65)
    blue, shirt, shorts = M.m('tunic', '#4A6DA8'), M.m('shirt', '#DCCBAA'), M.m('shorts', '#CDB48B')
    belt, gold, pouch = M.m('belt', '#7E4A2A', .6), M.m('gold', '#E8B63E', .35), M.m('pouch', '#8E5634', .6)
    cape, cape_d = M.m('cape', '#D49B2E'), M.m('cape_dark', '#C68C26')
    red, red_d = M.m('cap', '#D2463B'), M.m('cap_dark', '#B9392F')
    boot, boot_d = M.m('boot', '#A1603A', .65), M.m('boot_dark', '#87502F', .65)
    # ---- boots + legs ----
    for sx, bn in ((-1, 'leg_L'), (1, 'leg_R')):
        x = sx * .085
        M.lathe('boot', [(0, .02), (.08, .02), (.086, .06), (.08, .14), (.077, .2)], boot, bn, 16, (x, 0, 0))
        M.lathe('cuff', [(.075, .19), (.094, .195), (.098, .245), (.088, .255), (0, .255)], boot_d, bn, 16, (x, 0, 0))
        M.ball('toe', .078, (x, .058, .06), boot, bn, (1.05, .75, 1.35), sub=3)
        M.ball('sole', .086, (x, .022, .035), boot_d, bn, (1.08, .26, 1.45), sub=3)
        M.lathe('leg', [(.056, .24), (.06, .32), (.066, .4)], skin, bn, 12, (x, 0, 0), cap=False)
        M.lathe('shortleg', [(0, .38), (.082, .38), (.086, .4), (.088, .5), (0, .52)], shorts, bn, 14, (x, 0, 0))
    M.lathe('shorts', [(.15, .44), (.17, .48), (.17, .53), (0, .55)], shorts, 'hips', 18)
    # ---- tunic, belt, pouch ----
    M.lathe('tunic', [(0, .5), (.205, .5), (.21, .52), (.185, .6), (.168, .68), (.16, .78), (.145, .86), (.09, .91), (0, .92)], blue, 'torso', 22)
    M.lathe('belt', [(.17, .625), (.176, .64), (.174, .675), (.168, .69)], belt, 'torso', 22, cap=False)
    M.rbox('buckle', (.075, .06, .02), (0, .657, .176), gold, 'torso', .01, 2)
    M.rbox('buckle_in', (.042, .03, .02), (0, .657, .183), belt, 'torso', .006, 1)
    M.rbox('pouch', (.08, .075, .05), (-.095, .6, .168), pouch, 'torso', .02, 2)
    M.rbox('flap', (.084, .032, .056), (-.095, .632, .173), belt, 'torso', .012, 2)
    M.ball('stud', .011, (-.095, .622, .203), gold, 'torso')
    # ---- capelet: drapes from the shoulders to the hips, open at the front, wavy hem, hood roll ----
    prof = [(.1, .93), (.16, .9), (.215, .84), (.25, .74), (.275, .62), (.29, .53)]
    cp = M.lathe('cape_cloth', prof, cape, 'cape', 32, cap=False)
    cut(cp, lambda x, y, z: not (z > -.02 and abs(x) < .1 + (.93 - y) * .45) or y > .86)
    bm = bmesh.new(); bm.from_mesh(cp.data)  # wavy hem
    for v in bm.verts:
        x, y, z = v.co.x, v.co.z, -v.co.y
        if y < .56:
            a = math.atan2(z, x); v.co.z += .02 * math.sin(a * 6)
    bm.to_mesh(cp.data); bm.free()
    hood = M.ball('hood', .185, (0, .905, -.035), cape_d, 'cape', (1.0, .26, .9), sub=3)
    cut(hood, lambda x, y, z: z < .06)
    M.ball('hoodback', .13, (0, .93, -.13), cape_d, 'cape', (1.1, .55, .5), sub=3)
    M.lathe('brooch', [(0, 0), (.03, 0), (.034, .012), (.02, .02), (0, .022)], gold, 'torso', 14, (.075, .875, .135), 'z')
    # ---- arms: A pose, cream sleeves, skin hands ----
    for sx, bn in ((-1, 'arm_L'), (1, 'arm_R')):
        M.ball('shoulder', .064, (sx * .16, .855, 0), shirt, bn, sub=3)
        M.tube('sleeve', [(sx * .165, .85, 0), (sx * .22, .75, .01), (sx * .27, .65, .02)], .056, shirt, bn, [1, .95, .85], res=6, bev=3)
        M.lathe('wrist', [(.036, -.012), (.042, 0), (.036, .012)], shirt, bn, 10, (sx * .268, .645, .02))
        M.ball('hand', .045, (sx * .282, .6, .025), skin, bn, (.85, 1.15, .9), sub=3)
        M.ball('thumb', .017, (sx * .268, .615, .057), skin, bn)
    hx, hyy = .295, .6
    if girl:
        M.cyl('wand', .012, .28, (hx, hyy + .08, .04), M.m('wood', '#C68A4E'), 'arm_R', 8)
        star = [(math.cos(TAU * i / 10 + math.pi / 2) * (.085 if i % 2 == 0 else .04), math.sin(TAU * i / 10 + math.pi / 2) * (.085 if i % 2 == 0 else .04)) for i in range(10)]
        M.flat('star', star, .03, (hx, hyy + .26, .04), gold, 'arm_R')
    else:
        wood, wood_d = M.m('wood', '#D19A5E'), M.m('wood_dark', '#9B6534')
        M.rbox('blade', (.055, .3, .02), (hx, hyy + .2, .04), wood, 'arm_R', .02, 1)
        M.rbox('guard', (.13, .026, .034), (hx, hyy + .045, .04), wood_d, 'arm_R', .01, 1)
        M.cyl('grip', .016, .07, (hx, hyy, .04), wood_d, 'arm_R', 8)
    # ---- head: wide chibi face, chin at .99 ----
    hy = 1.17
    head = M.ball('head', .225, (0, hy, 0), skin, 'head', (1.08, .97, .98), sub=4)
    M.cyl('neck', .05, .08, (0, .96, 0), skin, 'head', 10)
    fz0 = M.surface(head)
    for sx in (-1, 1):
        M.ball('ear', .045, (sx * .24, hy - .04, -.01), skin, 'head', (.5, 1, .75), sub=3)
    # hair: back shell (whole front cut away), then a curtain of clay strands over the forehead, side locks
    hb = M.ball('hairback', .238, (0, hy + .015, -.015), hair, 'head', (1.1, 1.0, 1.03), sub=3)
    cut(hb, lambda x, y, z: (z < .03 or (abs(x) > .135 and y > hy - .02) or (abs(x) > .18 and y > hy - .12 and z < .1)) and y > hy - .17)
    under = M.ball('fringe', .232, (0, hy + .012, .0), hair, 'head', (1.09, 1.0, 1.03), sub=3)  # dark base under the strands
    cut(under, lambda x, y, z: z >= .03 and y > hy + .06 + .02 * abs(math.sin(x * 18)))
    def on0(x, y, d): return (x, y, fz0(x, y) + d)
    # strands: (x at the crown, x at the tip, tip height) - a side part on her right, sweeping across
    strands = ((-.19, -.215, hy - .02), (-.13, -.16, hy + .025), (-.07, -.1, hy + .045), (-.01, -.045, hy + .05),
               (.05, .02, hy + .05), (.11, .1, hy + .045), (.17, .19, hy + .01))
    for i, (x0, x1, ty) in enumerate(strands):  # a part on her right, sweeping across; roots hidden under the cap
        a, b = on0(x0 * .8, hy + .14, .0), on0(x1, ty, .012)
        mid = on0((x0 * .8 + x1) / 2 - .01, (hy + .14 + ty) / 2 + .01, .03)
        M.tube('fringe%d' % i, [a, mid, b], .056, hair_l if i % 3 == 1 else hair, 'head', [1, .9, .4], res=8, bev=3)
    for sx in (-1, 1):  # locks in front of the ears, down to the cheeks
        M.tube('lock', [on0(sx * .19, hy + .12, .02), on0(sx * .215, hy + .0, .022), on0(sx * .2, hy - .1, .02)], .04, hair, 'head', [1, .9, .3], res=8, bev=3)
    if girl:
        for sx in (-1, 1):  # low pigtails beside the jaw, red ties
            tx, ty, tz = sx * .205, hy - .12, -.06
            M.ball('tie', .034, (tx, ty, tz), red, 'head', (1, 1, 1), sub=3)
            M.ball('tail', .085, (tx + sx * .085, ty - .05, tz), hair, 'head', (1.1, .95, .95), sub=3)
            for j, (dx, dy, dz) in enumerate(((.15, -.06, .03), (.14, -.13, -.02), (.09, -.16, .03), (.17, -.02, -.03))):
                M.tube('plait%d' % j, [(tx, ty, tz), (tx + sx * dx * .6, ty + dy * .3, tz + dz), (tx + sx * dx, ty + dy, tz + dz * .5)],
                       .055, hair if j % 2 else hair_l, 'head', [.8, 1, .35], res=6, bev=3)
    else:
        for i, (x, z) in enumerate(((-.12, -.17), (0, -.2), (.12, -.17))):  # short tufts at the nape
            M.tube('nape%d' % i, [(x, hy - .02, z), (x * 1.1, hy - .12, z - .02), (x * 1.2, hy - .16, z + .02)], .045, hair, 'head', [1, .7, .25], res=6, bev=3)
    # ---- newsboy cap: soft crown that wraps the head down to the fringe, short brim, pom, two side puffs ----
    def tilt(o, deg, py, pz=0):  # rotate about the x axis (front goes down for deg > 0) around (y=py, z=pz)
        c, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        for v in o.data.vertices:
            y, z = v.co.z - py, -v.co.y - pz
            y, z = y * c - z * sn, y * sn + z * c
            v.co.z, v.co.y = y + py, -(z + pz)
        return o
    T = -15  # crown tipped back over the nape, front edge lifted off the fringe
    tilt(M.ball('cap', 1, (0, hy + .2, -.04), red, 'head', (.305, .2, .305), sub=3), T, hy + .2)  # puffy crown, tipped forward
    brim = M.ball('brim', .16, (0, hy + .135, .19), red_d, 'head', (1.12, .17, .72), sub=3)
    cut(brim, lambda x, y, z: z > .235)
    tilt(M.ball('pom', .062, (0, hy + .405, -.06), red, 'head', sub=3), T, hy + .2)
    for sx in (-1, 1):
        tilt(M.ball('puff', .075, (sx * .25, hy + .3, -.03), red, 'head', (1, .9, 1), sub=3), T, hy + .2)
    # ---- face: big round eyes (white, brown iris, pupil, two glints, top lash), arched brows, open smile ----
    fz = fz0
    E, W, I = M.m('eye', '#2A170F', .3), M.m('white', '#FFFFFF', .35), M.m('iris', '#5E3519', .3)
    ey = hy - .05
    for sx in (-1, 1):
        x = sx * .1
        z = fz(x, ey)
        M.ball('sclera', .046, (x, ey, z - .012), W, 'head', (1.05, 1.22, .42), sub=3)
        M.ball('iris', .039, (x - sx * .003, ey - .004, z - .004), I, 'head', (1, 1.18, .4), sub=3)
        M.ball('pupil', .022, (x - sx * .003, ey - .002, z + .003), E, 'head', (1, 1.2, .35), sub=3)
        M.ball('glint', .015, (x + .014, ey + .02, z + .01), W, 'head', (1, 1.1, .4))
        M.ball('glint2', .007, (x - .013, ey - .022, z + .009), W, 'head', (1, 1, .4))
        lash = [(x - sx * .046, ey + .01), (x - sx * .022, ey + .048), (x + sx * .02, ey + .053), (x + sx * .05, ey + .026)]
        M.tube('lash', [(a, b, fz(a, b) + .001) for a, b in lash], .0075, E, 'head', [.5, 1, 1, .8], res=4, bev=2)
        brow = [(x - .035, ey + .088), (x, ey + .102), (x + .035, ey + .09)]
        M.tube('brow', [(a, b, fz(a, b) + .002) for a, b in brow], .006, hair, 'head', res=4, bev=1)
        cx = sx * .155
        M.ball('cheek', .048, (cx, ey - .07, fz(cx, ey - .07) - .008), M.m('cheek', '#F4A194', .95), 'head', (1.2, .7, .3), sub=3)
    my = hy - .112  # open D-shaped smile: flat top, round bottom
    mouth = [(math.cos(math.pi + math.pi * i / 14) * .052, math.sin(math.pi + math.pi * i / 14) * .05) for i in range(15)]
    M.flat('mouth', mouth, .014, (0, my, fz(0, my - .015) - .002), M.m('mouth', '#9C2A35', .6), 'head')
    tongue = [(math.cos(math.pi + math.pi * i / 10) * .032, math.sin(math.pi + math.pi * i / 10) * .018 - .027) for i in range(11)]
    M.flat('tongue', tongue, .014, (0, my, fz(0, my - .025) + .003), M.m('tongue', '#EE7480', .6), 'head')
    M.ball('nose', .012, (0, ey - .045, fz(0, ey - .045) - .002), M.m('nose', '#F0B394', .7), 'head')
    M.fin = {'details': {'tunic': ('cloth', .55), 'shorts': ('cloth', .5), 'shirt': ('cloth', .45), 'cape': ('cloth', .5),
                         'cape_dark': ('cloth', .5), 'cap': ('felt', .6), 'cap_dark': ('felt', .6), 'boot': ('leather', .6),
                         'boot_dark': ('leather', .6), 'belt': ('leather', .6), 'pouch': ('leather', .6), 'hair': ('hair', .55),
                         'hair_light': ('hair', .55), 'skin': ('skin', .12), 'wood': ('straw', .4), 'wood_dark': ('straw', .4)},
             'tiles': 15, 'rough': {'skin': .6, 'gold': .28, 'tunic': .9, 'cape': .88, 'cap': .95, 'boot': .5, 'boot_dark': .55, 'hair': .55}}
    M.rig(HERO_BONES)
    hero_clips(M)
    return M


def hero_clips(M):
    M.clip('idle', [(1, {'torso.scl': ONE, 'head.rot': (0, 0, 2), 'arm_L.rot': (0, 0, -4), 'arm_R.rot': (0, 0, 4), 'cape.rot': (0, 0, 0)}),
                    (20, {'torso.scl': (1, 1.025, 1), 'head.rot': (0, 0, -2), 'arm_L.rot': (0, 0, -8), 'arm_R.rot': (0, 0, 8), 'cape.rot': (-5, 0, 0)}),
                    (40, {'torso.scl': ONE, 'head.rot': (0, 0, 2), 'arm_L.rot': (0, 0, -4), 'arm_R.rot': (0, 0, 4), 'cape.rot': (0, 0, 0)})])
    s = 32
    M.clip('walk', [(1, {'leg_L.rot': (s, 0, 0), 'leg_R.rot': (-s, 0, 0), 'arm_L.rot': (-s, 0, 0), 'arm_R.rot': (s, 0, 0), 'hips.loc': Z, 'cape.rot': (-12, 0, 0)}),
                    (6, {'hips.loc': (0, .03, 0), 'cape.rot': (-18, 0, 0)}),
                    (11, {'leg_L.rot': (-s, 0, 0), 'leg_R.rot': (s, 0, 0), 'arm_L.rot': (s, 0, 0), 'arm_R.rot': (-s, 0, 0), 'hips.loc': Z, 'cape.rot': (-12, 0, 0)}),
                    (16, {'hips.loc': (0, .03, 0), 'cape.rot': (-18, 0, 0)}),
                    (21, {'leg_L.rot': (s, 0, 0), 'leg_R.rot': (-s, 0, 0), 'arm_L.rot': (-s, 0, 0), 'arm_R.rot': (s, 0, 0), 'hips.loc': Z, 'cape.rot': (-12, 0, 0)})])
    M.clip('cast', [(1, {'arm_R.rot': Z, 'torso.rot': Z, 'cape.rot': Z}),
                    (6, {'arm_R.rot': (-150, 0, 0), 'torso.rot': (0, 15, 0), 'cape.rot': (-10, 0, 0)}),
                    (11, {'arm_R.rot': (-60, 0, 0), 'torso.rot': (8, -20, 0), 'cape.rot': (-25, 0, 0)}),
                    (20, {'arm_R.rot': Z, 'torso.rot': Z, 'cape.rot': Z})])
    M.clip('cheer', [(1, {'root.loc': Z, 'arm_L.rot': Z, 'arm_R.rot': Z, 'leg_L.rot': Z, 'leg_R.rot': Z}),
                     (6, {'root.loc': (0, .25, 0), 'arm_L.rot': (0, 0, -135), 'arm_R.rot': (0, 0, 135), 'leg_L.rot': (20, 0, 0), 'leg_R.rot': (20, 0, 0)}),
                     (12, {'root.loc': Z, 'arm_L.rot': (0, 0, -125), 'arm_R.rot': (0, 0, 125), 'leg_L.rot': Z, 'leg_R.rot': Z}),
                     (18, {'root.loc': (0, .2, 0), 'arm_L.rot': (0, 0, -135), 'arm_R.rot': (0, 0, 135)}),
                     (26, {'root.loc': Z, 'arm_L.rot': Z, 'arm_R.rot': Z})])
    M.clip('hurt', [(1, {'torso.rot': Z, 'root.loc': Z, 'head.rot': Z}),
                    (4, {'torso.rot': (-15, 0, 0), 'root.loc': (0, 0, -.1), 'head.rot': (-10, 0, 0)}),
                    (14, {'torso.rot': Z, 'root.loc': Z, 'head.rot': Z})])


def pip():
    M = Model('pip'); random.seed(3)
    o, cr, y = M.m('feather', '#F08C2E'), M.m('belly', '#F7DDB0'), M.m('beak', '#F2B630', .5)
    body = M.ball('body', .42, (0, .5, 0), o, 'body', (1, .95, .9), sub=3)
    M.ball('belly', .3, (0, .4, .2), cr, 'body', (1, 1, .6), sub=3)
    for sx in (-1, 1):
        M.ball('tuft', .1, (sx * .26, .9, 0), o, 'body', (.7, 1.3, .7))
        M.ball('wing', .2, (sx * .4, .48, 0), M.m('wing', '#E07A22'), 'arm_L' if sx < 0 else 'arm_R', (.4, 1.1, .8))
        M.ball('foot', .07, (sx * .13, .07, .15), y, 'body', (1, .5, 1.3))
    fz = M.surface(body)
    W, E = M.m('white', '#FFFFFF', .4), M.m('eye', '#2A1A14', .3)
    for sx in (-1, 1):
        x = sx * .15
        M.ball('eyewhite', .13, (x, .62, fz(x, .62) - .05), W, 'body', (1, 1, .5))
        M.ball('pupil', .075, (x, .62, fz(x, .62) + .01), E, 'body', (1, 1, .45))
        M.ball('glint', .025, (x + .03, .66, fz(x, .62) + .04), W, 'body', (1, 1, .4))
        M.ball('cheek', .05, (sx * .27, .5, fz(sx * .27, .5) - .01), M.m('cheek', '#FF9C9C', .9), 'body', (1, .6, .3))
    M.lathe('beak', [(.0, 0), (.06, 0), (0, -.09)], y, 'body', 8, (0, .53, fz(0, .53) + .02), 'z')
    M.fin = {'details': {'feather': ('fur', .55), 'wing': ('fur', .55), 'belly': ('fur', .4)}, 'rough': {'feather': .9, 'beak': .4}}
    M.rig([('root', (0, 0, 0), None), ('body', (0, .1, 0), 'root'), ('arm_L', (-.36, .62, 0), 'body'), ('arm_R', (.36, .62, 0), 'body')])
    M.clip('idle', [(1, {'root.loc': Z, 'arm_L.rot': (0, 0, 0), 'arm_R.rot': (0, 0, 0)}),
                    (20, {'root.loc': (0, .06, 0), 'arm_L.rot': (0, 0, -15), 'arm_R.rot': (0, 0, 15)}),
                    (40, {'root.loc': Z, 'arm_L.rot': (0, 0, 0), 'arm_R.rot': (0, 0, 0)})])
    M.clip('flap', [(1, {'arm_L.rot': (0, 0, -10), 'arm_R.rot': (0, 0, 10), 'root.loc': Z}),
                    (4, {'arm_L.rot': (0, 0, -70), 'arm_R.rot': (0, 0, 70), 'root.loc': (0, .08, 0)}),
                    (8, {'arm_L.rot': (0, 0, -10), 'arm_R.rot': (0, 0, 10), 'root.loc': Z})])
    return M


BUILD = {'m12-sock': m12_sock, 'm13-cushion': m13_cushion, 'm14-balloon': m14_balloon, 'm21-hay': m21_hay,
         'm22-sheep': m22_sheep, 'm23-mud': m23_mud, 'm24-fruit': m24_fruit,
         'hero-boy': lambda: hero('boy'), 'hero-girl': lambda: hero('girl'), 'pip': pip}

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    out = args[0] if args else 'models'
    names = args[1:] or list(BUILD)
    os.makedirs(out, exist_ok=True)
    for n in names:
        BUILD[n]().export(os.path.join(out, n + '.glb'))
