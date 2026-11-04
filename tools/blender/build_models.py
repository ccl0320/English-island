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
        n = sum(len(o.data.polygons) for o in C.scene.objects if o.type == 'MESH')
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_animation_mode='NLA_TRACKS',
                                  export_apply=True, export_yup=True, export_def_bones=False)
        print('%-14s %5d faces %6.1f KB' % (self.name, n, os.path.getsize(path) / 1024))


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
    return M


# ======================= heroes =======================
HERO_BONES = [('root', (0, 0, 0), None), ('hips', (0, .42, 0), 'root'), ('torso', (0, .45, 0), 'hips'),
              ('head', (0, .82, 0), 'torso'), ('cape', (0, .8, -.12), 'torso'),
              ('arm_L', (-.2, .75, 0), 'torso'), ('arm_R', (.2, .75, 0), 'torso'),
              ('leg_L', (-.09, .42, 0), 'hips'), ('leg_R', (.09, .42, 0), 'hips')]


def hero(kind):
    girl = kind == 'girl'
    M = Model('hero-' + kind); random.seed(7)
    skin, hair = M.m('skin', '#F6D2B0', .7), M.m('hair', '#7A4A2A', .7)
    blue, belt, gold = M.m('tunic', '#3E6FB0'), M.m('belt', '#7A4A2A', .6), M.m('gold', '#E8B93C', .4)
    cape, red, boot = M.m('cape', '#F2C230'), M.m('cap', '#D9433E'), M.m('boot', '#8A5A33', .6)
    shorts = M.m('shorts', '#E9D6B4')
    # legs + boots
    for sx, bn in ((-1, 'leg_L'), (1, 'leg_R')):
        x = sx * .09
        M.cyl('leg', .055, .2, (x, .3, 0), skin if girl else shorts, bn, 8)
        M.lathe('boot', [(.0, 0), (.08, .0), (.085, .06), (.07, .18), (.075, .2), (0, .2)], boot, bn, 10, (x, 0, .0))
        M.ball('toe', .075, (x, .045, .05), boot, bn, (1, .6, 1.3))
    if not girl:
        M.lathe('shorts', [(.13, .36), (.15, .42), (.14, .47), (0, .47)], shorts, 'hips', 14)
    # tunic / dress
    tun = [(.0, .45), (.15, .45), (.14, .55), (.13, .7), (.15, .78), (0, .82)] if not girl else \
          [(.0, .35), (.2, .34), (.16, .5), (.13, .7), (.15, .78), (0, .82)]
    M.lathe('tunic', tun, blue, 'torso', 16)
    if girl:
        M.lathe('hem', [(.205, .335), (.21, .36), (.19, .375)], gold, 'torso', 16, cap=False)
    M.lathe('belt', [(.145, .53), (.15, .56), (.145, .59)], belt, 'torso', 16, cap=False)
    M.rbox('buckle', (.08, .06, .03), (0, .56, .15), gold, 'torso', .01, 1)
    M.tube('strap', [(-.14, .78, .06), (0, .66, .155), (.13, .53, .1)], .015, belt, 'torso', res=4, bev=1)
    M.rbox('bag', (.08, .08, .05), (-.12, .5, .12), belt, 'torso', .015, 1)
    # cape: back half of a cone
    cp = M.lathe('cape_cloth', [(.36, .32), (.25, .55), (.16, .8), (.12, .84)], cape, 'cape', 18, cap=False)
    bm = bmesh.new(); bm.from_mesh(cp.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if -f.calc_center_median().y > -.02], context='FACES')
    bm.to_mesh(cp.data); bm.free()
    cp.data.materials[0].use_backface_culling = False
    M.ball('collar', .06, (-.13, .8, .08), cape, 'torso'); M.ball('collar', .06, (.13, .8, .08), cape, 'torso')
    # arms + hands
    for sx, bn in ((-1, 'arm_L'), (1, 'arm_R')):
        x = sx * .215
        M.lathe('sleeve', [(.05, .0), (.06, .2), (.05, .22)], blue, bn, 8, (x, .54, 0))
        M.ball('hand', .055, (x, .5, .01), skin, bn)
    # weapon in right hand
    if girl:
        M.cyl('wand', .018, .34, (.215, .58, .05), M.m('wood', '#C68A4E'), 'arm_R', 6)
        star = [(math.cos(TAU * i / 10 + math.pi / 2) * (.11 if i % 2 == 0 else .05), math.sin(TAU * i / 10 + math.pi / 2) * (.11 if i % 2 == 0 else .05)) for i in range(10)]
        M.flat('star', star, .04, (.215, .8, .05), gold, 'arm_R')
    else:
        wood = M.m('wood', '#D19A5E')
        M.rbox('blade', (.07, .36, .025), (.215, .74, .05), wood, 'arm_R', .02, 1)
        M.rbox('guard', (.16, .03, .04), (.215, .55, .05), M.m('wood_dark', '#9B6534'), 'arm_R', .01, 1)
        M.cyl('grip', .02, .09, (.215, .5, .05), M.m('wood_dark', '#9B6534'), 'arm_R', 6)
    # head
    hy = 1.08
    head = M.ball('head', .3, (0, hy, 0), skin, 'head', (1, .95, .95), sub=3)
    hb = M.ball('hairback', .315, (0, hy + .03, -.025), hair, 'head', (1, .97, .97), sub=3)
    bm = bmesh.new(); bm.from_mesh(hb.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (-f.calc_center_median().y > .1 and f.calc_center_median().z < hy + .17)], context='FACES')
    bm.to_mesh(hb.data); bm.free(); hb.data.materials[0].use_backface_culling = False
    for i, x in enumerate((-.19, -.09, .02, .13, .21)):  # fringe
        M.ball('fringe%d' % i, .085, (x, hy + .16 - abs(x) * .25, .22 - abs(x) * .3), hair, 'head', (1, .8, .8))
    for sx in (-1, 1):  # side hair
        M.ball('side', .1, (sx * .27, hy - .06, .02), hair, 'head', (.6, 1.3, .9))
    if girl:
        for sx in (-1, 1):
            M.ball('tail', .11, (sx * .36, hy - .12, -.05), hair, 'head', (.9, 1.2, .9))
            M.ball('tie', .045, (sx * .31, hy - .02, -.04), red, 'head')
    # cap: beanie + brim + knob
    M.ball('cap', .33, (0, hy + .1, -.02), red, 'head', (1.02, .7, 1.0), sub=3)
    M.lathe('brim', [(0, 0), (.2, 0), (.21, .025), (0, .03)], M.m('cap_dark', '#C23A36'), 'head', 14, (.02, hy + .16, .2))
    M.ball('knob', .07, (0, hy + .32, -.05), red, 'head')
    # face
    fz = M.surface(head)
    E, W = M.m('eye', '#2A1A14', .3), M.m('white', '#FFFFFF', .4)
    for sx in (-1, 1):
        x = sx * .11
        M.ball('eye', .072, (x, hy - .01, fz(x, hy - .01) - .022), E, 'head', (1, 1.35, .5))
        M.ball('glint', .026, (x + .022, hy + .035, fz(x, hy - .01) + .006), W, 'head', (1, 1, .5))
        M.ball('cheek', .05, (sx * .2, hy - .1, fz(sx * .2, hy - .1) - .008), M.m('cheek', '#FF9C9C', .9), 'head', (1, .6, .3))
        M.tube('brow', [(x - .04, hy + .1, fz(x - .04, hy + .1) - .003), (x + .04, hy + .11, fz(x + .04, hy + .11) - .003)], .012, hair, 'head', res=1, bev=1)
    M.ball('mouth', .05, (0, hy - .14, fz(0, hy - .14) - .012), M.m('mouth', '#C2405A', .6), 'head', (1.2, .8, .4))
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
