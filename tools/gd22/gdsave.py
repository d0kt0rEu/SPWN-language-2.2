"""Dummy GD save helpers so SPWN's full pipeline (optimizer + writer) can be tested
without ever touching a real save file.

  python3 gdsave.py make  <out.dat>            create a fresh save with one empty level
  python3 gdsave.py dump  <save.dat>           decode and print the objects, with names from the schema
"""
import base64
import gzip
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import schema as S

HEADER = "kS38,1_40_2_125_3_255_11_255_12_255_13_255_4_-1_6_1000_7_1_15_1_18_0_8_1|,kA13,0,kA15,0,kA16,0,kA14,,kA6,0,kA7,0,kA17,0,kA18,0,kS39,0,kA2,0,kA3,0,kA8,0,kA4,0,kA9,0,kA10,0,kA11,0;"


def b64url_gzip(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(gzip.compress(data))


def un_b64url_gzip(data: bytes) -> bytes:
    data = data.replace(b"\0", b"")
    pad = (-len(data)) % 4
    return gzip.decompress(base64.urlsafe_b64decode(data + b"=" * pad))


def xor11(data: bytes) -> bytes:
    return bytes(b ^ 11 for b in data)


def make(path, level=HEADER):
    xml = (
        '<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict>'
        "<k>LLM_01</k><d><k>_isArr</k><t /><k>k_0</k><d><k>kCEK</k><i>4</i>"
        "<k>k2</k><s>test</s><k>k4</k><s>%s</s></d></d></dict></plist>"
    ) % b64url_gzip(level.encode()).decode()
    open(path, "wb").write(xor11(b64url_gzip(xml.encode())))


def read_levelstring(path):
    xml = un_b64url_gzip(xor11(open(path, "rb").read())).decode("latin-1")
    m = re.search(r"<k>k4</k><s>([^<]*)</s>", xml)
    return un_b64url_gzip(m.group(1).encode()).decode("latin-1")


def parse_objects(ls):
    objs = []
    for chunk in ls.split(";")[1:]:
        if not chunk.strip():
            continue
        parts = chunk.split(",")
        props = {}
        for i in range(0, len(parts) - 1, 2):
            props[int(parts[i])] = parts[i + 1]
        objs.append(props)
    return objs


_types = _classes = _ids = None


def _load():
    global _types, _classes, _ids
    if _types is None:
        _types, _classes, _ids = S.parse()


def prop_names(obj_id):
    _load()
    cls = _ids.get(obj_id)
    if cls is None:
        return None, {}
    return cls, {p[1]: p[0] for p in S.all_props(_classes, cls)}


def dump(path, show_all=False):
    ls = read_levelstring(path)
    for o in parse_objects(ls):
        oid = int(o.get(1, "0"))
        cls, names = prop_names(oid)
        bits = []
        for k in sorted(o):
            if k == 1:
                continue
            nm = names.get(k)
            bits.append(f"{nm or '?'+str(k)}[{k}]={o[k]}")
        print(f"#{oid} {cls or '(unknown)'}: " + ", ".join(bits))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "make":
        make(sys.argv[2])
    elif cmd == "dump":
        dump(sys.argv[2])
