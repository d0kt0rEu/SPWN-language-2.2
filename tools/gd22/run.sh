#!/bin/bash
# usage: tools/gd22/run.sh script.spwn [extra spwn flags]
# Compiles with the full pipeline (optimizer + writer) against a throwaway save file and prints the decoded objects.
set -e
T="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$T/../.." && pwd)"
SAVE=$(mktemp --suffix=.dat)
python3 "$T/gdsave.py" make "$SAVE"
f=$(realpath "$1"); shift
cd "$REPO"
./target/release/spwn build "$f" -s "$SAVE" -i "$REPO/libraries" "$@" 2>&1 | grep -v -E "^\s*$" | sed 's/\x1b\[[0-9;]*m//g' | tail -${TAIL:-25}
echo "--- decoded ---"
python3 "$T/gdsave.py" dump "$SAVE"
rm -f "$SAVE"
