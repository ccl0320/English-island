"""Tileable surface textures for the island scenes (2026-11-13).

    python3 tools/blender/build_textures.py img/tex/

Writes small JPEGs the game multiplies with its theme colours, so every island keeps its own
palette: <kind>.jpg is a grey detail map (mean about 0.9, white = the plain theme colour). No normal
maps for the scene: derivative normal mapping shimmers on phone GPUs. Kinds: grass, path, rock, wood, bark, sand.
All are seamless (built in the frequency domain / with wrapped distances), 256 px, ~10-25 KB.
"""
import bpy, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from finish import _fnoise, _stretch

N = 256


def voronoi(n, cells, rng):
    """wrapped Voronoi: (distance to nearest point, distance to the second nearest, cell id)."""
    pts = rng.uniform(0, 1, (cells, 2))
    u = (np.arange(n) + .5) / n
    x, y = np.meshgrid(u, u)
    d = np.full((2, n, n), 9.0); idx = np.zeros((n, n), int)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(x - px); dx = np.minimum(dx, 1 - dx)
        dy = np.abs(y - py); dy = np.minimum(dy, 1 - dy)
        r = np.sqrt(dx * dx + dy * dy)
        closer = r < d[0]
        d[1] = np.where(closer, d[0], np.minimum(d[1], r))
        idx = np.where(closer, i, idx); d[0] = np.where(closer, r, d[0])
    return d[0], d[1], idx


def build(kind):
    rng = np.random.default_rng({'grass': 1, 'path': 2, 'rock': 3, 'wood': 4, 'bark': 5, 'sand': 6}[kind])
    u = np.arange(N) / N
    x, y = np.meshgrid(u, u)
    if kind == 'grass':  # soft light/dark patches + fine blades + a few clover clumps
        patches = _fnoise(N, 2, 6, rng)
        blades = _fnoise(N, 40, 128, rng)
        clumps = (_fnoise(N, 8, 16, rng) > .72) * .5
        alb = .78 + .14 * patches + .1 * blades - .06 * clumps
        h = blades * .7 + clumps * .6 + patches * .2
    elif kind == 'path':  # packed earth with pebbles
        f1, f2, ids = voronoi(N, 70, rng)
        peb = np.clip((f2 - f1) * 30, 0, 1) * (rng.uniform(0, 1, 70)[ids] > .45)
        dirt = _fnoise(N, 4, 40, rng)
        alb = .82 + .1 * dirt + .08 * peb * (rng.uniform(-1, 1, 70)[ids]) - .06 * (1 - np.clip((f2 - f1) * 60, 0, 1)) * (peb > 0)
        h = peb * .8 + dirt * .3
    elif kind == 'sand':
        g = _fnoise(N, 60, 128, rng); ripples = .5 + .5 * np.sin((y * 9 + _fnoise(N, 2, 4, rng) * .6) * np.pi * 2)
        alb = .86 + .08 * g + .05 * ripples
        h = g * .5 + ripples * .4
    elif kind == 'rock':  # cliff: layered strata, cracks, speckles
        warp = _fnoise(N, 2, 5, rng) * .15
        strata = .5 + .5 * np.sin((y + warp) * np.pi * 2 * 6)
        f1, f2, _ = voronoi(N, 24, rng)
        crack = 1 - np.clip((f2 - f1) * 25, 0, 1)
        spk = _fnoise(N, 50, 128, rng)
        alb = .8 + .08 * strata + .08 * spk - .22 * crack
        h = strata * .4 + spk * .3 - crack * .8
    elif kind == 'wood':  # 4 planks with grain and gaps, running along v
        plank = np.floor(x * 4)
        off = rng.uniform(0, 1, 4)[plank.astype(int)]
        grain = _stretch(N, 50, rng, 1) * .7 + .3 * (.5 + .5 * np.sin(((x * 4) % 1) * 40 + _fnoise(N, 2, 6, rng) * 6))
        gap = np.exp(-(((x * 4) % 1) * N / 4) ** 2 / 2) + np.exp(-((1 - (x * 4) % 1) * N / 4) ** 2 / 2)
        endc = np.exp(-(((y + off) % 1) * N) ** 2 / 3)
        alb = .8 + .1 * grain + .06 * (off - .5) - .3 * np.clip(gap + endc, 0, 1)
        h = grain * .4 - np.clip(gap + endc, 0, 1)
    elif kind == 'bark':  # vertical ridges
        ridges = _stretch(N, 14, rng, 1)
        fine = _fnoise(N, 30, 100, rng)
        alb = .72 + .2 * ridges + .08 * fine
        h = ridges * .9 + fine * .2
    alb = np.clip(alb, 0, 1)
    h = (h - h.min()) / (np.ptp(h) + 1e-9)
    s = {'grass': 3, 'path': 5, 'sand': 2, 'rock': 6, 'wood': 6, 'bark': 7}[kind]
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * s
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * s
    l = np.sqrt(dx * dx + dy * dy + 1)
    nrm = np.stack([-dx / l, -dy / l, 1 / l], -1) * .5 + .5
    return alb, nrm


def save(name, rgb, out):
    n = rgb.shape[0]
    px = np.concatenate([rgb, np.ones((n, n, 1))], -1).astype(np.float32)
    im = bpy.data.images.new(name, n, n, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(px[::-1].ravel())  # Blender rows go bottom-up
    im.filepath_raw = os.path.join(out, name + '.jpg'); im.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 82
    im.save()
    print('%-8s %5.1f KB' % (name, os.path.getsize(im.filepath_raw) / 1024))


if __name__ == '__main__':
    out = ([a for a in sys.argv[1:] if not a.startswith('-')] or ['img/tex'])[0]
    os.makedirs(out, exist_ok=True)
    for k in ('grass', 'path', 'sand', 'rock', 'wood', 'bark'):
        alb, nrm = build(k)
        save(k, np.repeat(alb[..., None], 3, -1), out)
