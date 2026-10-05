"""Parser for gd-info-explorer's schema.txt (the community GD 2.2 object property table).

Produces:
  types:    name -> ('prim', 'Int'|'Float'|...) | ('enum', [(name, value)])
  classes:  name -> {'parents': [...], 'props': [(name, key, type, comment)]}
  ids:      object id -> class name
  names:    object id -> display name (from objects.csv)
"""
import os
import re

# Clone https://github.com/FlowVix/gd-info-explorer and point GD_INFO_DIR at its `src/lib` directory.
SRC = os.environ.get("GD_INFO_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gd-info-explorer/src/lib"))

PRIMS = {"Int", "Float", "Bool", "String", "HSVString", "GroupList", "ParticleString",
         "RemapList", "AdvRandomList", "SequenceList", "EventList"}


# The community schema types a few ID fields as plain Int. These are corrections where the
# field is known to hold an ID from a specific pool: (class, property name) -> declared type.
FIXES = {
    ("StaticCameraTrigger", "target_group"): "GroupID",
    ("SFXTrigger", "group_id_1"): "GroupID",
    ("SFXTrigger", "group_id_2"): "GroupID",
    ("ResetTrigger", "group_id"): "GroupID",
    ("TimeControlTrigger", "item_id"): "TimerID",
}


def parse(path=None):
    types, classes, ids = _parse(path)
    for (cls, prop), typ in FIXES.items():
        c = classes[cls]
        for i, p in enumerate(c["props"]):
            if p[0] == prop:
                c["props"][i] = (p[0], p[1], typ, p[3])
                break
        else:
            raise KeyError(f"fix target not found: {cls}.{prop}")
    return types, classes, ids


def _parse(path=None):
    path = path or os.path.join(SRC, "schema.txt")
    lines = open(path).read().split("\n")
    types = {}
    classes = {}
    ids = {}
    cur = None
    section = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.split("#")[0].strip() if not raw.strip().startswith("%") else raw.strip()
        comment = raw.split("#", 1)[1].strip() if "#" in raw else ""
        i += 1
        if not line:
            continue
        if line.startswith("%"):
            section = line[1:]
            cur = None
            continue
        if section is not None:
            m = re.match(r"^(\d+)\s+(\w+)$", line)
            if m:
                ids[int(m.group(1))] = m.group(2)
            continue
        if line.startswith("$"):
            m = re.match(r"^\$(\w+)\s*=\s*(.*)$", line)
            if not m:
                m2 = re.match(r"^\$(\w+)$", line)
                types[m2.group(1)] = ("prim", m2.group(1))
                continue
            name, rest = m.group(1), m.group(2).strip()
            if rest.startswith("{"):
                body = rest
                while "}" not in body:
                    body += " " + lines[i].split("#")[0].strip()
                    i += 1
                body = body[body.index("{") + 1: body.index("}")]
                toks = re.findall(r"(\w+)(?:\s*=\s*(-?\d+))?", body)
                vals, nxt = [], 0
                for n, v in toks:
                    if v != "":
                        nxt = int(v)
                    vals.append((n, nxt))
                    nxt += 1
                types[name] = ("enum", vals)
            else:
                types[name] = ("alias", rest)
            continue
        if line.startswith("@"):
            m = re.match(r"^@(\w+)\s*(?::\s*(.*))?$", line)
            name = m.group(1)
            parents = (m.group(2) or "").split()
            cur = {"parents": parents, "props": []}
            classes[name] = cur
            continue
        if cur is not None:
            parts = line.split()
            if len(parts) >= 3:
                cur["props"].append((parts[0], int(parts[1]), parts[2], comment))
    return types, classes, ids


def resolve_type(types, t):
    """Follow aliases until a prim or enum is reached."""
    seen = 0
    while t in types and types[t][0] == "alias" and seen < 20:
        t = types[t][1]
        seen += 1
    return t, types.get(t)


def all_props(classes, name, _seen=None):
    """Properties of a class including inherited ones (child overrides parent by name)."""
    c = classes[name]
    out = {}
    for p in c["parents"]:
        if p in classes:
            for prop in all_props(classes, p):
                out[prop[0]] = prop
    for prop in c["props"]:
        out[prop[0]] = prop
    return list(out.values())


def object_names(path=None):
    path = path or os.path.join(SRC, "objects.csv")
    out = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        a, b = line.split(",", 1)
        out[int(a)] = b
    return out


if __name__ == "__main__":
    t, c, ids = parse()
    print(len(t), "types", len(c), "classes", len(ids), "ids")
    for cid in (2067, 3016, 2905):
        print(cid, ids[cid], len(all_props(c, ids[cid])))
