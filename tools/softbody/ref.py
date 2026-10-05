"""Reference implementation of the soft body algorithm (plain floats). The trigger network must match it."""
import math


class Pt:
    def __init__(self, x, y, pinned=False, mass=1.0):
        self.x, self.y, self.vx, self.vy = x, y, 0.0, 0.0
        self.ax, self.ay = x, y
        self.pinned = pinned
        self.inv_mass = 1.0 / mass
        self.fx = self.fy = 0.0


class Spring:
    def __init__(self, a, b, k, c, length=None):
        self.a, self.b, self.k, self.c = a, b, k, c
        self.L = length if length is not None else math.hypot(b.x - a.x, b.y - a.y)


class World:
    def __init__(self, gravity=1800, fps=60, floor=None, ceiling=None, left=None, right=None,
                 restitution=0.3, friction=0.05, air_drag=0.0, bits=6, sqrt_iterations=4,
                 solids=None, push=1.0, radius=10.0):
        self.grav = -gravity / (fps * fps)
        self.limits = dict(floor=floor, ceiling=ceiling, left=left, right=right)
        self.e, self.mu = restitution, friction
        self.air = (1 - air_drag) ** (1 / fps)
        self.bits, self.iters = bits, sqrt_iterations
        self.pts, self.springs = [], []
        self.solids = solids or []     # (x, y, half size) boxes
        self.push, self.radius = push, radius

    def point(self, *a, **k):
        p = Pt(*a, **k)
        self.pts.append(p)
        return p

    def spring(self, a, b, k, c, length=None):
        s = Spring(a, b, k, c, length)
        self.springs.append(s)
        return s

    def _bound(self, pos, vel, vt, limit, lower):
        d = limit - pos if lower else pos - limit
        pen = (d + abs(d)) * 0.5
        pos = pos + pen if lower else pos - pen
        tmp = pen * 1000
        c = (tmp + 1 - abs(tmp - 1)) * 0.5
        vn = (vel - abs(vel)) * 0.5 if lower else (vel + abs(vel)) * 0.5
        vel = vel - c * vn * (1 + self.e)
        vt = vt * (1 - c * self.mu)
        return pos, vel, vt

    def _respond(self, p, axis, lower):
        pos, vel, vt = (p.x, p.vx, p.vy) if axis == 0 else (p.y, p.vy, p.vx)
        vn = (vel - abs(vel)) * 0.5 if lower else (vel + abs(vel)) * 0.5
        vel = vel - vn * (1 + self.e)
        vt = vt * (1 - self.mu)
        pos = pos + self.push if lower else pos - self.push
        if axis == 0:
            p.x, p.vx, p.vy = pos, vel, vt
        else:
            p.y, p.vy, p.vx = pos, vel, vt

    def step(self):
        for p in self.pts:
            if not p.pinned:
                p.fx, p.fy = 0.0, self.grav
        for s in self.springs:
            a, b = s.a, s.b
            dx, dy = b.x - a.x, b.y - a.y
            d2 = dx * dx + dy * dy
            ln = s.L
            for _ in range(self.iters):
                ln = (ln + d2 / ln) * 0.5
            ext = ln - s.L
            dvx, dvy = b.vx - a.vx, b.vy - a.vy
            pv = (dvx * dx + dvy * dy) / ln
            f = ext * s.k + pv * s.c
            fx, fy = f * dx / ln, f * dy / ln
            if not a.pinned:
                a.fx += fx * a.inv_mass
                a.fy += fy * a.inv_mass
            if not b.pinned:
                b.fx -= fx * b.inv_mass
                b.fy -= fy * b.inv_mass
        off = 2 ** (self.bits - 1)
        for p in self.pts:
            if p.pinned:
                continue
            p.vx += p.fx
            p.vy += p.fy
            if self.air != 1:
                p.vx *= self.air
                p.vy *= self.air
            p.x += p.vx
            p.y += p.vy
            L = self.limits
            if L["floor"] is not None:
                p.y, p.vy, p.vx = self._bound(p.y, p.vy, p.vx, L["floor"], True)
            if L["ceiling"] is not None:
                p.y, p.vy, p.vx = self._bound(p.y, p.vy, p.vx, L["ceiling"], False)
            if L["left"] is not None:
                p.x, p.vx, p.vy = self._bound(p.x, p.vx, p.vy, L["left"], True)
            if L["right"] is not None:
                p.x, p.vx, p.vy = self._bound(p.x, p.vx, p.vy, L["right"], False)
            for dx, dy, axis, lower in ((-1, 0, 0, True), (1, 0, 0, False), (0, -1, 1, True), (0, 1, 1, False)):
                if not self.solids:
                    break
                sx, sy = p.ax + dx * self.radius, p.ay + dy * self.radius
                if any(abs(sx - bx) < 3.75 + h and abs(sy - by) < 3.75 + h for bx, by, h in self.solids):
                    self._respond(p, axis, lower)
            for axis in (0, 1):
                pos = p.x if axis == 0 else p.y
                applied = p.ax if axis == 0 else p.ay
                q = pos - applied + off + 0.5
                q = min(q, 2 ** self.bits - 0.001)
                q = max(q, 0.0)
                qc = q
                for i in range(self.bits - 1, -1, -1):
                    if q >= 2 ** i:
                        q -= 2 ** i
                applied = applied + (qc - q) - off
                if axis == 0:
                    p.ax = applied
                else:
                    p.ay = applied
