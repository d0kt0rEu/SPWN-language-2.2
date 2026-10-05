import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "gd22"))
t = open(os.path.join(HERE, "test_softbody.py")).read().replace("\nmain()\n", "\n")
ns = {"__file__": os.path.join(HERE, "test_softbody.py")}
exec(compile(t, "t", "exec"), ns)
name = sys.argv[1]; n = int(sys.argv[2])
src, groups, frames, mk = ns[name]()
s, out = ns["compile_script"](src)
s.start()
spawns = [o for o in s.objects if o[1] == "1268" and float(o.get(63, 0)) >= 1000]
driver = int(spawns[0][51])
w, pts = mk()
for i in range(n):
    s.step(driver); w.step()
    row = []
    for (g, x0, y0), p in zip(groups, pts):
        mx, my = s.moves[g]
        row.append((round(x0 + mx, 3), round(y0 + my, 3), round(p.ax, 3), round(p.ay, 3)))
    print(i, row)
