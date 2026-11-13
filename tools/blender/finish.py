"""Finishing pass that makes the procedural models look less like plastic toys (2026-11-13).

Used by build_models.py and dust_monster.py right before export. It adds, cheaply for phones:

1. Ambient occlusion baked into vertex colours (glTF COLOR_0): soft contact shadows where parts
   meet (under the cap, under the chin, between the legs, under the arms), so the model reads as one
   solid object instead of separate balls. Three.js multiplies COLOR_0 with the material colour, so
   it costs nothing at run time and survives the game's grey-out / colour-wash on monsters.
2. Tiny tileable detail normal maps (128 px JPEG, shared): woven cloth, knitted wool, leather,
   felt, fur, straw, hair strands, mud, skin pores. Light catches the surface texture.
3. Better roughness: glossy eyes / balloon / wet mud, matte cloth.

The game draws colours as-is (no sRGB output), so the AO values are written straight to a
FLOAT_COLOR attribute: what is stored is what is shown.
"""
import bpy, bmesh, math, os, random, tempfile
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TAU = math.pi * 2
_IMG = {}
_TMP = tempfile.mkdtemp(prefix='ei_detail_')


# ---------------------------------------------------------------- detail maps
def _fnoise(n, f0, f1, rng):
    """tileable band-limited noise in [0, 1] (FFT, so it wraps seamlessly)."""
    k = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(k, k)
    r = np.sqrt(kx * kx + ky * ky)
    amp = np.where((r >= f0) & (r <= f1), 1.0 / np.maximum(r, 1), 0)
    ph = rng.uniform(0, TAU, (n, n))
    h = np.real(np.fft.ifft2(amp * np.exp(1j * ph)))
    return (h - h.min()) / (np.ptp(h) + 1e-9)


def _stretch(n, f, rng, axis=0):
    """streaks along one axis (straw, hair): noise that only varies across the strands."""
    k = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(k, k)
    along, across = (kx, ky) if axis == 0 else (ky, kx)
    amp = np.where((np.abs(across) >= 2) & (np.abs(across) <= f) & (np.abs(along) <= 2), 1.0, 0)
    h = np.real(np.fft.ifft2(amp * np.exp(1j * rng.uniform(0, TAU, (n, n)))))
    return (h - h.min()) / (np.ptp(h) + 1e-9)


def _height(kind, n):
    rng = np.random.default_rng(abs(hash(kind)) % 2 ** 31)
    u = np.arange(n) / n
    x, y = np.meshgrid(u, u)
    if kind == 'cloth':  # plain weave: threads over / under in a checker of 16 x 16 cells
        c = 16
        fx, fy = (x * c) % 1, (y * c) % 1
        warp = np.sin(np.pi * fx) ** .7 * (0.6 + 0.4 * np.cos(TAU * fy))
        weft = np.sin(np.pi * fy) ** .7 * (0.6 + 0.4 * np.cos(TAU * fx))
        chk = ((np.floor(x * c) + np.floor(y * c)) % 2).astype(bool)
        return np.where(chk, warp, weft) * .85 + _fnoise(n, 20, 60, rng) * .15
    if kind == 'knit':  # rows of V stitches
        cols, rows = 8, 12
        fx, fy = (x * cols) % 1, (y * rows) % 1
        v = 1 - np.abs((fx - .5) * 2 - (fy - .5) * .9) ** 1.5
        v2 = 1 - np.abs((.5 - fx) * 2 - (fy - .5) * .9) ** 1.5
        return np.clip(np.maximum(v, v2), 0, 1) * np.sin(np.pi * fy) * .85 + _fnoise(n, 16, 48, rng) * .15
    if kind == 'leather':
        return _fnoise(n, 6, 30, rng) * .6 + _fnoise(n, 30, 64, rng) * .4
    if kind == 'felt':
        return _fnoise(n, 24, 64, rng)
    if kind == 'fur':
        return _fnoise(n, 3, 10, rng) * .55 + _fnoise(n, 24, 64, rng) * .45
    if kind == 'wool':  # little curls
        return np.abs(np.sin(_fnoise(n, 4, 9, rng) * TAU * 2)) * .7 + _fnoise(n, 20, 64, rng) * .3
    if kind == 'straw':
        return _stretch(n, 40, rng) * .8 + _fnoise(n, 24, 64, rng) * .2
    if kind == 'hair':
        return _stretch(n, 30, rng, 1) * .85 + _fnoise(n, 30, 64, rng) * .15
    if kind == 'mud':
        return _fnoise(n, 2, 8, rng) * .7 + _fnoise(n, 16, 40, rng) * .3
    if kind == 'skin':
        return _fnoise(n, 40, 64, rng)
    if kind == 'rubber':
        return _fnoise(n, 3, 8, rng)
    raise KeyError(kind)


def detail_image(kind, n=128):
    """a shared tileable tangent-space normal map image for kind."""
    im = bpy.data.images.get('detail_' + kind)  # a new scene (read_factory_settings) drops old images
    if im is not None and _IMG.get(kind) == im.name: return im
    h = _height(kind, n).astype(np.float32)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5 * n / 16
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5 * n / 16
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + 1)
    rgb = np.stack([-dx / l, -dy / l, nz / l], -1) * .5 + .5
    px = np.concatenate([rgb, np.ones((n, n, 1), np.float32)], -1)
    im = bpy.data.images.new('detail_' + kind, n, n, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(px.ravel())
    path = os.path.join(_TMP, 'detail_%s.jpg' % kind)
    im.filepath_raw = path; im.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 88
    im.save(); im.source = 'FILE'; im.reload()
    _IMG[kind] = im.name
    return im


def add_detail(mat, kind, strength=.6):
    """plug a detail normal map into mat (glTF normalTexture, scale = strength)."""
    nt = mat.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = detail_image(kind); tx.interpolation = 'Linear'
    uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    nt.links.new(uvn.outputs['UV'], tx.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = strength
    nt.links.new(tx.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    mat['detail'] = kind


# ---------------------------------------------------------------- UVs
def box_uv(o, tile):
    """box-project UVs from the rest-pose world position: one texture tile every `tile` units."""
    me = o.data; mw = o.matrix_world
    while len(me.uv_layers): me.uv_layers.remove(me.uv_layers[0])  # one clean layer (joined curves bring extras)
    lay = me.uv_layers.new(name='UVMap'); me.uv_layers.active = lay; lay.active_render = True
    uv = lay.data
    nmat = mw.to_3x3()
    for p in me.polygons:
        n = (nmat @ p.normal); a = (abs(n.x), abs(n.y), abs(n.z))
        ax = a.index(max(a))
        for li in p.loop_indices:
            w = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: s, t = w.y, w.z
            elif ax == 1: s, t = w.x, w.z
            else: s, t = w.x, w.y
            uv[li].uv = (s / tile, t / tile)


# ---------------------------------------------------------------- AO
def _hemi(n_rays, seed=1):
    """cosine-weighted directions around +Z (a fixed, well spread set)."""
    rng = random.Random(seed); out = []
    for i in range(n_rays):
        u = (i + rng.random()) / n_rays; v = rng.random()
        r = math.sqrt(u); th = TAU * v
        out.append(Vector((r * math.cos(th), r * math.sin(th), math.sqrt(max(0, 1 - u)))))
    return out


def bake_ao(objs, dist, rays=40, strength=.75, skip=(), occluders=None, ground=True):
    """write ambient occlusion into a FLOAT_COLOR point attribute 'AO' on every mesh in objs.
    dist: how far (model units) a surface can shade another. skip: material names kept at full
    brightness (eye whites, glints). ground: the floor at z=0 also occludes (feet get grounded)."""
    dg = bpy.context.evaluated_depsgraph_get()
    occ = [o for o in (occluders or objs) if o.type == 'MESH']
    V, F = [], []
    for o in occ:
        me = o.data; mw = o.matrix_world; base = len(V)
        V += [mw @ v.co for v in me.vertices]
        F += [tuple(base + i for i in p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(V, F, epsilon=0.0)
    dirs = _hemi(rays)
    for o in objs:
        if o.type != 'MESH': continue
        me = o.data; mw = o.matrix_world; nm = mw.to_3x3().inverted().transposed()
        vm = [None] * len(me.vertices)
        for p in me.polygons:
            for vi in p.vertices:
                if vm[vi] is None and p.material_index < len(me.materials) and me.materials[p.material_index]:
                    vm[vi] = me.materials[p.material_index].name
        cols = np.ones((len(me.vertices), 4), np.float32)
        for vi, v in enumerate(me.vertices):
            if vm[vi] in skip: continue
            pw = mw @ v.co; n = (nm @ v.normal).normalized()
            t = n.orthogonal().normalized(); bt = n.cross(t)
            start = pw + n * (dist * .01)
            hit = 0.0
            for d in dirs:
                w = t * d.x + bt * d.y + n * d.z
                loc, _, _, h = bvh.ray_cast(start, w, dist)
                if loc is not None:
                    hit += 1 - (h / dist) ** 2 * .6
                elif ground and w.z < -1e-3:
                    h = -start.z / w.z
                    if h < dist: hit += (1 - (h / dist) ** 2 * .6) * .7
            ao = 1 - hit / len(dirs)
            ao = ao ** 1.3
            k = 1 - strength * (1 - ao)
            cols[vi, :3] = k
        a = me.color_attributes.get('AO') or me.color_attributes.new('AO', 'FLOAT_COLOR', 'POINT')
        a.data.foreach_set('color', cols.ravel())
        me.color_attributes.active_color = a; me.color_attributes.render_color_index = me.color_attributes.find('AO')


# ---------------------------------------------------------------- the pass
def finish(objs, mats, size, details, rough=None, ao=.75, skip_ao=('white',), occluders=None, tiles=6):
    """objs: meshes to finish (rest pose). mats: {name: material}. size: model height in units.
    details: {material name: (kind, strength)}. rough: {material name: roughness}."""
    rough = rough or {}
    for name, (kind, s) in details.items():
        if name in mats: add_detail(mats[name], kind, s)
    for name, r in rough.items():
        if name in mats: mats[name].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = r
    tile = size / tiles  # texture repeats from feet to head
    for o in objs:
        if o.type == 'MESH' and any(m and 'detail' in m for m in o.data.materials):
            box_uv(o, tile)
    bake_ao([o for o in objs if o.type == 'MESH'], size * .22, strength=ao, skip=set(skip_ao), occluders=occluders)


GLTF_KW = dict(export_vertex_color='ACTIVE', export_image_format='JPEG', export_jpeg_quality=85)


# ---------------------------------------------------------------- GLB slimming
def slim_glb(path):
    """after export: store COLOR_0 as normalised bytes (4 B a vertex instead of 8-16 B) and drop
    TEXCOORD_0 from primitives whose material has no texture. Rewrites the binary chunk."""
    import json, struct
    d = open(path, 'rb').read()
    jl = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + jl])
    bo = 20 + jl; bl = struct.unpack('<I', d[bo:bo + 4])[0]; bin_ = d[bo + 8:bo + 8 + bl]
    acc, bvs = j['accessors'], j['bufferViews']
    textured = {i for i, m in enumerate(j.get('materials', [])) if any(k in m for k in ('normalTexture', 'occlusionTexture', 'emissiveTexture')) or 'baseColorTexture' in m.get('pbrMetallicRoughness', {})}
    data = {}  # accessor index -> new bytes
    for me in j['meshes']:
        for p in me['primitives']:
            at = p['attributes']
            if 'TEXCOORD_0' in at and p.get('material') not in textured:
                del at['TEXCOORD_0']
            c = at.get('COLOR_0')
            if c is not None and acc[c]['componentType'] in (5126, 5123) and c not in data:
                a = acc[c]; bv = bvs[a['bufferView']]; n = a['count']; k = 4 if a['type'] == 'VEC4' else 3
                start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
                if a['componentType'] == 5126: f = np.frombuffer(bin_, np.float32, n * k, start).reshape(n, k)
                else: f = np.frombuffer(bin_, np.uint16, n * k, start).reshape(n, k) / 65535.0
                if k == 3: f = np.concatenate([f, np.ones((n, 1))], 1); a['type'] = 'VEC4'
                data[c] = (np.clip(f, 0, 1) * 255 + .5).astype(np.uint8).tobytes()
    used = set()
    for me in j['meshes']:
        for p in me['primitives']:
            used.update(p['attributes'].values())
            if 'indices' in p: used.add(p['indices'])
            for t in p.get('targets', []): used.update(t.values())
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s: used.add(s['inverseBindMatrices'])
    for an in j.get('animations', []):
        for sm in an['samplers']: used.update((sm['input'], sm['output']))
    # rebuild: one buffer view per used accessor + the views images use
    out = bytearray(); nbv = []; remap_bv = {}
    def push(b, extra):
        while len(out) % 4: out.append(0)
        v = dict(buffer=0, byteOffset=len(out), byteLength=len(b)); v.update(extra); out.extend(b); nbv.append(v); return len(nbv) - 1
    for i, a in enumerate(acc):
        if i not in used or 'bufferView' not in a: continue
        bv = bvs[a['bufferView']]
        if i in data:
            a['componentType'] = 5121; a['normalized'] = True; a.pop('byteOffset', None)
            a.pop('min', None); a.pop('max', None)
            a['bufferView'] = push(data[i], {'target': 34962}); continue
        comp = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[a['componentType']]
        nc = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', comp * nc)
        if stride != comp * nc: raise ValueError('interleaved views not handled')
        extra = {k: bv[k] for k in ('target',) if k in bv}
        a['bufferView'] = push(bin_[start:start + a['count'] * comp * nc], extra); a.pop('byteOffset', None)
    for im in j.get('images', []):
        if 'bufferView' in im:
            bv = bvs[im['bufferView']]; s0 = bv.get('byteOffset', 0)
            im['bufferView'] = push(bin_[s0:s0 + bv['byteLength']], {})
    j['accessors'] = [a for a in acc]  # unused accessors keep a stale view: drop them by index remap
    keep = [i for i, a in enumerate(acc) if i in used or 'bufferView' not in a]
    idx = {o: n for n, o in enumerate(keep)}
    j['accessors'] = [acc[i] for i in keep]
    for me in j['meshes']:
        for p in me['primitives']:
            p['attributes'] = {k: idx[v] for k, v in p['attributes'].items()}
            if 'indices' in p: p['indices'] = idx[p['indices']]
            if 'targets' in p: p['targets'] = [{k: idx[v] for k, v in t.items()} for t in p['targets']]
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s: s['inverseBindMatrices'] = idx[s['inverseBindMatrices']]
    for an in j.get('animations', []):
        for sm in an['samplers']: sm['input'] = idx[sm['input']]; sm['output'] = idx[sm['output']]
    while len(out) % 4: out.append(0)
    j['bufferViews'] = nbv; j['buffers'] = [{'byteLength': len(out)}]
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(out)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(out), 0x004E4942)); f.write(out)
