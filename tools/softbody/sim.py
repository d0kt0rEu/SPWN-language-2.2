#!/usr/bin/env python3
"""A small simulator for the trigger subset the soft body engine uses.

It exists to test the engine's logic without Geometry Dash. It models:
  * groups run their triggers in x order (then y, descending), spawn triggers with delay 0 run the target
    group immediately (depth first), delayed spawns are queued
  * item edit / item compare / pickup / instant count / toggle / move / instant collision
Assumptions about the game (documented in README): item values are floats; item edit computes
  target <assign>= (item1 <op1> item2) <op2> mod ; abs applies to the result.
"""
import collections
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gd22"))
import gdsave  # noqa: E402

OPS = {1: lambda a, b: a + b, 2: lambda a, b: a - b, 3: lambda a, b: a * b, 4: lambda a, b: a / b if b else 0.0}


def groups_of(o):
    v = o.get(57)
    return [int(x) for x in v.split(".")] if v else []


class Sim:
    def __init__(self, objs, fps=60):
        self.fps = fps
        self.items = collections.defaultdict(float)
        self.toggled_off = set()
        self.moves = collections.defaultdict(lambda: [0.0, 0.0])  # group -> total displacement
        self.queue = []  # (tick, seq, group)
        self.seq = 0
        self.tick = 0
        self.triggers = collections.defaultdict(list)
        self.blocks = []  # collision block objects
        self.counts = collections.Counter()  # trigger executions
        self.executed_per_frame = []
        self.start_triggers = []
        self.depth = 0
        self.write_log = []
        for o in objs:
            oid = int(o[1])
            if oid == 1816:
                self.blocks.append(o)
            if oid in (3619, 3620, 1817, 1811, 1268, 901, 3609, 1049):
                gl = groups_of(o)
                for g in gl:
                    self.triggers[g].append(o)
                if 62 not in o:
                    self.start_triggers.append(o)
        key = lambda o: (float(o.get(2, 0)), -float(o.get(3, 0)))
        for g in self.triggers:
            self.triggers[g].sort(key=key)
        self.start_triggers.sort(key=key)
        self.objects = objs

    # -- helpers
    def run_group(self, g):
        if g in self.toggled_off:
            return
        self.depth += 1
        if self.depth > 200:
            raise RuntimeError("spawn recursion too deep")
        for o in self.triggers.get(g, []):
            self.exec(o)
        self.depth -= 1

    def schedule(self, delay, g):
        if delay <= 0:
            self.run_group(g)
        else:
            self.seq += 1
            self.queue.append((self.tick + max(1, round(delay * self.fps)), self.seq, g))

    def val(self, i):
        return self.items[i]

    def pos(self, o):
        x, y = float(o.get(2, 0)), float(o.get(3, 0))
        for g in groups_of(o):
            m = self.moves.get(g)
            if m:
                x += m[0]
                y += m[1]
        return x, y

    def overlap(self, a, b):
        ax, ay = self.pos(a)
        bx, by = self.pos(b)
        ha = 15.0 * float(a.get(32, 1))
        hb = 15.0 * float(b.get(32, 1))
        return abs(ax - bx) < ha + hb and abs(ay - by) < ha + hb

    # -- triggers
    def exec(self, o):
        oid = int(o[1])
        self.counts[oid] += 1
        self.frame_count += 1
        if oid == 1268:
            self.schedule(float(o.get(63, 0)), int(o.get(51, 0)))
        elif oid == 3619:
            a, b = self.val(int(o.get(80, 0))), self.val(int(o.get(95, 0)))
            op1 = int(o.get(481, 1))
            op2 = int(o.get(482, 3))
            mod = float(o.get(479, 1))
            r = OPS[op1](a, b) if op1 in OPS else a
            r = OPS[op2](r, mod) if op2 in OPS else r
            if int(o.get(578, 0)) == 1 or int(o.get(579, 0)) == 1:
                r = abs(r)
            t = int(o.get(51, 0))
            self.write_log.append(t)
            asg = int(o.get(480, 0))
            if asg == 0:
                self.items[t] = r
            else:
                self.items[t] = OPS[asg](self.items[t], r)
        elif oid == 3620:
            a, b = self.val(int(o.get(80, 0))), self.val(int(o.get(95, 0)))
            m1, m2 = float(o.get(479, 1)), float(o.get(483, 1))
            a = OPS[int(o.get(480, 3))](a, m1)
            b = OPS[int(o.get(481, 3))](b, m2)
            tol = float(o.get(484, 0))
            op = int(o.get(482, 0))
            c = {0: abs(a - b) <= tol, 1: a > b + tol, 2: a >= b - tol, 3: a < b - tol, 4: a <= b + tol}[op]
            g = int(o.get(51, 0)) if c else int(o.get(71, 0))
            if g:
                self.run_group(g)
        elif oid == 1817:
            i = int(o.get(80, 0))
            if int(o.get(139, 0)):
                self.items[i] = float(o.get(77, 0))
            else:
                mode = int(o.get(88, 0))
                mod = float(o.get(449, 1))
                if mode == 1:
                    self.items[i] *= mod
                elif mode == 2:
                    self.items[i] /= mod if mod else 1
                else:
                    self.items[i] += float(o.get(77, 0))
        elif oid == 1811:
            v = self.val(int(o.get(80, 0)))
            n = float(o.get(77, 0))
            cmpm = int(o.get(88, 0))
            c = {0: v == n, 1: v > n, 2: v < n}[cmpm]
            if c and int(o.get(56, 0)):
                self.run_group(int(o.get(51, 0)))
        elif oid == 901:
            g = int(o.get(51, 0))
            self.moves[g][0] += float(o.get(28, 0))
            self.moves[g][1] += float(o.get(29, 0))
        elif oid == 1049:
            g = int(o.get(51, 0))
            if int(o.get(56, 0)):
                self.toggled_off.discard(g)
            else:
                self.toggled_off.add(g)
        elif oid == 3609:
            ba, bb = int(o.get(80, 0)), int(o.get(95, 0))
            hit = False
            for a in self.blocks:
                if int(a.get(80, -1)) != ba:
                    continue
                for b in self.blocks:
                    if int(b.get(80, -1)) == bb and self.overlap(a, b):
                        hit = True
                        break
                if hit:
                    break
            g = int(o.get(51, 0)) if hit else int(o.get(71, 0))
            if g:
                self.run_group(g)

    # -- driving
    def start(self):
        self.frame_count = 0
        for o in self.start_triggers:
            self.exec(o)

    def step(self, driver=None):
        """One frame: delayed spawns that are due, then the driver group."""
        self.tick += 1
        self.frame_count = 0
        due = sorted(q for q in self.queue if q[0] <= self.tick)
        self.queue = [q for q in self.queue if q[0] > self.tick]
        for _, _, g in due:
            self.run_group(g)
        if driver is not None:
            self.run_group(driver)
        self.executed_per_frame.append(self.frame_count)


def load(path):
    return Sim(gdsave.parse_objects(gdsave.read_levelstring(path)))
