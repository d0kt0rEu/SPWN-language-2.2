import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "gd22"))
src_t = open(os.path.join(HERE, "test_softbody.py")).read().replace("\nmain()\n", "\n")
ns = {"__file__": os.path.join(HERE, "test_softbody.py")}
exec(compile(src_t, "t", "exec"), ns)
s, out = ns["compile_script"](open(sys.argv[1]).read())
print(out[-300:])
for g, l in sorted(s.triggers.items()):
    kinds = collections.Counter(int(o[1]) for o in l)
    print(g, dict(kinds))
print("start:", [(o[1], o.get(51)) for o in s.start_triggers])
