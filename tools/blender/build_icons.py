"""Build the picture objects (words, quiz pictures, island friends, shop items) as one GLB.

    python3 tools/blender/build_icons.py models/icons.glb
    node tools/blender/render_icons.js           # -> icons/<name>.png (needs a local server, see that file)

Each object is a top-level node named by its key in ICONS (index.html). Front is glTF +Z.
Numbers below are Y-up like the game: (x, up, front).
"""
import bpy, math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_models import Model, P, TAU, cut

M = Model('icons')
C = bpy.context
PROPS = {}


def prop(key):
    def deco(fn):
        PROPS[key] = fn; return fn
    return deco


def m(name, hexc=None, rough=.8): return M.m('%s_%s' % (name, hexc), hexc, rough)  # same name, different colour -> new material
def _w(fn, n):
    # n = number of positional args before `bone`; extra positionals go after bone=None
    def f(*a, **k):
        if len(a) > n: a = a[:n] + (k.pop('bone', None),) + a[n:]
        else: k.setdefault('bone', None)
        return fn('o', *a, **k)
    return f
ball = _w(M.ball, 3); lathe = _w(M.lathe, 2); cyl = _w(M.cyl, 4)
box = _w(M.rbox, 3); tube = _w(M.tube, 3); flat = _w(M.flat, 4)


def eyes(y, z, dx=.08, r=.035, smile=True, col='#2A1A14'):
    for sx in (-1, 1):
        ball(r, (sx * dx, y, z), m('eye', col, .3), scale=(1, 1.25, .6))
        ball(r * .35, (sx * dx + r * .3, y + r * .4, z + r * .4), m('white', '#FFFFFF', .4))
    ball(r * .9, (-dx * 2, y - r * 1.6, z - .02), m('cheek', '#FF9E9E', .9), scale=(1, .6, .3))
    ball(r * .9, (dx * 2, y - r * 1.6, z - .02), m('cheek', '#FF9E9E', .9), scale=(1, .6, .3))
    if smile:
        tube([(-dx * .6, y - r * 1.8, z), (0, y - r * 2.6, z + .01), (dx * .6, y - r * 1.8, z)], .012, m('eye', col, .3), res=4, bev=1)


# ---------------- home ----------------
@prop('bed')
def _():
    wood, sheet, blanket = m('wood', '#C98B55'), m('sheet', '#FFFFFF'), m('blanket', '#7C8CE0')
    box((1.0, .22, .62), (0, .25, 0), wood, bevel=.04)
    box((.08, .62, .66), (-.5, .4, 0), wood, bevel=.03); box((.08, .4, .66), (.5, .3, 0), wood, bevel=.03)
    box((.92, .1, .58), (0, .4, 0), sheet, bevel=.04)
    box((.62, .12, .62), (.12, .45, 0), blanket, bevel=.05)
    ball(.16, (-.32, .5, 0), sheet, scale=(1, .45, 1.5))
    for x in (-.45, .45):
        for z in (-.26, .26): cyl(.035, .16, (x, .08, z), wood)


@prop('sofa')
def _():
    c, d = m('sofa', '#E46B6B'), m('sofa_dark', '#C95454')
    box((1.0, .3, .5), (0, .3, 0), c, bevel=.08); box((1.0, .4, .16), (0, .55, -.2), d, bevel=.07)
    for x in (-.5, .5): box((.16, .42, .52), (x, .38, 0), d, bevel=.07)
    for x in (-.2, .2): box((.38, .1, .4), (x, .48, .04), c, bevel=.05)
    for x in (-.42, .42):
        for z in (-.18, .18): cyl(.03, .1, (x, .07, z), m('wood', '#8A5A33'))


@prop('chair')
def _():
    w = m('wood', '#C98B55')
    box((.5, .08, .5), (0, .45, 0), w, bevel=.02); box((.5, .5, .07), (0, .75, -.22), w, bevel=.02)
    box((.4, .2, .1), (0, .68, -.21), m('cushion', '#7CC67A'), bevel=.04)
    for x in (-.2, .2):
        for z in (-.2, .2): cyl(.03, .42, (x, .21, z), w)


@prop('table')
def _():
    w = m('wood', '#C98B55')
    box((1.0, .07, .6), (0, .5, 0), w, bevel=.02)
    for x in (-.42, .42):
        for z in (-.24, .24): cyl(.035, .48, (x, .24, z), w)
    for x in (-.25, .25):
        lathe([(0, .54), (.14, .54), (.16, .57)], m('plate', '#FFFFFF', .3), pos=(x, 0, .05))
        ball(.06, (x, .58, .05), m('food', '#F2A93B'), scale=(1, .5, 1))


@prop('bath')
def _():
    w = m('tub', '#FFFFFF', .3)
    t = lathe([(0, .05), (.42, .06), (.5, .2), (.52, .45), (.48, .47)], w, axis='y')
    t.scale = (1.15, 1, .7)
    ball(.4, (0, .45, 0), m('water', '#8FD3F5', .1), scale=(1.15, .1, .65))
    for i in range(5):
        ball(random.uniform(.06, .11), (random.uniform(-.35, .35), .5 + random.uniform(0, .1), random.uniform(-.15, .15)), m('foam', '#F4FBFF', .6))
    for x in (-.4, .4): ball(.06, (x, .04, 0), m('gold', '#E9B83A', .35))
    cyl(.025, .35, (.5, .65, 0), m('metal', '#B8C4CC', .3)); cyl(.03, .14, (.43, .82, 0), m('metal', '#B8C4CC', .3), axis='x')


@prop('kitchen')
def _():
    pan, egg = m('pan', '#3B3F47', .4), m('egg', '#FFFFFF', .5)
    lathe([(0, 0), (.36, 0), (.4, .1), (.38, .11), (0, .03)], pan, pos=(0, .3, 0))
    cyl(.035, .45, (.58, .35, 0), m('handle', '#8A5A33'), axis='x')
    ball(.22, (0, .35, 0), egg, scale=(1.1, .12, 1)); ball(.09, (0, .38, .02), m('yolk', '#F7B52C', .4), scale=(1, .6, 1))


@prop('closet')
def _():
    w, d = m('closet', '#B97A4A'), m('closet_dark', '#9A6037')
    box((.7, 1.0, .4), (0, .52, 0), w, bevel=.03)
    box((.01, .9, .02), (0, .53, .2), d, bevel=0)
    for x in (-.06, .06): ball(.03, (x, .55, .21), m('gold', '#E9B83A', .35))
    box((.74, .06, .44), (0, 1.03, 0), d, bevel=.02)
    for x in (-.28, .28): cyl(.03, .05, (x, .01, .1), d)


@prop('picture')
def _():
    box((.8, .62, .06), (0, .5, 0), m('frame', '#D8A047', .4), bevel=.03)
    box((.66, .48, .02), (0, .5, .03), m('sky', '#9BD6F2'), bevel=0)
    flat([(-.33, -.24), (-.1, .06), (.06, -.1), (.2, .1), (.33, -.24)], .01, (0, .5, .045), m('hill', '#5DBB63'))
    ball(.06, (.2, .64, .045), m('sun', '#F7D03C'), scale=(1, 1, .2))


@prop('mirror')
def _():
    lathe([(0, -.02), (.3, -.02), (.33, 0), (.3, .02), (0, .02)], m('frame', '#D8A047', .4), pos=(0, .6, 0), axis='z').scale = (1, 1.35, 1)
    lathe([(0, 0), (.27, 0), (0, .025)], m('glass', '#D5EEF7', .05), pos=(0, .6, .005), axis='z').scale = (1, 1.35, 1)
    tube([(-.12, .78, .04), (-.04, .88, .04)], .02, m('white', '#FFFFFF', .4), res=1, bev=1)
    box((.3, .06, .12), (0, .08, 0), m('frame', '#D8A047', .4), bevel=.02); cyl(.025, .14, (0, .16, 0), m('frame', '#D8A047', .4))


@prop('bookcase')
def _():
    w = m('wood', '#B97A4A')
    for x in (-.38, .38): box((.06, 1.0, .3), (x, .5, -.02), w, bevel=.015)
    for y in (.03, .97): box((.82, .06, .3), (0, y, -.02), w, bevel=.015)
    box((.76, .94, .04), (0, .5, -.15), m('wood_dark', '#8A5A33'), bevel=0)
    cols = ['#E05B5B', '#4A90D9', '#F2C230', '#5DBB63', '#A56BD6', '#F08C2E']
    for row, y in enumerate((.27, .72)):
        x = -.32
        for i in range(6):
            h = random.uniform(.24, .32); bw = random.uniform(.07, .1)
            box((bw, h, .2), (x + bw / 2, y - .14 + h / 2, 0), m('book%d' % i, cols[(i + row * 2) % 6]), bevel=.01)
            x += bw + .015
    box((.74, .04, .26), (0, .5, 0), w, bevel=.01)


@prop('door')
def _():
    box((.7, 1.1, .1), (0, .55, 0), m('door', '#C8784A'), bevel=.03)
    for y in (.3, .78): box((.5, .34, .03), (0, y, .055), m('door_dark', '#A85F38'), bevel=.02)
    ball(.045, (.24, .55, .08), m('gold', '#E9B83A', .35))
    box((.82, .06, .14), (0, 1.12, 0), m('frame_w', '#F3E6CF'), bevel=.02)


@prop('stairs')
def _():
    w = m('wood', '#C98B55'); c = m('carpet', '#C85A8A')
    for i in range(5):
        box((.7, .18 * (i + 1), .2), (0, .09 * (i + 1), .4 - i * .2), w, bevel=.015)
        box((.5, .02, .2), (0, .18 * (i + 1) + .005, .4 - i * .2), c, bevel=0)
    tube([(.38, .45, .5), (.38, 1.15, -.4)], .03, m('rail', '#8A5A33'), res=1, bev=1)
    for i in range(4): cyl(.018, .3, (.38, .3 + .17 * i + .15, .42 - i * .22), m('rail', '#8A5A33'))


@prop('wall')
def _():
    for row in range(4):
        for i in range(4):
            x = -.42 + i * .28 + (.14 if row % 2 else 0)
            if x > .45: continue
            box((.26, .16, .2), (x, .1 + row * .18, 0), m('brick%d' % (row % 2), '#C8553D' if (row + i) % 3 else '#B44A35'), bevel=.02)


@prop('floor')
def _():
    for i in range(3):
        for j in range(3):
            box((.32, .06, .32), (-.33 + i * .33, .03, -.33 + j * .33), m('tile%d' % ((i + j) % 2), '#C98B55' if (i + j) % 2 else '#A86F40'), bevel=.015)


@prop('yard')
def _():
    ball(.5, (0, 0, 0), m('grass', '#7CC67A'), scale=(1, .12, 1))
    cyl(.07, .45, (0, .25, 0), m('trunk', '#8A5A33'), 8)
    for (x, y, z, r) in [(0, .7, 0, .28), (-.18, .58, .05, .2), (.18, .6, .02, .21), (0, .9, -.02, .2)]:
        ball(r, (x, y, z), m('leaf', '#4FAE4F'))
    for x, z in ((-.35, .2), (.3, .3), (.35, -.2)): ball(.05, (x, .07, z), m('flower%d' % int(x * 10), '#FF7FA8' if x < 0 else '#FFD84A'))


@prop('house')
def _():
    box((.7, .5, .6), (0, .25, 0), m('wall_h', '#FFF1DE'), bevel=.02)
    r = lathe([(.62, .5), (0, .92)], m('roof', '#E0473F'), seg=4); r.rotation_euler[2] = math.pi / 4
    box((.16, .26, .03), (0, .13, .3), m('door', '#C8784A'), bevel=.02)
    box((.14, .14, .03), (.2, .32, .3), m('window', '#9BD6F2'), bevel=.01)
    box((.1, .2, .1), (.2, .85, 0), m('chimney', '#B44A35'), bevel=.01)


@prop('dining')
def _():
    PROPS['table']()
    for x in (-.65, .65):
        w = m('wood', '#C98B55')
        box((.3, .05, .3), (x, .32, 0), w, bevel=.02); box((.05, .32, .3), (x + (.14 if x > 0 else -.14), .5, 0), w, bevel=.02)
        for dx in (-.11, .11):
            for z in (-.11, .11): cyl(.02, .3, (x + dx, .15, z), w)


@prop('cushion')
def _():
    b = box((.8, .6, .3), (0, .4, 0), m('cushion_y', '#F6C744'), bevel=.14, segs=4)
    for v in b.data.vertices:
        x, h = v.co.x / .42, (v.co.z - .4) / .32
        v.co.y *= 1 + 1.0 * max(0, 1 - x * x) * max(0, 1 - h * h)
    for sx in (-1, 1):
        for sy in (-1, 1): ball(.05, (sx * .4, .4 + sy * .3, 0), m('tassel', '#E3AC2A'))


# ---------------- words that are ideas ----------------
@prop('up')
def _():
    PROPS['stairs']()
    flat([(-.12, 0), (-.12, .3), (-.26, .3), (0, .58), (.26, .3), (.12, .3), (.12, 0)], .1, (-.55, .5, .2), m('arrow_g', '#3FB65A'))


@prop('down')
def _():
    PROPS['stairs']()
    flat([(-.12, 0), (-.12, -.3), (-.26, -.3), (0, -.58), (.26, -.3), (.12, -.3), (.12, 0)], .1, (-.55, .85, .2), m('arrow_b', '#3B8FE0'))


@prop('noisy')
def _():
    o = lathe([(.08, 0), (.1, .1), (.32, .5), (.33, .52)], m('horn', '#E0473F'), seg=16, axis='x', pos=(-.2, .5, 0))
    cyl(.09, .12, (-.24, .5, 0), m('horn_d', '#B8382F'), axis='x')
    box((.08, .2, .08), (-.12, .36, 0), m('horn_d', '#B8382F'), bevel=.02)
    for i, r in enumerate((.25, .38, .51)):
        tube([(.25 + r * .5, .5 + r * .6, 0), (.3 + r * .7, .5, 0), (.25 + r * .5, .5 - r * .6, 0)], .02, m('wave', '#F2B630'), res=4, bev=1)


@prop('quiet')
def _():
    ball(.38, (0, .5, 0), m('face_y', '#F7D24A'), sub=3)
    for sx in (-1, 1): tube([(sx * .17, .58, .33), (sx * .12, .61, .35), (sx * .07, .58, .34)], .02, m('eye', '#2A1A14', .3), res=3, bev=1)
    ball(.035, (0, .37, .36), m('mouth', '#B5323F', .6), scale=(1.4, .6, .5))
    cyl(.05, .32, (0, .42, .4), m('finger', '#F8D5B8', .7)); ball(.052, (0, .58, .4), m('finger', '#F8D5B8', .7))


@prop('clean')
def _():
    for (x, y, z, r) in [(0, .45, 0, .26), (-.3, .3, .1, .16), (.28, .7, 0, .14), (.25, .22, .1, .1), (-.2, .78, 0, .09)]:
        ball(r, (x, y, z), m('bubble', '#BFE8FF', .05), sub=3)
        ball(r * .25, (x - r * .35, y + r * .4, z + r * .75), m('white', '#FFFFFF', .4), scale=(1, 1, .5))
    for (x, y) in [(.4, .45), (-.42, .6)]:
        flat([(math.cos(TAU * i / 8 + .4) * (.08 if i % 2 == 0 else .025), math.sin(TAU * i / 8 + .4) * (.08 if i % 2 == 0 else .025)) for i in range(8)], .02, (x, y, .1), m('spark', '#FFE27A'))


@prop('dirty')
def _():
    ball(.38, (0, .04, 0), m('mud', '#8A5A3A'), scale=(1.2, .2, 1))
    for i in range(6):
        a = i / 6 * TAU
        ball(random.uniform(.07, .11), (math.cos(a) * .5, .03, math.sin(a) * .45), m('mud', '#8A5A3A'), scale=(1, .4, 1))
    ball(.16, (.05, .14, 0), m('mud_d', '#6E452B'), scale=(1.2, .7, 1))
    for i, (x, z) in enumerate([(-.2, .1), (.25, -.05)]): ball(.04, (x, .45 + i * .1, z), m('fly', '#333333'))


# ---------------- animals ----------------
def quad(body, head, spots=None, leg='#6E4A34', ears='side', horn=None, tail=None, mane=None, size=1., snout=None, eye=.035):
    b = ball(.33 * size, (0, .5 * size, 0), m('a_body', body), scale=(1.35, .85, .9))
    hy, hz = .72 * size, .38 * size
    ball(.22 * size, (0, hy, hz), m('a_head', head), scale=(1, 1, 1))
    if snout: ball(.13 * size, (0, hy - .07 * size, hz + .17 * size), m('a_snout', snout), scale=(1.2, .8, .7))
    for sx in (-1, 1):
        for z in (-.2, .2):
            cyl(.075 * size, .3 * size, (sx * .17 * size, .17 * size, z * size), m('a_leg', leg), 10)
            cyl(.08 * size, .06 * size, (sx * .17 * size, .03 * size, z * size), m('hoof', '#4A3A32'), 10)
        if ears == 'side': ball(.08 * size, (sx * .22 * size, hy + .08 * size, hz - .02), m('a_head', head), scale=(1.4, .5, .8))
        elif ears == 'up': ball(.07 * size, (sx * .1 * size, hy + .22 * size, hz - .02), m('a_head', head), scale=(.6, 1.6, .5))
        elif ears == 'round': ball(.08 * size, (sx * .15 * size, hy + .17 * size, hz - .02), m('a_ear', head), scale=(1, 1, .5))
        if horn: tube([(sx * .08 * size, hy + .18 * size, hz - .04), (sx * .14 * size, hy + .32 * size, hz - .1)], .03 * size, m('horn', horn), [1, .3], res=2, bev=1)
    if spots:
        for (x, y, z, r) in spots: ball(r * size, (x * size, y * size, z * size), m('a_spot', '#3A3330'), scale=(1, .8, .5))
    if tail: tube([(0, .55 * size, -.42 * size), (0, .45 * size, -.52 * size), (0, .35 * size, -.5 * size)], .03 * size, m('a_tail', tail), res=3, bev=1)
    if mane:
        for i in range(4): ball(.07 * size, (0, hy + .15 * size - i * .08 * size, hz - .14 * size - i * .06 * size), m('mane', mane))
    eyes(hy + .03 * size, hz + .2 * size, .08 * size, eye * size, smile=snout is None)


@prop('cow')
def _(): quad('#FFFFFF', '#FFFFFF', [(.2, .6, .25, .1), (-.18, .55, -.15, .12), (.1, .62, -.28, .09)], '#FFFFFF', horn='#F3E6CF', snout='#F7B8B8', tail='#FFFFFF')


@prop('horse')
def _(): quad('#B8764A', '#B8764A', None, '#8A5230', ears='up', mane='#5A3420', snout='#D6A37A', tail='#5A3420')


@prop('donkey')
def _(): quad('#9A9AA5', '#9A9AA5', None, '#6E6E78', ears='up', mane='#4A4A52', snout='#D9D9DE', tail='#4A4A52')


@prop('goat')
def _():
    quad('#F3EEE6', '#F3EEE6', None, '#D8CFC2', horn='#B39270', snout='#F2D6CF', tail='#F3EEE6')
    lathe([(.04, 0), (0, -.14)], m('beard', '#E8E0D4'), pos=(0, .6, .62))


@prop('sheep')
def _():
    wool = m('wool', '#FBF3E8')
    for i in range(14):
        a = i / 14 * TAU
        ball(.17, (math.cos(a) * .3, .5 + math.sin(a * 2) * .06, math.sin(a) * .22), wool)
    ball(.3, (0, .55, 0), wool, scale=(1.2, .9, .9))
    ball(.17, (0, .62, .32), m('face', '#3A3330'), scale=(1, 1.1, .9))
    for sx in (-1, 1):
        for z in (-.15, .15): cyl(.05, .3, (sx * .16, .15, z), m('a_leg', '#3A3330'), 8)
        ball(.06, (sx * .18, .7, .3), m('face', '#3A3330'), scale=(1.4, .5, .8))
    for sx in (-1, 1): ball(.03, (sx * .06, .66, .46), m('white', '#FFFFFF', .4))


@prop('chicken')
def _():
    w = m('hen', '#FFFFFF')
    ball(.3, (0, .45, 0), w, scale=(1, .9, 1.1)); ball(.17, (0, .78, .15), w)
    for i, z in enumerate((.12, .18, .24)): ball(.045, (0, .95 - i * .01, z), m('comb', '#E0473F'))
    lathe([(.05, 0), (0, .09)], m('beak', '#F2B630', .5), axis='z', pos=(0, .77, .3))
    ball(.035, (0, .7, .29), m('comb', '#E0473F'), scale=(1, 1.4, .6))
    for sx in (-1, 1):
        ball(.15, (sx * .26, .48, -.02), w, scale=(.4, .9, 1.1))
        cyl(.02, .2, (sx * .1, .1, 0), m('legs', '#F2B630', .5), 6)
        ball(.025, (sx * .07, .82, .27), m('eye', '#2A1A14', .3))
    for i in range(3): ball(.08, (0, .62 + i * .04, -.3 - i * .03), w, scale=(.5, 1, .6))


@prop('chick')
def _():
    y = m('chick', '#FFD84A')
    ball(.3, (0, .35, 0), y); ball(.2, (0, .7, .05), y)
    lathe([(.05, 0), (0, .08)], m('beak', '#F28A2E', .5), axis='z', pos=(0, .68, .23))
    for sx in (-1, 1): ball(.11, (sx * .28, .38, 0), y, scale=(.4, .8, 1)); cyl(.02, .1, (sx * .08, .05, .05), m('beak', '#F28A2E', .5), 6)
    eyes(.74, .22, .07, .028, smile=False)
    ball(.05, (0, .92, .02), y, scale=(.6, 1, .6))


@prop('mouse')
def _():
    g = m('mouse', '#B9BCC4')
    ball(.28, (0, .3, 0), g, scale=(.9, .9, 1.25)); ball(.18, (0, .45, .3), g)
    for sx in (-1, 1): ball(.12, (sx * .15, .63, .25), m('ear_pink', '#F5B3C2'), scale=(1, 1, .3))
    ball(.035, (0, .42, .48), m('nose', '#F07C9A'))
    tube([(0, .25, -.33), (0, .2, -.55), (.15, .3, -.65)], .018, m('ear_pink', '#F5B3C2'), res=4, bev=1)
    eyes(.5, .44, .07, .028, smile=False)


@prop('bird')
def _():
    b = m('bird', '#5AB0E8')
    ball(.26, (0, .45, 0), b, scale=(1, .95, 1.1)); ball(.15, (0, .7, .1), b)
    ball(.16, (0, .38, .1), m('belly_b', '#F7E9C8'), scale=(.8, .8, .6))
    lathe([(.04, 0), (0, .08)], m('beak', '#F2B630', .5), axis='z', pos=(0, .68, .24))
    for sx in (-1, 1): ball(.14, (sx * .24, .47, -.02), m('wing_b', '#3E8FCC'), scale=(.35, .8, 1.1)); cyl(.015, .16, (sx * .06, .1, 0), m('beak', '#F2B630', .5), 6)
    flat([(-.1, 0), (.1, 0), (.14, -.2), (-.14, -.2)], .03, (0, .45, -.28), m('wing_b', '#3E8FCC'), plane='xz')
    eyes(.73, .23, .06, .022, smile=False)


@prop('cat')
def _():
    o = m('cat', '#F2A65A')
    ball(.26, (0, .32, 0), o, scale=(.9, 1, 1)); ball(.24, (0, .7, .05), o)
    for sx in (-1, 1): lathe([(.07, 0), (0, .13)], o, seg=4, pos=(sx * .13, .88, .05))
    ball(.1, (0, .63, .24), m('muzzle', '#FFF1DE'), scale=(1.3, .8, .6)); ball(.025, (0, .67, .3), m('nose', '#F07C9A'))
    tube([(.2, .2, -.15), (.4, .35, -.2), (.38, .6, -.2)], .04, o, res=4, bev=1)
    eyes(.74, .25, .09, .032, smile=False)
    for sx in (-1, 1):
        for i in (-1, 1): tube([(sx * .1, .64 + i * .015, .27), (sx * .25, .66 + i * .04, .25)], .006, m('eye', '#2A1A14', .3), res=1, bev=0)


@prop('dog')
def _():
    o, d = m('dog', '#D9A066'), m('dog_d', '#8A5A33')
    ball(.26, (0, .32, 0), o, scale=(.95, 1, 1.05)); ball(.25, (0, .7, .05), o)
    for sx in (-1, 1): ball(.11, (sx * .25, .66, .02), d, scale=(.5, 1.3, .7))
    ball(.11, (0, .62, .25), m('muzzle', '#FFF1DE'), scale=(1.2, .8, .7)); ball(.04, (0, .67, .34), m('nose_d', '#2A1A14', .3))
    ball(.04, (0, .55, .3), m('tongue', '#F07C86'), scale=(1, .6, .5))
    tube([(0, .35, -.25), (0, .55, -.38)], .04, o, res=2, bev=1)
    eyes(.76, .25, .09, .032, smile=False)


@prop('bunny')
def _():
    w = m('bunny', '#FFFFFF')
    ball(.27, (0, .3, 0), w); ball(.22, (0, .66, .05), w)
    for sx in (-1, 1):
        ball(.07, (sx * .09, 1.0, 0), w, scale=(.8, 2.6, .5)); ball(.045, (sx * .09, 1.0, .03), m('ear_pink', '#F5B3C2'), scale=(.7, 2.8, .3))
    ball(.025, (0, .64, .27), m('nose', '#F07C9A')); ball(.07, (0, .3, -.27), w)
    eyes(.7, .24, .08, .03, smile=False)


@prop('unicorn')
def _():
    quad('#FFFFFF', '#FFFFFF', None, '#F2D6E8', ears='up', mane='#C79BEA', snout='#FCE4EC', tail='#9BD6F2')
    lathe([(.05, 0), (0, .28)], m('horn_g', '#F7D03C', .35), seg=8, pos=(0, .9, .42))


@prop('bee')
def _():
    ball(.3, (0, .5, 0), m('bee', '#F7C531'), scale=(1, .9, 1.2))
    for z in (-.1, .1): lathe([(.29, -.03), (.31, 0), (.29, .03)], m('stripe', '#2A1A14', .5), pos=(0, .5, z), axis='z', cap=False)
    for sx in (-1, 1):
        ball(.17, (sx * .18, .82, -.05), m('wing', '#DFF3FF', .1), scale=(.7, 1, .35))
        tube([(sx * .07, .75, .25), (sx * .12, .9, .3)], .012, m('stripe', '#2A1A14', .5), res=1, bev=0)
        ball(.03, (sx * .12, .9, .3), m('stripe', '#2A1A14', .5))
    eyes(.55, .34, .1, .035)
    lathe([(.05, 0), (0, -.1)], m('stripe', '#2A1A14', .5), axis='z', pos=(0, .5, -.35))


@prop('owl')
def _():
    o = m('feather', '#F08C2E')
    ball(.4, (0, .45, 0), o, scale=(1, .95, .9), sub=3); ball(.28, (0, .35, .18), m('belly', '#F7DDB0'), scale=(1, 1, .6))
    for sx in (-1, 1):
        ball(.1, (sx * .25, .82, 0), o, scale=(.7, 1.3, .7))
        ball(.12, (sx * .14, .55, .3), m('white', '#FFFFFF', .4), scale=(1, 1, .5)); ball(.07, (sx * .14, .55, .36), m('eye', '#2A1A14', .3), scale=(1, 1, .5))
    lathe([(.05, 0), (0, -.08)], m('beak', '#F2B630', .5), axis='y', pos=(0, .48, .38))


# ---------------- people ----------------
def person(skin='#F8D5B8', hair='#8B5634', shirt='#4A90D9', style='short', beard=False, glasses=False, apron=None, tie=None, h=1.0):
    S = m('p_skin', skin)
    lathe([(0, .02), (.24, .02), (.26, .1), (.2, .4), (.12, .48), (0, .5)], m('p_shirt' + shirt, shirt), seg=16)
    if apron: box((.26, .3, .02), (0, .25, .2), m('apron', apron), bevel=.01)
    if tie: box((.05, .2, .02), (0, .34, .2), m('tie', tie), bevel=.01)
    for sx in (-1, 1): ball(.06, (sx * .25, .2, .04), S)
    ball(.27, (0, .72, 0), S, sub=3)
    H = m('p_hair' + hair, hair)
    if style == 'bald':
        for sx in (-1, 1): ball(.1, (sx * .22, .74, -.06), H, scale=(.6, .8, .9))
    elif style == 'bun':
        hb = ball(.285, (0, .76, -.03), H, sub=3); cut(hb, lambda x, y, z: not (z > .05 and y < .86))
        ball(.12, (0, 1.02, -.08), H)
    elif style == 'pigtails':
        hb = ball(.285, (0, .76, -.03), H, sub=3); cut(hb, lambda x, y, z: not (z > .05 and y < .86))
        for sx in (-1, 1): ball(.1, (sx * .3, .64, -.05), H); ball(.035, (sx * .25, .7, -.05), m('ribbon', '#E0473F'))
    else:
        hb = ball(.285, (0, .78, -.03), H, sub=3); cut(hb, lambda x, y, z: not (z > .08 and y < .88))
        for x in (-.12, 0, .12): ball(.08, (x, .93, .18), H, scale=(1.2, .7, .7))
    if beard:
        ball(.18, (0, .6, .14), m('beard', '#EDEDED'), scale=(1.2, .9, .8))
        ball(.07, (0, .66, .25), m('moustache', '#EDEDED'), scale=(1.8, .5, .6))
    eyes(.74, .25, .09, .035, smile=not beard)
    if glasses:
        G = m('glasses', '#5A4A3A', .4)
        for sx in (-1, 1): lathe([(.055, -.005), (.06, 0), (.055, .005)], G, pos=(sx * .09, .74, .27), axis='z', cap=False)
        tube([(-.035, .75, .275), (.035, .75, .275)], .008, G, res=1, bev=0)


@prop('grandpa')
def _(): person(hair='#DDDDDD', shirt='#7A8F5A', style='bald', beard=True, glasses=True)


@prop('grandma')
def _(): person(hair='#E5E5E5', shirt='#C77DB8', style='bun', glasses=True)


@prop('dad')
def _(): person(hair='#4A3020', shirt='#4A7CC8', tie='#E0473F')


@prop('mom')
def _(): person(hair='#7A4A2A', shirt='#E06B8F', style='bun', apron='#FFFFFF')


@prop('boy')
def _(): person(hair='#5A3A22', shirt='#F2A93B')


@prop('girl')
def _(): person(hair='#8B5634', shirt='#9B6BD6', style='pigtails')


# ---------------- fruit ----------------
def leafy(y, z=0, x=0):
    cyl(.025, .12, (x, y + .05, z), m('stem', '#8A5A33'), 6)
    ball(.1, (x + .1, y + .08, z), m('leaf', '#4FAE4F'), scale=(1.2, .2, .55))


@prop('apple')
def _():
    lathe([(0, .02), (.25, .05), (.36, .2), (.36, .38), (.28, .55), (.1, .58), (0, .53)], m('apple', '#E0473F', .35), seg=20)
    ball(.06, (-.15, .42, .28), m('white', '#FFFFFF', .4), scale=(1, 1.4, .4)); leafy(.55)


@prop('banana')
def _():
    for i, a in enumerate((-.35, 0, .35)):
        pts = [(math.sin(a) * .15, .1, math.cos(a) * .05), (math.sin(a) * .3 - .25, .4, math.cos(a) * .1), (math.sin(a) * .2 - .1, .8, 0)]
        tube(pts, .09, m('banana', '#F7D03C', .5), [.4, 1, .5], res=6, bev=3)
    cyl(.04, .1, (-.08, .82, 0), m('stem_b', '#6E5A2A'), 6)


@prop('peach')
def _():
    ball(.33, (0, .38, 0), m('peach', '#FFB08A', .7), scale=(1, .95, 1), sub=3)
    ball(.2, (.12, .5, .18), m('peach_r', '#FF8A80', .7), scale=(1, 1, .6)); leafy(.68)
    tube([(0, .7, .05), (.05, .38, .33), (0, .08, .1)], .012, m('peach_r', '#FF8A80', .7), res=4, bev=1)


@prop('lemon')
def _():
    ball(.3, (0, .35, 0), m('lemon', '#F7E04A', .5), scale=(1.35, 1, 1), sub=3)
    for sx in (-1, 1): ball(.06, (sx * .4, .35, 0), m('lemon', '#F7E04A', .5), scale=(1, .7, .7))
    ball(.1, (-.1, .5, .2), m('white', '#FFFFFF', .4), scale=(1.2, .6, .3)); ball(.09, (.1, .6, 0), m('leaf', '#4FAE4F'), scale=(1.3, .2, .6))


@prop('pineapple')
def _():
    lathe([(0, 0), (.24, .03), (.28, .2), (.26, .45), (.18, .58), (0, .6)], m('pine', '#E8A53A', .6), seg=16)
    for i in range(18):
        a = i / 6 * TAU; y = .12 + (i // 6) * .15
        ball(.04, (math.cos(a + i) * .27, y, math.sin(a + i) * .27), m('pine_d', '#B87A22', .6), scale=(1, 1, .5))
    for i in range(7):
        a = i / 7 * TAU
        tube([(0, .58, 0), (math.cos(a) * .12, .82, math.sin(a) * .12), (math.cos(a) * .2, .95, math.sin(a) * .2)], .04, m('leaf', '#4FAE4F'), [1, .7, .2], res=3, bev=1)


@prop('watermelon')
def _():
    w = ball(.38, (0, .38, 0), m('melon', '#3E9A4A', .5), scale=(1.15, 1, 1), sub=3)
    cut(w, lambda x, y, z: z < .05)
    flat([(math.cos(a) * .43, math.sin(a) * .38) for a in [i / 24 * TAU for i in range(24)]], .02, (0, .38, .04), m('melon_r', '#F25A5A'))
    for i in range(8):
        a = i / 8 * TAU
        ball(.025, (math.cos(a) * .22, .38 + math.sin(a) * .2, .06), m('seed', '#2A1A14', .4), scale=(.7, 1, .4))


@prop('pear')
def _():
    lathe([(0, .02), (.26, .05), (.33, .18), (.3, .33), (.2, .48), (.15, .6), (.08, .68), (0, .7)], m('pear', '#A8D65A', .6), seg=18)
    leafy(.68)


@prop('strawberry')
def _():
    lathe([(0, .05), (.12, .1), (.25, .3), (.28, .45), (.22, .55), (0, .57)], m('straw', '#E83E4C', .5), seg=16)
    for i in range(16):
        a = i * 2.4; y = .18 + (i % 4) * .09; r = [.17, .24, .27, .25][i % 4]
        ball(.015, (math.cos(a) * r, y, math.sin(a) * r), m('seed_y', '#F7E04A', .5))
    for i in range(5):
        a = i / 5 * TAU
        ball(.07, (math.cos(a) * .12, .58, math.sin(a) * .12), m('leaf', '#4FAE4F'), scale=(1.4, .3, .7))


@prop('mango')
def _():
    ball(.3, (0, .38, 0), m('mango', '#F7A531', .55), scale=(1.3, 1, .9), sub=3)
    ball(.18, (.18, .5, .1), m('mango_r', '#F26B3A', .55), scale=(1, 1, .7)); leafy(.68, x=-.2)


# ---------------- toys & things ----------------
@prop('ball')
def _():
    ball(.35, (0, .35, 0), m('ball_w', '#FFFFFF', .5), sub=3)
    for (x, y, z) in [(0, .35, .34), (.29, .5, .14), (-.29, .5, .14), (.2, .15, .22), (-.2, .15, .22), (0, .68, 0)]:
        ball(.1, (x, y, z), m('ball_b', '#2A2A2A', .5), scale=(1, 1, .4))


@prop('teddy')
def _():
    b = m('teddy', '#C88A55')
    ball(.26, (0, .3, 0), b); ball(.22, (0, .68, .02), b)
    for sx in (-1, 1):
        ball(.08, (sx * .17, .86, 0), b); ball(.09, (sx * .25, .35, .05), b); ball(.1, (sx * .14, .08, .1), b)
    ball(.16, (0, .3, .15), m('teddy_l', '#F0CFA3'), scale=(1, 1, .5)); ball(.08, (0, .62, .2), m('teddy_l', '#F0CFA3'))
    ball(.025, (0, .65, .27), m('nose_d', '#2A1A14', .3)); eyes(.72, .2, .07, .025, smile=False)
    ball(.05, (0, .5, .2), m('bow_r', '#E0473F'), scale=(2, .8, .5))


@prop('book')
def _():
    box((.6, .75, .14), (0, .4, 0), m('cover', '#E0473F'), bevel=.025)
    box((.56, .7, .1), (.03, .4, 0), m('pages', '#FFF8E8'), bevel=.01)
    box((.6, .75, .02), (0, .4, .06), m('cover', '#E0473F'), bevel=.01)
    flat([(math.cos(TAU * i / 10 + math.pi / 2) * (.12 if i % 2 == 0 else .05), math.sin(TAU * i / 10 + math.pi / 2) * (.12 if i % 2 == 0 else .05)) for i in range(10)], .01, (0, .45, .075), m('gold', '#E9B83A', .35))


@prop('plane')
def _():
    lathe([(0, -.5), (.12, -.38), (.14, .2), (.1, .4), (0, .5)], m('plane', '#FFFFFF', .4), seg=14, axis='x', pos=(0, .5, 0))
    flat([(-.1, 0), (.15, 0), (.05, .5), (-.05, .5)], .03, (0, .5, 0), m('wing_p', '#E0473F'), plane='xz', rot_y=math.pi / 2)
    flat([(-.1, 0), (.15, 0), (.05, -.5), (-.05, -.5)], .03, (0, .5, 0), m('wing_p', '#E0473F'), plane='xz', rot_y=math.pi / 2)
    flat([(0, 0), (.12, 0), (.04, .22)], .03, (-.42, .58, 0), m('wing_p', '#E0473F'))
    for x in (.0, .12, .24): ball(.03, (x, .56, .12), m('window', '#9BD6F2', .2))


@prop('balloon')
def _():
    ball(.3, (0, .7, 0), m('balloon_r', '#E0473F', .25), scale=(1, 1.15, 1), sub=3)
    ball(.07, (-.12, .86, .22), m('white', '#FFFFFF', .4), scale=(1, 1.4, .4))
    lathe([(0, .35), (.05, .35), (0, .4)], m('balloon_r', '#E0473F', .25))
    tube([(0, .35, 0), (.06, .2, 0), (-.04, .05, 0)], .01, m('string', '#888888'), res=4, bev=0)


@prop('cake')
def _():
    lathe([(0, 0), (.4, 0), (.4, .25), (0, .25)], m('cake', '#F8C9D4'), seg=20)
    lathe([(0, .25), (.4, .25), (.41, .29), (0, .3)], m('icing', '#FFFFFF', .5), seg=20)
    for i in range(10):
        a = i / 10 * TAU; ball(.05, (math.cos(a) * .4, .24, math.sin(a) * .4), m('icing', '#FFFFFF', .5))
    lathe([(0, .3), (.25, .3), (.25, .48), (0, .48)], m('cake2', '#FDE3B5'), seg=20)
    ball(.06, (0, .55, 0), m('cherry', '#E0473F', .3))
    for x in (-.14, .14):
        cyl(.018, .16, (x, .56, 0), m('candle', '#7FC3F0'), 6); ball(.025, (x, .67, 0), m('flame', '#FFB52E', .2), scale=(1, 1.6, 1))


@prop('gift')
def _():
    box((.6, .45, .6), (0, .23, 0), m('gift', '#E0473F'), bevel=.03)
    box((.66, .1, .66), (0, .5, 0), m('gift_lid', '#E8564E'), bevel=.03)
    for rot in (0, 1):
        box((.1, .58, .68) if rot == 0 else (.68, .58, .1), (0, .29, 0), m('ribbon_g', '#F7D03C', .4), bevel=.01)
    for sx in (-1, 1): ball(.11, (sx * .1, .6, 0), m('ribbon_g', '#F7D03C', .4), scale=(1, .6, .5))


@prop('cap')
def _():
    c = ball(.32, (0, .2, 0), m('cap_b', '#3E6FB0'), scale=(1, .8, 1), sub=3); cut(c, lambda x, y, z: y > .2)
    b = ball(.3, (0, .21, .22), m('cap_brim', '#2F5893'), scale=(.9, .08, .9), sub=3); cut(b, lambda x, y, z: z > .1)
    ball(.04, (0, .46, 0), m('cap_b', '#3E6FB0'))


@prop('bow')
def _():
    r = m('bow_p', '#F27AA8', .4)
    for sx in (-1, 1): ball(.2, (sx * .2, .4, 0), r, scale=(1.1, .8, .45))
    ball(.08, (0, .4, .02), m('bow_d', '#D9568A', .4))
    for sx in (-1, 1): tube([(sx * .03, .38, 0), (sx * .12, .18, 0)], .04, r, [1, .6], res=1, bev=1)


@prop('flower')
def _():
    for i in range(6):
        a = i / 6 * TAU; ball(.15, (math.cos(a) * .18, .5 + math.sin(a) * .18, 0), m('petal', '#FFFFFF', .6), scale=(1, 1, .35))
    ball(.12, (0, .5, .03), m('center', '#F7C531', .6), scale=(1, 1, .6))
    cyl(.025, .3, (0, .2, -.02), m('leaf', '#4FAE4F'), 6)


@prop('tophat')
def _():
    k = m('hat_k', '#2A2A35', .5)
    lathe([(0, 0), (.42, 0), (.43, .04), (0, .04)], k, seg=20)
    lathe([(.26, .04), (.28, .55), (0, .56)], k, seg=20)
    lathe([(.265, .08), (.275, .08), (.28, .17), (.27, .17)], m('band_r', '#E0473F'), seg=20, cap=False)


@prop('crown')
def _():
    g = m('gold', '#E9B83A', .35)
    o = lathe([(.3, 0), (.32, .02), (.32, .25), (.3, .25)], g, seg=20, cap=False)
    for i in range(5):
        a = i / 5 * TAU
        lathe([(.07, 0), (0, .2)], g, seg=4, pos=(math.cos(a) * .3, .25, math.sin(a) * .3))
        ball(.035, (math.cos(a) * .3, .47, math.sin(a) * .3), g)
        ball(.04, (math.cos(a + .63) * .325, .13, math.sin(a + .63) * .325), m('gem%d' % (i % 3), ['#E0473F', '#4A90D9', '#5DBB63'][i % 3], .2))


@prop('chest')
def _():
    w, g = m('chest_w', '#C8843E'), m('gold', '#E9B83A', .35)
    box((.7, .38, .45), (0, .2, 0), w, bevel=.04)
    t = lathe([(0, -.35), (.23, -.35), (.23, .35), (0, .35)], m('chest_t', '#D99650'), seg=12, axis='x', pos=(0, .38, 0)); cut(t, lambda x, y, z: y > .38)
    for x in (-.25, .25): box((.06, .5, .48), (x, .3, 0), g, bevel=.01)
    box((.1, .12, .04), (0, .36, .23), g, bevel=.01)


@prop('owl_cap')   # "the cap is on Pip"
def _():
    PROPS['owl']()
    c = ball(.22, (0, .85, 0), m('cap_b', '#3E6FB0'), scale=(1, .7, 1), sub=3); cut(c, lambda x, y, z: y > .85)
    b = ball(.2, (0, .86, .16), m('cap_brim', '#2F5893'), scale=(.9, .08, .9)); cut(b, lambda x, y, z: z > .08)


# ---------------- Word Book words (Magic Word Book, PR #5) ----------------
@prop('ant')
def _():
    b = m('ant', '#5A3A2E')
    for i, (z, r) in enumerate(((.32, .14), (.08, .1), (-.2, .18))): ball(r, (0, .25, z), b, scale=(1, .85, 1.1 if i == 2 else 1), sub=3)
    for sx in (-1, 1):
        for z in (.12, .05, -.02):
            tube([(sx * .05, .25, z), (sx * .22, .3, z + .04), (sx * .3, .03, z + .08)], .018, b, res=4, bev=1)
        tube([(sx * .05, .38, .4), (sx * .12, .55, .45), (sx * .18, .58, .38)], .014, b, res=4, bev=1)
    eyes(.29, .45, .06, .03, smile=True, col='#1A0F0A')


@prop('jam')
def _():
    lathe([(0, 0), (.22, 0), (.25, .05), (.25, .4), (.2, .48), (0, .48)], m('jam_jar', '#C9283E', .2))
    lathe([(0, .48), (.23, .48), (.24, .56), (0, .57)], m('jam_lid', '#F2F2F2', .5))
    ball(.17, (0, .62, 0), m('jam_cloth', '#E85A5A'), scale=(1.6, .25, 1.6), sub=3)
    box((.3, .16, .02), (0, .25, .25), m('label', '#FFF5D6'), bevel=.01)
    ball(.06, (0, .25, .265), m('jam_berry', '#D6334F'), scale=(1, 1, .3))


@prop('fan')   # 電風扇: an electric fan
def _():
    w, b = m('fan_body', '#F2F2F2', .4), m('fan_blue', '#4AB3E8', .3)
    lathe([(0, 0), (.25, 0), (.27, .04), (.22, .08), (0, .09)], w, seg=24)
    cyl(.035, .5, (0, .33, 0), w, 12)
    ball(.08, (0, .62, -.02), w, scale=(1, 1, 1.3), sub=3)
    for i in range(3):
        a = TAU * i / 3 + .3
        ball(.13, (math.cos(a) * .14, .62 + math.sin(a) * .14, .08), b, scale=(1, .55, .15), sub=3).rotation_euler = (0, 0, 0)
    ball(.045, (0, .62, .1), w, sub=2)
    for r in (.15, .3):
        lathe([(r - .006, -.006), (r + .006, -.006), (r + .006, .006), (r - .006, .006), (r - .006, -.006)], w, seg=36, axis='z', pos=(0, .62, .14), cap=False)
    for i in range(8):
        a = TAU * i / 8; tube([(0, .62, .14), (math.cos(a) * .3, .62 + math.sin(a) * .3, .14)], .005, w, res=1, bev=1)
    lathe([(.3, -.006), (.31, .0), (.3, .006)], w, seg=36, axis='z', pos=(0, .62, .02), cap=False)
    ball(.03, (.12, .06, .2), m('btn', '#E0473F'), scale=(1, .5, 1))


@prop('garden')
def _():
    ball(.5, (0, 0, 0), m('soil', '#6FB548'), scale=(1, .18, .7), sub=3)
    for i, (x, z, c) in enumerate(((-.3, .1, '#E0473F'), (-.1, -.15, '#F2C230'), (.1, .15, '#E85AA8'), (.3, -.05, '#E0473F'), (0, .0, '#A56BD6'))):
        cyl(.015, .35, (x, .2, z), m('stem', '#4E9A3A'))
        ball(.09, (x, .42, z), m('tulip' + c, c), scale=(1, 1.3, 1))
        for k in (-1, 1): ball(.05, (x + k * .05, .45, z), m('tulip' + c, c), scale=(.6, 1.2, .8))
        ball(.06, (x + .05, .15, z), m('leaf', '#5DBB63'), scale=(.4, 1.3, .4))


@prop('circle')
def _(): lathe([(.3, -.06), (.42, -.06), (.45, 0), (.42, .06), (.3, .06), (.27, 0), (.3, -.06)], m('ring', '#E0473F'), seg=40, axis='z', pos=(0, .45, 0), cap=False)


@prop('square')
def _(): box((.75, .75, .14), (0, .4, 0), m('sq', '#E0473F'), bevel=.05)


@prop('elephant')   # "big"
def _():
    g = m('elephant', '#9EA8B8')
    ball(.38, (0, .52, -.05), g, scale=(1.1, .9, 1.2), sub=3)
    ball(.28, (0, .72, .32), g, sub=3)
    tube([(0, .65, .55), (0, .45, .65), (0, .3, .62), (0, .28, .55)], .07, g, [1, .8, .6, .5], res=6, bev=2)
    for sx in (-1, 1):
        ball(.22, (sx * .28, .75, .25), m('ear_e', '#B9C1CF'), scale=(.25, 1, .9), sub=3)
        for z in (-.25, .18): cyl(.1, .35, (sx * .2, .17, z), g, 12)
        tube([(sx * .1, .55, .55), (sx * .14, .48, .65)], .025, m('tusk', '#FFF8E8'), [1, .4], res=3, bev=1)
    eyes(.8, .54, .12, .035, smile=False)


@prop('bag')
def _():
    box((.6, .7, .3), (0, .4, 0), m('bag', '#3E8ED0'), bevel=.1)
    box((.44, .3, .08), (0, .3, .17), m('bag_pocket', '#2F6FAF'), bevel=.05)
    tube([(-.18, .72, 0), (0, .9, 0), (.18, .72, 0)], .03, m('strap', '#2A4D7A'), res=6, bev=2)
    ball(.025, (0, .45, .21), m('gold', '#E9B83A', .35))


@prop('mat')
def _():
    box((.9, .05, .7), (0, .03, .05), m('mat', '#F08C2E'), bevel=.02)
    for i in range(4): box((.9, .052, .05), (0, .032, -.2 + i * .15), m('mat_stripe', '#F7C25A'), bevel=0)
    cyl(.13, .9, (0, .14, -.36), m('mat', '#F08C2E'), 20, axis='x')
    cyl(.135, .05, (0, .14, -.36), m('mat_stripe', '#F7C25A'), 20, axis='x')
    for x in (-.47, .47):
        for i in range(5): cyl(.008, .07, (x, .03, -.1 + i * .08), m('mat_stripe', '#F7C25A'), 4, axis='x')


@prop('pencil_case')
def _():
    box((.85, .3, .3), (0, .2, 0), m('pcase', '#5DBB63'), bevel=.12)
    tube([(-.38, .36, 0), (.38, .36, 0)], .015, m('zip', '#3A7D40'), res=1, bev=1)
    for i, (x, c) in enumerate(((-.15, '#E0473F'), (0, '#F2C230'), (.15, '#3E8ED0'))):
        cyl(.035, .4, (x, .5, -.02), m('pencil' + c, c), 6)
        lathe([(.035, 0), (.005, .08)], m('wood', '#F3D29A'), seg=6, pos=(x, .7, -.02))


@prop('bottle')
def _():
    lathe([(0, 0), (.15, 0), (.17, .05), (.17, .55), (.12, .66), (.1, .7), (0, .7)], m('bottle', '#4AB3E8', .2), seg=20)
    lathe([(.1, .7), (.11, .82), (0, .83)], m('bottle_cap', '#E0473F'), seg=16)
    lathe([(.171, .2), (.171, .4)], m('bottle_band', '#FFFFFF'), seg=20, cap=False)


@prop('lunchbox')
def _():
    box((.8, .32, .55), (0, .18, 0), m('lbox', '#E85A5A'), bevel=.08)
    box((.82, .08, .57), (0, .36, 0), m('lbox_lid', '#F7A6A6'), bevel=.04)
    tube([(-.15, .4, 0), (0, .52, 0), (.15, .4, 0)], .025, m('lbox_h', '#C9283E'), res=6, bev=2)
    eyes(.2, .29, .1, .035)


@prop('scissors')
def _():
    blade = m('blade', '#D6DCE4', .25)
    for sx in (-1, 1):
        flat([(0, 0), (sx * .05, .02), (sx * .03, .55), (0, .58)], .03, (sx * .02, .3, sx * .01), blade, rot_y=0)
        lathe([(.06, -.02), (.1, -.02), (.1, .02), (.06, .02)], m('handle', '#E0473F'), seg=20, axis='z', pos=(sx * .14, .15, 0))
        tube([(sx * .1, .2, 0), (sx * .03, .3, 0)], .025, m('handle', '#E0473F'), res=2, bev=1)
    ball(.03, (0, .31, .03), m('gold', '#E9B83A', .35))


@prop('sneakers')
def _():
    for sx, dz in ((-1, 0), (1, -.12)):
        x = sx * .2; c = m('shoe', '#3E8ED0'); w = m('sole', '#FFFFFF')
        box((.24, .08, .56), (x, .04, dz), w, bevel=.035)
        box((.22, .13, .5), (x, .14, dz - .01), c, bevel=.06)
        ball(.12, (x, .13, dz + .18), c, scale=(.95, .7, 1), sub=3)
        box((.22, .2, .2), (x, .25, dz - .16), c, bevel=.07)
        box((.12, .14, .18), (x, .22, dz + .04), m('tongue_s', '#2F6FAF'), bevel=.04)
        for k in range(3): tube([(x - .07, .23 - k * .03, dz + .0 + k * .06), (x + .07, .23 - k * .03, dz + .0 + k * .06)], .012, w, res=1, bev=1)
        ball(.04, (x + sx * .11, .17, dz - .12), m('star_s', '#F2C230'), scale=(.3, 1, 1))


@prop('shorts')
def _():
    c = m('shorts_c', '#3E8ED0')
    box((.6, .16, .2), (0, .62, 0), c, bevel=.06)
    for sx in (-1, 1):
        lathe([(.15, .2), (.16, .25), (.15, .58), (0, .6)], c, seg=16, pos=(sx * .16, 0, 0))
    box((.62, .05, .22), (0, .7, 0), m('shorts_band', '#F2F2F2'), bevel=.02)


@prop('web')
def _():
    w = m('web', '#F4F6FA', .4)
    for i in range(8):
        a = TAU * i / 8; tube([(0, .45, 0), (math.cos(a) * .45, .45 + math.sin(a) * .45, 0)], .008, w, res=1, bev=1)
    for r in (.12, .22, .32, .42):
        pts = [(math.cos(TAU * i / 8) * r, .45 + math.sin(TAU * i / 8) * r, 0) for i in range(9)]
        tube(pts, .007, w, res=2, bev=1)
    ball(.08, (.15, .5, .03), m('spider', '#3A3330'), sub=3); eyes(.52, .1, .03, .015, col='#FFFFFF', smile=False)


@prop('ten')
def _():
    c = m('ten', '#3E8ED0')
    box((.12, .6, .14), (-.25, .4, 0), c, bevel=.05); box((.12, .1, .14), (-.3, .66, 0), c, bevel=.04)
    o = lathe([(.08, -.07), (.2, -.07), (.2, .07), (.08, .07), (.08, -.07)], c, seg=28, axis='z', pos=(0, 0, 0), cap=False)
    for v in o.data.vertices: v.co.x = v.co.x * .75 + .14; v.co.z = v.co.z * 1.5 + .4


@prop('jet')
def _():
    b = m('jet', '#F2F2F2', .4)
    ball(.16, (0, .4, 0), b, scale=(1, 1, 3.6), sub=3)
    lathe([(.16, 0), (.0, .25)], m('jet_nose', '#E0473F'), seg=16, axis='z', pos=(0, .4, .5))
    for sx in (-1, 1):
        flat([(0, .25), (sx * .7, -.1), (sx * .7, -.22), (0, -.15)], .03, (0, .4, 0), m('jet_wing', '#3E8ED0'), plane='xz')
        flat([(0, -.45), (sx * .25, -.6), (sx * .25, -.66), (0, -.6)], .03, (0, .42, 0), m('jet_wing', '#3E8ED0'), plane='xz')
    flat([(0, 0), (.0, .32), (-.2, .32), (-.3, 0)], .03, (0, .45, -.42), m('jet_wing', '#3E8ED0'), rot_y=math.pi / 2)
    for z in (.15, 0, -.15): ball(.04, (.15, .45, z), m('window', '#7FC8F0', .2), scale=(.3, 1, 1))


@prop('dance')
def _():
    person(hair='#8B5634', shirt='#E85AA8', style='pigtails')
    for sx in (-1, 1): tube([(sx * .22, .4, 0), (sx * .38, .62, .02), (sx * .42, .82, .04)], .045, m('p_shirt#E85AA8', '#E85AA8'), res=4, bev=2)
    for sx in (-1, 1): ball(.06, (sx * .42, .88, .04), m('p_skin', '#F8D5B8'))
    for x, y in ((-.5, .3), (.5, .45), (.45, 1.0)):
        ball(.05, (x, y, .1), m('note', '#A56BD6'), scale=(1, .8, .6)); cyl(.01, .15, (x + .045, y + .08, .1), m('note', '#A56BD6'), 4)


@prop('read')
def _():
    for sx in (-1, 1):
        p = [(0, 0)] + [(sx * .42 * i / 6, .06 * math.sin(math.pi * i / 6)) for i in range(1, 7)] + [(sx * .42, -.04), (0, -.04)]
        flat([(sx * .44, -.06), (0, -.06), (0, .02), (sx * .44, .0)], .55, (0, .3, 0), m('cover', '#E0473F'), plane='xz')
        for k in range(3):
            pts = [(sx * .42 * i / 6, .06 + .05 * math.sin(math.pi * i / 6) - k * .015) for i in range(7)]
            flat(pts + [(sx * .42, .02 - k * .015), (0, .02 - k * .015)], .5, (0, .3 + k * .01, 0), m('pages', '#FFF8E8'), plane='xz')
        for j in range(4): box((.25, .006, .025), (sx * .21, .41, -.15 + j * .1), m('text', '#8A8F99'), bevel=0)


@prop('smell')
def _():
    ball(.38, (0, .45, 0), m('face_s', '#F8D5B8'), sub=3)
    ball(.11, (0, .42, .36), m('nose_s', '#F3B998'), scale=(1, .9, .9), sub=3)
    for sx in (-1, 1):
        tube([(sx * .16, .55, .33), (sx * .11, .59, .35), (sx * .06, .55, .36)], .014, m('eye', '#2A1A14', .3), res=4, bev=1)
        ball(.06, (sx * .22, .38, .3), m('cheek', '#FF9E9E', .9), scale=(1, .6, .3))
    tube([(-.05, .27, .33), (0, .25, .34), (.05, .27, .33)], .014, m('eye', '#2A1A14', .3), res=4, bev=1)
    for x in (.3, .45):
        tube([(x, .55, .3), (x + .07, .7, .3), (x - .02, .85, .3), (x + .06, 1.0, .3)], .022, m('scent', '#9BD3F2', .4), res=6, bev=2)
    cyl(.012, .35, (.55, .2, .25), m('stem', '#4E9A3A'))
    for i in range(5):
        a = TAU * i / 5; ball(.06, (.55 + math.cos(a) * .07, .4 + math.sin(a) * .07, .25), m('petal', '#E85AA8'))
    ball(.045, (.55, .4, .28), m('gold', '#E9B83A', .35))


@prop('taste')
def _():
    ball(.42, (0, .45, 0), m('face_t', '#FFD84A'), sub=3)
    eyes(.55, .38, .15, .05, smile=False)
    ball(.14, (0, .3, .35), m('mouth_t', '#9C2A35'), scale=(1.2, .6, .4))
    ball(.1, (.02, .2, .42), m('tongue_t', '#F07C86'), scale=(.9, 1.2, .4))
    lathe([(0, 0), (.09, .06), (.11, .16), (0, .18)], m('cone', '#E5B36A'), seg=12, pos=(.38, .35, .2))
    ball(.11, (.38, .55, .2), m('icecream', '#F7A6C8'), sub=3)


@prop('fries')
def _():
    box((.5, .5, .25), (0, .25, 0), m('fries_box', '#E0473F'), bevel=.04)
    for i in range(14):
        x = random.uniform(-.2, .2); z = random.uniform(-.08, .08); h = random.uniform(.35, .55)
        box((.06, h, .06), (x, .45 + h / 2 - .1, z), m('fry', '#F7C948'), bevel=.015)
    ball(.08, (0, .3, .13), m('gold', '#E9B83A', .35), scale=(1.4, 1, .2))


@prop('rice')
def _():
    lathe([(0, 0), (.15, 0), (.18, .03), (.38, .2), (.42, .32), (.4, .33), (0, .2)], m('bowl', '#F2F2F2', .35), seg=24)
    lathe([(.39, .32), (.4, .33)], m('bowl_band', '#3E8ED0'), seg=24, cap=False)
    ball(.37, (0, .36, 0), m('rice_w', '#FFFDF5'), scale=(1, .62, 1), sub=3)
    for i in range(18):
        a = random.uniform(0, TAU); r = random.uniform(0, .3)
        ball(.035, (math.cos(a) * r, .58 - r * .35, math.sin(a) * r), m('rice_w', '#FFFDF5'), scale=(1.6, .7, .8), sub=1)
    tube([(-.3, .62, -.1), (.35, .72, .1)], .015, m('chopstick', '#B5743E'), res=1, bev=1)
    tube([(-.3, .58, -.02), (.35, .68, .18)], .015, m('chopstick', '#B5743E'), res=1, bev=1)


@prop('cookie')
def _():
    lathe([(0, -.05), (.4, -.05), (.43, 0), (.4, .05), (0, .055)], m('cookie', '#D69A52'), seg=28, axis='z', pos=(0, .45, 0))
    for i in range(9):
        a = TAU * i / 9 + .3; r = .25 if i % 2 else .12
        ball(.05, (math.cos(a) * r, .45 + math.sin(a) * r, .055), m('choc', '#5A3A2E'), scale=(1, 1, .5))
    eyes(.5, .065, .12, .035)


@prop('yogurt')
def _():
    lathe([(0, 0), (.2, 0), (.27, .45), (0, .45)], m('cup_y', '#FFFFFF', .3), seg=20)
    lathe([(.271, .15), (.275, .32)], m('cup_band', '#F7A6C8'), seg=20, cap=False)
    ball(.25, (0, .46, 0), m('yog', '#FDEFF4'), scale=(1, .35, 1), sub=3)
    ball(.06, (0, .55, 0), m('berry', '#D6334F'), sub=2)
    box((.06, .5, .02), (.15, .65, 0), m('spoon', '#D6DCE4', .3), bevel=.02)


@prop('carrot')
def _():
    lathe([(0, 0), (.04, .06), (.1, .3), (.13, .55), (.12, .62), (0, .64)], m('carrot', '#F08C2E'), seg=16)
    for i in range(4): tube([(0, .33 + i * .07, .11), (.05, .33 + i * .07, .12)], .008, m('carrot_line', '#D06E18'), res=1, bev=1)
    for a in (-.5, 0, .5):
        tube([(0, .62, 0), (math.sin(a) * .15, .82, 0), (math.sin(a) * .25, .95, 0)], .03, m('leaf', '#5DBB63'), [1, .8, .3], res=4, bev=2)
    eyes(.4, .14, .055, .025)



if __name__ == '__main__':
    out = sys.argv[-1] if sys.argv[-1].endswith('.glb') else 'models/icons.glb'
    only = [a for a in sys.argv[1:] if not a.endswith('.glb')]
    random.seed(5)
    roots = []
    for key, fn in PROPS.items():
        if only and key not in only: continue
        before = set(C.scene.objects)
        fn()
        new = [o for o in C.scene.objects if o not in before and o.type == 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for o in new: o.select_set(True)
        C.view_layer.objects.active = new[0]; bpy.ops.object.join()
        o = C.view_layer.objects.active; o.name = key; o.data.name = key
        roots.append(o)
    n = sum(len(o.data.polygons) for o in roots)
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=False, export_apply=True, export_yup=True)
    print('%d objects, %d faces, %.0f KB' % (len(roots), n, os.path.getsize(out) / 1024))
