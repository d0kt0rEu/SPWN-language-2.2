#!/usr/bin/env python3
"""Compiles soft body scenarios with SPWN, runs them in the trigger simulator and compares with ref.py."""
import math, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "gd22"))
import gdsave, sim, ref



def compile_script(src):
    d = tempfile.mkdtemp()
    f = os.path.join(d, "s.spwn")
    open(f, "w").write(src)
    save = os.path.join(d, "save.dat")
    gdsave.make(save)
    r = subprocess.run([os.path.join(REPO, "target", "release", "spwn"), "build", f, "-s", save, "-i",
                        os.path.join(REPO, "libraries")] + os.environ.get("SB_FLAGS", "").split(), capture_output=True, text=True, cwd=REPO)
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    if "Written to save" not in out:
        print(out[-3000:])
        raise SystemExit("compile failed")
    return sim.load(save), out


def run(src, groups, frames, build_ref):
    """groups: list of (group id, start x, start y) in the order build_ref returns its points"""
    s, out = compile_script(src)
    w, pts = build_ref()
    s.start()
    # the script ends with `wait(100000) d!`: a spawn trigger with a huge delay that points at the driver group
    spawns = [o for o in s.objects if o[1] == "1268" and float(o.get(63, 0)) >= 1000]
    assert len(spawns) == 1, [o for o in s.objects if o[1] == "1268"]
    driver = int(spawns[0][51])
    worst = 0.0
    worst_item = 0.0
    for fr in range(frames):
        s.step(driver)
        w.step()
        for (g, x0, y0), p in zip(groups, pts):
            mx, my = s.moves[g]
            gx, gy = x0 + mx, y0 + my
            ex = abs(gx - p.ax)
            ey = abs(gy - p.ay)
            worst = max(worst, ex, ey)
            worst_item = max(worst_item, abs(gx - p.x), abs(gy - p.y))
    return worst, worst_item, max(s.executed_per_frame), out


def scenario_fall():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 1800, floor = 0, restitution = 0.5)
a = world.point(10g, 300, 300)
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        w = ref.World(gravity=1800, floor=0, restitution=0.5)
        return w, [w.point(300, 300)]
    return src, [(10, 300, 300)], 240, mk


def scenario_spring():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 1800, floor = 0, left = 0, right = 600)
a = world.point(10g, 300, 300)
b = world.point(11g, 340, 300)
c = world.point(12g, 320, 340)
world.spring(a, b)
world.spring(b, c)
world.spring(c, a, stiffness = 0.2, damping = 0.1)
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        w = ref.World(gravity=1800, floor=0, left=0, right=600)
        a, b, c = w.point(300, 300), w.point(340, 300), w.point(320, 340)
        w.spring(a, b, 0.3, 0.05)
        w.spring(b, c, 0.3, 0.05)
        w.spring(c, a, 0.2, 0.1)
        return w, [a, b, c]
    return src, [(10, 300, 300), (11, 340, 300), (12, 320, 340)], 300, mk


def scenario_spring_free():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 0)
a = world.point(10g, 300, 300)
b = world.point(11g, 360, 300)
c = world.point(12g, 330, 340)
world.spring(a, b, length = 40)
world.spring(b, c, length = 40)
world.spring(c, a, length = 40, stiffness = 0.2, damping = 0.1)
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        w = ref.World(gravity=0)
        a, b, c = w.point(300, 300), w.point(360, 300), w.point(330, 340)
        w.spring(a, b, 0.3, 0.05, 40)
        w.spring(b, c, 0.3, 0.05, 40)
        w.spring(c, a, 0.2, 0.1, 40)
        return w, [a, b, c]
    return src, [(10, 300, 300), (11, 360, 300), (12, 330, 340)], 200, mk


def scenario_wall():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 1800, floor = 0, restitution = 0.5, friction = 0.2)
a = world.point(10g, 300, 40)
b = world.point(11g, 340, 40)
world.spring(a, b)
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        w = ref.World(gravity=1800, floor=0, restitution=0.5, friction=0.2)
        a, b = w.point(300, 40), w.point(340, 40)
        w.spring(a, b, 0.3, 0.05)
        return w, [a, b]
    return src, [(10, 300, 40), (11, 340, 40)], 200, mk


def scenario_solid():
    src = '''
extract obj_props
sb = import softbody
d = ?g
solid = 5b
// a platform of collision blocks, top surface at y = 95
for i in 0..8 {
    $.add(obj { OBJ_ID: obj_ids.special.COLLISION_BLOCK, BLOCK_A: solid, X: 240 + i * 30, Y: 80 })
}
world = sb.world(gravity = 1800, restitution = 0.4, solid = solid, floor = -50)
a = world.point(10g, 300, 220)
b = world.point(11g, 340, 220)
world.spring(a, b)
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        solids = [(240 + i * 30, 80, 15.0) for i in range(8)]
        w = ref.World(gravity=1800, restitution=0.4, solids=solids, floor=-50)
        a, b = w.point(300, 220), w.point(340, 220)
        w.spring(a, b, 0.3, 0.05)
        return w, [a, b]
    return src, [(10, 300, 220), (11, 340, 220)], 240, mk


def scenario_blob():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 1800, floor = 0, restitution = 0.4)
pts = world.blob([10g, 11g, 12g, 13g, 14g, 15g], 400, 80, 40, center = 16g)
world.start(driver = d)
wait(100000)
d!
'''
    n = 6
    cx, cy, r = 400, 80, 40
    def mk():
        w = ref.World(gravity=1800, floor=0, restitution=0.4)
        ring = [w.point(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        for i in range(n):
            w.spring(ring[i], ring[(i + 1) % n], 0.3, 0.05)
            w.spring(ring[i], ring[(i + 2) % n], 0.3, 0.05)
        c = w.point(cx, cy)
        for i in range(n):
            w.spring(c, ring[i], 0.3, 0.05)
        return w, ring + [c]
    groups = [(10 + i, cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)] + [(16, cx, cy)]
    return src, groups, 240, mk


def scenario_rope():
    src = '''
extract obj_props
sb = import softbody
d = ?g
world = sb.world(gravity = 1800, floor = 0)
world.rope([world.point(30g, 100, 300, pinned = true), world.point(31g, 130, 300), world.point(32g, 160, 300), world.point(33g, 190, 300)])
world.start(driver = d)
wait(100000)
d!
'''
    def mk():
        w = ref.World(gravity=1800, floor=0)
        p = [w.point(100, 300, pinned=True), w.point(130, 300), w.point(160, 300), w.point(190, 300)]
        for i in range(1, 4):
            w.spring(p[i - 1], p[i], 0.3, 0.05)
        return w, p
    return src, [(30, 100, 300), (31, 130, 300), (32, 160, 300), (33, 190, 300)], 240, mk


def main():
    ok = True
    for name, sc in (("fall", scenario_fall), ("spring only", scenario_spring_free), ("floor pair", scenario_wall), ("solid block", scenario_solid), ("triangle", scenario_spring), ("blob", scenario_blob), ("rope", scenario_rope)):
        src, groups, frames, mk = sc()
        w, wi, trig, out = run(src, groups, frames, mk)
        good = wi <= 0.5 + 1e-6   # objects are never further than half a unit from the simulated position
        ok &= good
        print(f"{name:12s} objects vs reference positions: off by at most {wi:.3f} units; "
              f"max triggers/frame {trig}  {'OK' if good else 'MISMATCH'}")
    sys.exit(0 if ok else 1)


main()
