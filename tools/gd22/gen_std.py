#!/usr/bin/env python3
"""Generates the Geometry Dash 2.2 part of SPWN's standard library from the community property schema.

Writes:
  libraries/std/constants_gd22.spwn   obj_props / obj_ids / enum constants
  libraries/std/gd22.spwn             trigger functions (`name(...)` adds the trigger to the current trigger
                                      function, `name_trigger(...)` returns it as an @object) + @group sugar
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import schema as S

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
STD = os.path.join(REPO, "libraries", "std")
types, classes, ids = S.parse()
disp = S.object_names()

# ------------------------------------------------------------------------------------------------
# curated data
# ------------------------------------------------------------------------------------------------

# the triggers the original SPWN already models by hand; these keep their own implementations
LEGACY = {899, 901, 1006, 1007, 1049, 1268, 1346, 1347, 1520, 1585, 1595, 1611, 1811, 1812, 1814, 1815,
          1817, 1818, 1819, 1616, 32, 33, 1612, 1613}

PROP_RENAME = {"scale_trigger_scale_x": "scale_x", "scale_trigger_scale_y": "scale_y"}

# properties every trigger has; they are never exposed as parameters (spawn/multi/touch are managed by SPWN)
BASE_SKIP = {"spawn_triggered", "touch_triggered", "multi_triggered", "ignore_linked", "ignore_gparent",
             "easing", "easing_rate"}

KEYWORDS = {"as", "break", "case", "continue", "else", "extract", "false", "for", "if", "impl", "import", "in",
            "is", "let", "match", "null", "obj", "return", "self", "switch", "sync", "throw", "trigger", "true",
            "type", "while"}

# id -> dict(name, req=[...], defaults={prop: value}, wait=prop, easing=bool, self=prop, desc=str)
SPECS = {}


def spec(id_, name, desc, req=(), defaults=None, wait=None, easing=False, self_=None):
    SPECS[id_] = dict(name=name, desc=desc, req=list(req), defaults=defaults or {}, wait=wait, easing=easing,
                      self=self_)


# cameras
spec(1913, "camera_zoom", "Zooms the camera", ["zoom"], {"time": 0}, "time", True)
spec(1914, "camera_static", "Locks the camera to a group", ["target_group"], {"duration": 0}, "duration", True)
spec(1916, "camera_offset", "Offsets the camera (GD units, 30 per block)", ["offset_x", "offset_y"],
     {"move_time": 0}, "move_time", True)
spec(2015, "camera_rotate", "Rotates the camera", ["degrees"], {"move_time": 0}, "move_time", True)
spec(2062, "camera_edge", "Sets which group blocks the camera at a screen edge", ["edge", "target_group"])
spec(2925, "camera_mode", "Switches the camera between free mode and normal mode")
spec(2016, "camera_guide", "Camera guide object (editor only preview of a camera zoom/offset)")
spec(2901, "gameplay_offset", "Gameplay offset camera trigger (the schema documents no properties for it)")
# gameplay
spec(2900, "gameplay_rotation", "Gameplay rotation (arrow) trigger: rotates the gameplay direction")
spec(1917, "reverse", "Reverses the direction of the gameplay")
spec(1935, "timewarp", "Changes the game speed", ["time_mod"])
spec(2066, "gravity", "Sets the player gravity", ["gravity"])
spec(1932, "player_control", "Controls what a player can do")
spec(2899, "options", "Options trigger: toggles several level options")
spec(3600, "end_level", "End trigger: ends the level")
spec(3022, "teleport", "Teleports the player to a group", ["target_group_id"])
spec(2063, "checkpoint", "Checkpoint trigger")
# audio
spec(1934, "song", "Plays a song", ["song"])
spec(3605, "edit_song", "Edits a playing song channel")
spec(3602, "sfx", "Plays a sound effect", ["sfx_id"])
spec(3603, "edit_sfx", "Edits a playing sound effect")
spec(3604, "game_event", "Fires a group when a game event happens (jump, death, landing...)", ["group_id"])
# visual
spec(3613, "ui", "UI trigger: pins a group to a position on the screen", ["group_id", "ui_target"],
     self_="group_id")
spec(2903, "gradient", "Gradient trigger")
spec(3029, "change_background", "Changes the background image", ["background"])
spec(3030, "change_ground", "Changes the ground image", ["ground"])
spec(3031, "change_middleground", "Changes the middleground image", ["middle_ground"])
spec(3606, "background_speed", "Background speed trigger (the schema documents no properties for it)")
spec(3612, "middleground_speed", "Middleground speed trigger (the schema documents no properties for it)")
spec(2999, "edit_middleground", "Edit middleground trigger (the schema documents no properties for it)")
spec(2067, "scale", "Scales a group", ["target_group"], {"scale_x": 1, "scale_y": 1, "duration": 0}, "duration",
     True, "target_group")
# advanced follow
spec(3016, "advanced_follow", "Advanced follow trigger", ["target_group", "follow_group"], self_="target_group")
spec(3660, "edit_advanced_follow", "Edits the advanced follow of a group", ["target_group"],
     self_="target_group")
spec(3661, "retarget_advanced_follow", "Changes what an advanced follow follows", ["target_group", "follow_group"],
     self_="target_group")
# area triggers
for i, n in ((3006, "move"), (3007, "rotate"), (3008, "scale"), (3009, "fade"), (3010, "tint")):
    spec(i, "area_" + n, f"Area {n} trigger: applies the effect to objects based on their position on screen",
         ["target_group"], self_="target_group")
for i, n in ((3011, "move"), (3012, "rotate"), (3013, "scale"), (3014, "fade"), (3015, "tint")):
    spec(i, "edit_area_" + n, f"Edits an area {n} effect (use_eid selects whether group_effect_id is an effect id)",
         ["group_effect_id"], {"duration": 0})
spec(3024, "area_stop", "Stops an area effect", ["effect_id"])
# keyframes
spec(3032, "keyframe_point", "Keyframe point object")
spec(3033, "keyframe_animation", "Starts a keyframe animation", ["animation_group_id", "target_group"])
# random & friends
spec(1912, "random", "Spawns one of two groups at random", ["group_id_1", "group_id_2"], {"chance": 50})
spec(2068, "advanced_random", "Spawns random groups with weights: list is [[group, chance], ...]", ["list"])
spec(3607, "sequence", "Spawns groups in order: sequence is [[group, delay], ...]", ["sequence"])
spec(3608, "spawn_particle", "Spawns a particle system", ["particle_group"], self_="particle_group")
spec(3618, "reset", "Resets a group (sequence/random state)", ["group_id"], self_="group_id")
# items and timers
spec(3619, "item_edit", "Item edit trigger: target = op(item1 (op1) item2) * mod")
spec(3620, "item_compare", "Item compare trigger: spawns true_id or false_id depending on the comparison")
spec(3641, "persistent_item", "Persistent item setup trigger", ["item_id"])
spec(3614, "timer", "Starts a timer (time trigger)", ["item_id"])
spec(3615, "timer_event", "Spawns a group when a timer reaches a time", ["item_id", "target_id", "target_time"])
spec(3617, "timer_control", "Starts or stops a timer", ["item_id"])
# collisions, blocks, bpm, particles
spec(3609, "instant_collision", "Instant collision trigger", ["block_a_id", "block_b_id", "true_id"])
spec(3640, "collision_state_block", "Collision state block object")
spec(3643, "toggle_block", "Player touch toggle block object")
spec(2069, "force_block", "Force block object")
spec(3645, "force_circle", "Force circle object")
spec(3642, "bpm", "BPM guide")
spec(2065, "custom_particles", "Custom particles object")
# shaders
spec(2904, "shader_setup", "Shader setup trigger: chooses the layers shaders apply to")
for i, n in ((2905, "shockwave"), (2907, "shockline"), (2909, "glitch"), (2910, "chromatic"),
             (2911, "chromatic_glitch"), (2912, "pixelate"), (2913, "lens_circle"), (2914, "radial_blur"),
             (2915, "motion_blur"), (2916, "bulge"), (2917, "pinch"), (2919, "grayscale"), (2920, "sepia"),
             (2921, "invert_color"), (2922, "hue"), (2923, "edit_color")):
    spec(i, n + "_shader", f"{n.replace('_', ' ').title()} shader trigger")
spec(2924, "split_screen_shader", "Split screen shader trigger (the schema documents no properties for it)")
# enter effects
for i in (22, 23, 24, 25, 26, 27, 28, 55, 56, 57, 58, 59, 1915, 3017, 3018, 3019, 3020, 3021, 3023):
    n = re.sub(r"[^a-z0-9]+", "_", disp[i].lower().replace(" trigger", "")).strip("_")
    spec(i, n, disp[i])
SPECS[1915]["name"] = "dont_enter_effect"
SPECS[3017]["name"] = "enter_move"
SPECS[3018]["name"] = "enter_rotate"
SPECS[3019]["name"] = "enter_scale"
SPECS[3020]["name"] = "enter_fade"
SPECS[3021]["name"] = "enter_tint"
SPECS[3023]["name"] = "enter_stop"

# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------

def chain(cn):
    out = [cn]
    for p in classes[cn]["parents"]:
        if p in classes:
            out += chain(p)
    return out


COMMON = {p[0] for p in S.all_props(classes, "Common")}

enum_of = {}


def type_info(t):
    """-> (kind, spwn pattern, enum name or None)"""
    rt, info = S.resolve_type(types, t)
    if info and info[0] == "enum":
        return "Number", "@number", rt
    if t in ("GroupID", "GroupOrControlID", "ColorOrGroupID"):
        return "Group", "@group | @trigger_function" + (" | @number" if t != "GroupID" else ""), None
    if t == "GroupOrEffectID":
        return "Group", "@group | @trigger_function | @number", None
    if t == "ColorID":
        return "Color", "@color", None
    if t in ("ItemID", "TimerID", "ItemOrTimerID"):
        return "Item", "@item", None
    if t == "BlockID":
        return "Block", "@block", None
    if t in ("GroupList", "RemapList"):
        return "GroupList", "[@group | @trigger_function] | @group | @trigger_function", None
    if t in ("AdvRandomList", "SequenceList"):
        return "GroupPairs", "@array", None
    if t == "Bool":
        return "Bool", "@bool", None
    if t in ("String", "HSVString", "ParticleString", "EventList"):
        return "Text", "@string", None
    return "Number", "@number", None


def snake_upper(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()


def esc(s):
    return s.replace("\\", "/").replace('"', "'")


# ------------------------------------------------------------------------------------------------
# the classes we expose
# ------------------------------------------------------------------------------------------------

def is_triggerish(cn):
    return "Trigger" in chain(cn)


expose = {}  # id -> class
for i, cn in ids.items():
    if cn not in classes:
        continue
    if i in SPECS or (is_triggerish(cn) and i not in LEGACY):
        expose[i] = cn
missing = [i for i, cn in expose.items() if i not in SPECS]
if missing:
    sys.exit("no spec for " + ", ".join(f"{i} {disp.get(i)}" for i in missing))
absent = [i for i in SPECS if i not in ids]
if absent:
    sys.exit("spec for unknown ids " + str(absent))


def own_props(i):
    """Properties of this object's class that aren't shared base properties, in schema order, deduped by key."""
    cn = ids[i]
    out, seen_keys = [], set()
    for name, key, typ, comment in S.all_props(classes, cn):
        if name in COMMON or name in BASE_SKIP:
            continue
        name = PROP_RENAME.get(name, name)
        if key in seen_keys:
            print(f"  note: {disp.get(i)} has two properties on key {key}; keeping the first, skipping {name}")
            continue
        seen_keys.add(key)
        out.append((name, key, typ, comment))
    return out


# ------------------------------------------------------------------------------------------------
# object property constants
# ------------------------------------------------------------------------------------------------

constants_src = open(os.path.join(STD, "constants.spwn")).read()
existing_props = {}
for m in re.finditer(r"^\s+(\w+): ok\((\d+), (.+), \"(\w+)\"\),?\s*$", constants_src, re.M):
    existing_props[m.group(1)] = int(m.group(2))

# every property of every exposed class AND of the legacy trigger classes (so their extra keys get names too)
const_classes = dict(expose)
for i in LEGACY:
    if i in ids and ids[i] in classes:
        const_classes[i] = ids[i]

occ = collections.defaultdict(collections.Counter)  # name -> key -> count
for i, cn in const_classes.items():
    for name, key, typ, comment in own_props(i):
        occ[name][key] += 1

# the shared base properties get constants too
base_extra = []
for name, key, typ, comment in S.all_props(classes, "Trigger"):
    if name in BASE_SKIP and name not in COMMON:
        base_extra.append((name, key, typ, comment))
for name, key, typ, comment in base_extra:
    occ[name][key] += 1

prop_const = {}       # (id, propname) -> constant name
new_consts = {}       # constant name -> (key, pattern)
used_names = set(existing_props)


def class_stem(i):
    return snake_upper(SPECS[i]["name"]) if i in SPECS else snake_upper(disp.get(i, str(i)))


def assign(i, name, key, pattern):
    up = snake_upper(name)
    plurality = occ[name].most_common(1)[0][0]
    if up in existing_props:
        if existing_props[up] == key:
            prop_const[(i, name)] = up
            return
        cand = class_stem(i) + "_" + up
    elif key != plurality and len(occ[name]) > 1:
        cand = class_stem(i) + "_" + up
    else:
        cand = up
    if cand in new_consts and new_consts[cand][0] != key:
        cand = class_stem(i) + "_" + up
    if cand in existing_props and existing_props[cand] != key:
        sys.exit(f"constant clash {cand}")
    if cand in new_consts and new_consts[cand][0] != key:
        sys.exit(f"constant clash {cand}")
    new_consts.setdefault(cand, (key, pattern))
    prop_const[(i, name)] = cand


for i, cn in const_classes.items():
    for name, key, typ, comment in own_props(i):
        assign(i, name, key, type_info(typ)[1])
for name, key, typ, comment in base_extra:
    assign(0, name, key, type_info(typ)[1])
# `easing` is a plain Easing on every trigger that has it
EASING_CONST = prop_const[(0, "easing")]
EASING_RATE_CONST = prop_const[(0, "easing_rate")]

# ------------------------------------------------------------------------------------------------
# enums
# ------------------------------------------------------------------------------------------------

used_enums = collections.OrderedDict()
for i in const_classes:
    for name, key, typ, comment in own_props(i):
        rt, info = S.resolve_type(types, typ)
        if info and info[0] == "enum":
            used_enums[rt] = info[1]
for name, key, typ, comment in base_extra:
    rt, info = S.resolve_type(types, typ)
    if info and info[0] == "enum":
        used_enums[rt] = info[1]

# ------------------------------------------------------------------------------------------------
# constants_gd22.spwn
# ------------------------------------------------------------------------------------------------

out = []
w = out.append
w("// @generated by spwn-tools/gen_std.py from the community Geometry Dash 2.2 object property schema.")
w("// Do not edit by hand; regenerate instead.")
w("#[no_std, cache_output]")
w("")
w("ok = (id: @number, pat: @pattern | @type_indicator, name: @string) {")
w("    return @object_key::{id, pattern: pat, name}")
w("}")
w("")
w("return {")
w("    obj_ids: {")
w("        triggers: {")
trig_names = {}
for i in sorted(SPECS):
    if i in LEGACY:
        continue
    cn = ids[i]
    if not is_triggerish(cn) and i not in (3606,):
        continue
    n = snake_upper(SPECS[i]["name"])
    assert n not in trig_names, n
    trig_names[n] = i
    w(f"            {n}: {i},")
w("        },")
w("        special: {")
spec_names = {}
for i in sorted(SPECS):
    cn = ids[i]
    if is_triggerish(cn) or i in LEGACY:
        continue
    n = snake_upper(SPECS[i]["name"])
    spec_names[n] = i
    w(f"            {n}: {i},")
w("        },")
w("    },")
w("    obj_props: {")
for cname in sorted(new_consts, key=lambda c: (new_consts[c][0], c)):
    key, pat = new_consts[cname]
    w(f'        {cname}: ok({key}, {pat}, "{cname}"),')
w("    },")
w("    gd_enums: {")
for en, vals in used_enums.items():
    w(f"        {en}: {{")
    seen = set()
    for n, v in vals:
        un = snake_upper(n)
        if un in seen:
            continue
        seen.add(un)
        w(f"            {un}: {v},")
    w("        },")
w("    },")
w("}")
w("")
open(os.path.join(STD, "constants_gd22.spwn"), "w").write("\n".join(out))

# ------------------------------------------------------------------------------------------------
# gd22.spwn
# ------------------------------------------------------------------------------------------------

def spwn_val(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    return repr(v)


def example_value(pat):
    if pat.startswith("@group"):
        return "1g"
    if pat == "@color":
        return "1c"
    if pat == "@item":
        return "1i"
    if pat == "@block":
        return "1b"
    if pat == "@bool":
        return "true"
    if pat == "@string":
        return '""'
    if pat.startswith("["):
        return "[1g, 2g]" if "@group" in pat else "[]"
    if pat == "@array":
        return "[[1g, 1]]"
    return "1"


def param_name(n):
    return n + "_" if n in KEYWORDS else n


def enum_note(typ):
    rt, info = S.resolve_type(types, typ)
    if info and info[0] == "enum":
        vals = info[1]
        if len(vals) <= 12:
            return f" Values: gd_enums.{rt} ({', '.join(f'{snake_upper(n)}={v}' for n, v in vals)})."
        return f" See gd_enums.{rt}."
    return ""


def make_function(i, form, selfmode=False):
    """form: 'obj' | 'ctx'.  Returns the source of one dict entry (or method when selfmode)."""
    sp = SPECS[i]
    props = own_props(i)
    byname = {p[0]: p for p in props}
    easing_props = sp["easing"]
    req = [r for r in sp["req"]]
    for r in req:
        assert r in byname, (i, r, list(byname))
    selfprop = sp["self"] if selfmode else None
    params = []   # (name, pat, default or None, desc, required)
    for r in req:
        if r == selfprop:
            continue
        name, key, typ, comment = byname[r]
        _, pat, _ = type_info(typ)
        params.append((name, pat, "REQ", (comment or name.replace("_", " ")) + enum_note(typ), r))
    ordered = sorted((p for p in props if p[0] not in req),
                     key=lambda p: (list(sp["defaults"]).index(p[0]) if p[0] in sp["defaults"] else 999))
    for name, key, typ, comment in ordered:
        _, pat, _ = type_info(typ)
        d = sp["defaults"].get(name, None)
        if name in sp["defaults"]:
            params.append((name, pat, spwn_val(d), (comment or name.replace("_", " ")) + enum_note(typ), name))
        else:
            params.append((name, pat + " | @NULL", "null", (comment or name.replace("_", " ")) + enum_note(typ), name))
    if easing_props:
        params.append(("easing", "@easing_type | @number | @NULL", "null", "Easing type", "easing"))
        params.append(("easing_rate", "@number | @NULL", "null", "Easing rate", "easing_rate"))

    fname = sp["name"] if (form == "ctx" or selfmode) else sp["name"] + "_trigger"
    if selfmode:
        # methods read better without the trigger noun, but never shadow existing group methods
        fname = sp["name"]
    ex_args = []
    for p in params:
        if p[2] == "REQ":
            ex_args.append(example_value(p[1]))
    if selfmode:
        example = f"1g.{fname}({', '.join(ex_args)})"
    else:
        example = f"{fname}({', '.join(ex_args)})"
    ret = "@NULL" if (form == "ctx" or selfmode) else "@object"
    lines = []
    L = lines.append
    sig = []
    if selfmode:
        sig.append("        self")
    for name, pat, d, desc, _ in params:
        pn = param_name(name)
        a = f'#[desc("{esc(desc)}")] {pn}: {pat}'
        if d != "REQ":
            a += f" = {d}"
        sig.append("        " + a)
    desc = sp["desc"]
    if form == "obj" and not selfmode:
        desc += " (returns the trigger as an object; add it with `$.add` or `.add()`)"
    kind = "obj" if form == "obj" else "trigger"
    L(f'    {fname}: #[desc("{esc(desc)}"), example("{esc(example)}")] (')
    L(",\n".join(sig) + ("," if sig else ""))
    L(f"    ) -> {ret} {{")
    L(f"        let o = obj {{ OBJ_ID: {i} }}")
    for name, pat, d, desc_, pname in params:
        pn = param_name(name)
        if pname in ("easing", "easing_rate") and easing_props and name in ("easing", "easing_rate"):
            const = EASING_CONST if name == "easing" else EASING_RATE_CONST
            val = f"_ev({pn})"
        else:
            const = prop_const[(i, pname)]
            val = pn
        if d == "REQ" or d not in ("null",):
            L(f"        $.edit_obj(o, {const}, {val})")
        else:
            L(f"        if !({pn} is @NULL) {{ $.edit_obj(o, {const}, {val}) }}")
    if selfprop:
        const = prop_const[(i, selfprop)]
        L(f"        $.edit_obj(o, {const}, self)")
    if form == "obj" and not selfmode:
        L("        return o")
    else:
        L("        $.add($.as_trigger(o))")
        if sp["wait"]:
            wn = param_name(sp["wait"])
            if sp["defaults"].get(sp["wait"]) is not None:
                L(f"        wait({wn})")
            else:
                L(f"        if !({wn} is @NULL) {{ wait({wn}) }}")
    L("    }")
    return "\n".join(lines)


def no_trigger_form(i):
    """Objects that aren't triggers only get the object form."""
    return not is_triggerish(ids[i])


body_entries = []
sugar_entries = []
for i in sorted(SPECS):
    if i in LEGACY:
        continue
    body_entries.append(make_function(i, "obj").rstrip())
    if not no_trigger_form(i):
        body_entries.append(make_function(i, "ctx").rstrip())
        if SPECS[i]["self"]:
            sugar_entries.append(make_function(i, "ctx", selfmode=True).rstrip())


# hand written extensions of triggers SPWN already had (their new 2.2 properties)
STATIC_SUGAR = """    pause: #[desc("Pauses everything that is running on this group (stop trigger in pause mode)"), example("1g.pause()")]
    (self) -> @NULL {
        let o = obj { OBJ_ID: 1616 }
        $.edit_obj(o, TARGET, self)
        $.edit_obj(o, STOP_PAUSE_RESUME, 1)
        $.add($.as_trigger(o))
    },

    resume: #[desc("Resumes everything that was paused on this group (stop trigger in resume mode)"), example("1g.resume()")]
    (self) -> @NULL {
        let o = obj { OBJ_ID: 1616 }
        $.edit_obj(o, TARGET, self)
        $.edit_obj(o, STOP_PAUSE_RESUME, 2)
        $.add($.as_trigger(o))
    },"""

STATIC_FUNCS = """    pause_trigger: #[desc("Returns a stop trigger in pause mode as an object"), example("$.add( pause_trigger(1g) )")]
    (#[desc("Group to pause")] group: @group | @trigger_function) -> @object {
        return obj { OBJ_ID: 1616, TARGET: group, STOP_PAUSE_RESUME: 1 }
    },

    resume_trigger: #[desc("Returns a stop trigger in resume mode as an object"), example("$.add( resume_trigger(1g) )")]
    (#[desc("Group to resume")] group: @group | @trigger_function) -> @object {
        return obj { OBJ_ID: 1616, TARGET: group, STOP_PAUSE_RESUME: 2 }
    },

    pickup_multiply_trigger: #[desc("Returns a pickup trigger that multiplies an item by a number, as an object"), example("$.add( pickup_multiply_trigger(1i, 2) )")]
    (#[desc("Item to modify")] item_id: @item, #[desc("Factor")] factor: @number) -> @object {
        return obj { OBJ_ID: 1817, ITEM: item_id, PICKUP_TRIGGER_MODIFIER: factor, MULTIPLY_DIVIDE: 1 }
    },

    pickup_divide_trigger: #[desc("Returns a pickup trigger that divides an item by a number, as an object"), example("$.add( pickup_divide_trigger(1i, 2) )")]
    (#[desc("Item to modify")] item_id: @item, #[desc("Divisor")] divisor: @number) -> @object {
        return obj { OBJ_ID: 1817, ITEM: item_id, PICKUP_TRIGGER_MODIFIER: divisor, MULTIPLY_DIVIDE: 2 }
    },

    pickup_set_trigger: #[desc("Returns a pickup trigger that overrides an item with a number, as an object"), example("$.add( pickup_set_trigger(1i, 5) )")]
    (#[desc("Item to modify")] item_id: @item, #[desc("New value")] value: @number) -> @object {
        return obj { OBJ_ID: 1817, ITEM: item_id, COUNT: value, PICKUP_TRIGGER_OVERRIDE: true }
    },

    pickup_multiply: #[desc("Multiplies an item by a number"), example("pickup_multiply(1i, 2)")]
    (#[desc("Item to modify")] item_id: @item, #[desc("Factor")] factor: @number) -> @NULL {
        $.add($.as_trigger(obj { OBJ_ID: 1817, ITEM: item_id, PICKUP_TRIGGER_MODIFIER: factor, MULTIPLY_DIVIDE: 1 }))
    },

    pickup_divide: #[desc("Divides an item by a number"), example("pickup_divide(1i, 2)")]
    (#[desc("Item to modify")] item_id: @item, #[desc("Divisor")] divisor: @number) -> @NULL {
        $.add($.as_trigger(obj { OBJ_ID: 1817, ITEM: item_id, PICKUP_TRIGGER_MODIFIER: divisor, MULTIPLY_DIVIDE: 2 }))
    },

    pickup_set: #[desc("Sets an item to a number"), example("pickup_set(1i, 5)")]
    (#[desc("Item to modify")] item_id: @item, #[desc("New value")] value: @number) -> @NULL {
        $.add($.as_trigger(obj { OBJ_ID: 1817, ITEM: item_id, COUNT: value, PICKUP_TRIGGER_OVERRIDE: true }))
    },

    collision_player: #[desc("Collision trigger between a block and the player(s) (returns an event)"), example(u"
        on(collision_player(1b, p1 = true), !{
            BG.set(rgb(0, 0, 0))
        })
    ")] (
        #[desc("Block ID")] block: @block,
        #[desc("React to player 1")] p1: @bool = false,
        #[desc("React to player 2")] p2: @bool = false,
        #[desc("React to the player-to-player collision (PP)")] pp: @bool = false,
        #[desc("Trigger when the collision ends instead of when it starts")] on_exit: @bool = false,
    ) -> @event {
        event = @event::new()
        $.add( trigger{
            OBJ_ID: 1815,
            BLOCK_A: block,
            ACTIVATE_GROUP: true,
            ACTIVATE_ON_EXIT: on_exit,
            P1: p1,
            P2: p2,
            PP: pp,
            TARGET: event.io,
        })
        return event
    },"""

# names must not collide with anything the std library already exports or group methods
taken = set()
for f in ("general_triggers.spwn", "control_flow.spwn", "events.spwn", "frames.spwn", "group.spwn"):
    src = open(os.path.join(STD, f)).read()
    taken |= set(re.findall(r"^\s{1,4}([a-z_][a-z_0-9]*):", src, re.M))
names = [re.match(r"\s{4}(\w+):", e).group(1) for e in body_entries + re.findall(r"^    \w+: ", STATIC_FUNCS, re.M)]
dupes = [n for n, c in collections.Counter(names).items() if c > 1]
clash = [n for n in names if n in taken]
sugar_names = [re.match(r"\s{4}(\w+):", e).group(1) for e in sugar_entries] + ["pause", "resume"]
sclash = [n for n in sugar_names if n in taken]
if dupes or clash or sclash:
    sys.exit(f"name problems: duplicates={dupes} clashes={clash} group-method clashes={sclash}")

g = []
w = g.append
w("// @generated by spwn-tools/gen_std.py from the community Geometry Dash 2.2 object property schema.")
w("// Do not edit by hand; regenerate instead.")
w("//")
w("// For every trigger `name(...)` adds it to the current trigger function and `name_trigger(...)` returns")
w("// it as an @object. Only the parameters you pass are written to the level, everything else keeps the")
w("// game's default. Enumerated properties take plain numbers; the named values are in `gd_enums`.")
w("#[no_std, cache_output]")
w("constants = import \"constants.spwn\"")
w("")
w("extract constants.obj_props")
w("extract import \"control_flow.spwn\"")
w("")
w("_ev = (x) => match x {")
w("    @easing_type: x.id,")
w("    else: x,")
w("}")
w("")
w("impl @group {")
w(",\n\n".join(sugar_entries + [STATIC_SUGAR]))
w("}")
w("")
w("return {")
w(",\n\n".join(body_entries + [STATIC_FUNCS]))
w("}")
w("")
open(os.path.join(STD, "gd22.spwn"), "w").write("\n".join(g))
print(f"{len(body_entries)} functions, {len(sugar_entries)} group methods, {len(new_consts)} new property constants, "
      f"{len(used_enums)} enums")
