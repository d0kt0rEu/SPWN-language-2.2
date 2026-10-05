# Geometry Dash 2.2 support tooling

Everything 2.2 related in the standard library is generated from the community property table
(<https://github.com/FlowVix/gd-info-explorer>, `src/lib/schema.txt` and `objects.csv`).

```
git clone https://github.com/FlowVix/gd-info-explorer tools/gd22/gd-info-explorer   # or set GD_INFO_DIR
python3 tools/gd22/gen_std.py        # libraries/std/constants_gd22.spwn + libraries/std/gd22.spwn
python3 tools/gd22/gen_props_rs.py   # compiler/src/gd_props.rs (what each property key holds, for reading levels)
cargo build --release -p spwn
python3 tools/gd22/test_all.py       # calls every generated function with every parameter and checks the written keys
tools/gd22/run.sh script.spwn        # full compile against a throw-away save file, prints the decoded objects
```

`gen_std.py` has a small curated table (`SPECS`) with function names, required parameters, defaults and
descriptions; all other properties come straight from the schema.

The scripts never touch a real save file: `gdsave.py` creates a dummy save in the same format.
