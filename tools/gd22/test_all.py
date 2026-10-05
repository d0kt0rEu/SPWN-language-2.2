#!/usr/bin/env python3
"""Calls every generated 2.2 function with every parameter set and checks the emitted property keys/values."""
import os, subprocess, sys, tempfile, re
sys.path.insert(0, os.path.dirname(__file__))
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import gen_std as G
import gdsave

SCR = tempfile.mkdtemp()

def sample(pat, key, name):
    if name == "easing": return "EASE_IN", ("num", 2)
    if name == "easing_rate": return "3", ("num", 3)
    p = pat
    if p.startswith("@group"): return "5g", ("id", None)
    if p == "@color": return "6c", ("id", None)
    if p == "@item": return "7i", ("id", None)
    if p == "@block": return "8b", ("id", None)
    if p == "@bool": return "true", ("num", 1)
    if p == "@string": return '"1.2"', ("str", "1.2")
    if p.startswith("["): return "[5g, 6g]", ("id", None)
    if p == "@array": return "[[5g, 1], [6g, 2]]", ("id", None)
    return str(key), ("num", key)

def build():
    lines, expect = [], []
    for i in sorted(G.SPECS):
        if i in G.LEGACY: continue
        sp = G.SPECS[i]
        props = G.own_props(i)
        args, exp = [], {}
        for name, key, typ, comment in props:
            kind, pat, _ = G.type_info(typ)
            v, e = sample(pat, key, name)
            args.append(f"{G.param_name(name)} = {v}")
            exp[key] = e
        if sp["easing"]:
            for name in ("easing", "easing_rate"):
                v, e = sample("", 0, name)
                args.append(f"{name} = {v}")
            exp[30] = ("num", 2); exp[85] = ("num", 3)
        a = ", ".join(args)
        lines.append(f"$.add({sp['name']}_trigger({a}))")
        if G.is_triggerish(G.ids[i]):
            lines.append(f"ctx_{i} = !{{ {sp['name']}({a}) }}\nctx_{i}!")
        expect.append((i, exp))
    return "\n".join(lines), expect

def main():
    src, expect = build()
    f = os.path.join(SCR, "all.spwn")
    open(f, "w").write(src)
    save = tempfile.mktemp(dir=SCR, suffix=".dat")
    gdsave.make(save)
    r = subprocess.run([os.path.join(G.REPO, "target", "release", "spwn"), "build", f, "-s", save, "-i",
                        os.path.join(G.REPO, "libraries")], capture_output=True, text=True, cwd=G.REPO)
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    if "Written to save" not in out:
        print(out[-4000:]); sys.exit(1)
    objs = gdsave.parse_objects(gdsave.read_levelstring(save))
    os.remove(save)
    byid = {}
    for o in objs:
        byid.setdefault(int(o[1]), []).append(o)
    bad = 0
    for i, exp in expect:
        cands = byid.get(i, [])
        stat = [o for o in cands if 62 not in o]
        ctx = [o for o in cands if 62 in o]
        want = 2 if G.is_triggerish(G.ids[i]) else 1
        for label, group in (("obj", stat), ("ctx", ctx)):
            if label == "ctx" and not G.is_triggerish(G.ids[i]): continue
            if not group:
                print(f"MISSING {label} {i} {G.SPECS[i]['name']}"); bad += 1; continue
            o = group[0]
            for key, (kind, val) in exp.items():
                if key not in o:
                    print(f"{label} {i} {G.SPECS[i]['name']}: key {key} not written"); bad += 1; continue
                if kind == "num" and abs(float(o[key]) - float(val)) > 1e-6:
                    print(f"{label} {i}: key {key} = {o[key]} want {val}"); bad += 1
                if kind == "str" and o[key] != val:
                    print(f"{label} {i}: key {key} = {o[key]} want {val}"); bad += 1
                if kind == "id" and not re.fullmatch(r"[0-9.]+", o[key]):
                    print(f"{label} {i}: key {key} = {o[key]} not an id list"); bad += 1
    print("objects in level:", len(objs), "| problems:", bad)
    sys.exit(1 if bad else 0)

main()
