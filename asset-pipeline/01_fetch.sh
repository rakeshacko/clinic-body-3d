#!/usr/bin/env bash
# Phase 0.1 — clone source repos into ./sources (gitignored).
#
#   sources/bodyparts3d : per-structure STL geometry named by FMA id (CC BY-SA 2.1 Japan). GEOMETRY SOURCE.
#   sources/z-anatomy   : structure naming / grouping reference only (CC BY-SA 4.0). NOT used as geometry.
#
# BodyParts3D is ~900 MB if fully checked out. We do a real `git clone` but use a partial
# (blob:none) + sparse checkout to materialize only the metadata and the exact STLs referenced
# by fma-to-system.json (+ the skin shell). Set FULL_CLONE=1 to check out the entire repo instead.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p sources

BP3D_REMOTE="https://github.com/Kevin-Mattheus-Moerman/BodyParts3D"
ZAN_REMOTE="https://github.com/Z-Anatomy/Models-of-human-anatomy"
BP3D_DIR="sources/bodyparts3d"
ZAN_DIR="sources/z-anatomy"
DATA="assets/BodyParts3D_data"
SHELL_FMA="FMA7163"   # skin -> body_shell

echo "==> BodyParts3D (geometry)"
if [ ! -d "$BP3D_DIR/.git" ]; then
  if [ "${FULL_CLONE:-0}" = "1" ]; then
    git clone --depth 1 "$BP3D_REMOTE" "$BP3D_DIR"
  else
    git clone --depth 1 --filter=blob:none --sparse "$BP3D_REMOTE" "$BP3D_DIR"
  fi
fi

if [ "${FULL_CLONE:-0}" != "1" ]; then
  # Build the sparse path set: metadata files + each referenced STL + the skin shell.
  paths=$(python3 - "$SHELL_FMA" <<'PY'
import json, sys
shell = sys.argv[1]
m = json.load(open("fma-to-system.json"))
data = "assets/BodyParts3D_data"
out = [f"{data}/LICENSE_content", f"{data}/parts_list_e.txt", f"{data}/README_e.html"]
for sysid, items in m["systems"].items():
    for it in items:
        out.append(f"{data}/stl/{it['fma']}.stl")
out.append(f"{data}/stl/{shell}.stl")
print("\n".join(out))
PY
)
  # The partial+sparse clone can leave a promisor remote-helper briefly holding a lock; clear
  # stale locks (only when no git process is live for this repo) and retry the sparse-checkout.
  (
    cd "$BP3D_DIR"
    for attempt in 1 2 3; do
      if ! pgrep -f "$BP3D_DIR" >/dev/null 2>&1; then
        rm -f .git/index.lock .git/info/sparse-checkout.lock 2>/dev/null || true
      fi
      if git sparse-checkout init --no-cone \
         && printf "%s\n" $paths | git sparse-checkout set --no-cone --stdin \
         && git checkout main; then
        break
      fi
      echo "  sparse-checkout attempt $attempt failed; retrying in 2s..."
      sleep 2
    done
  )
fi

missing=0
while read -r p; do
  [ -z "$p" ] && continue
  if [ ! -f "$BP3D_DIR/$p" ]; then echo "  MISSING: $p"; missing=$((missing+1)); fi
done <<EOF
$(python3 - "$SHELL_FMA" <<'PY'
import json, sys
shell=sys.argv[1]; m=json.load(open("fma-to-system.json")); data="assets/BodyParts3D_data"
ps=[f"{data}/stl/{it['fma']}.stl" for items in m["systems"].values() for it in items]
ps.append(f"{data}/stl/{shell}.stl")
print("\n".join(ps))
PY
)
EOF
echo "  STL fetch check: $missing missing"

echo "==> Z-Anatomy (naming reference only)"
if [ ! -d "$ZAN_DIR/.git" ]; then
  git clone --depth 1 "$ZAN_REMOTE" "$ZAN_DIR" || echo "  (Z-Anatomy clone failed — non-fatal; used as naming reference only)"
fi

echo "==> MPFB2 (MakeHuman body generator — CC0 base mesh + morph targets)"
# MPFB2 supplies the parametric skin envelopes (03b_build_shells.py). We clone the
# source and package the addon as a Blender extension zip that 03b installs headless.
MPFB_REMOTE="https://github.com/makehumancommunity/mpfb2"
MPFB_DIR="sources/mpfb/src-repo"
MPFB_ZIP="sources/mpfb/mpfb_ext.zip"
if [ ! -f "$MPFB_ZIP" ]; then
  mkdir -p sources/mpfb
  rm -rf "$MPFB_DIR"
  if git clone --depth 1 "$MPFB_REMOTE" "$MPFB_DIR" && [ -d "$MPFB_DIR/src/mpfb" ]; then
    ( cd "$MPFB_DIR/src" && zip -r -q -X "../../mpfb_ext.zip" mpfb -x "*.pyc" -x "*__pycache__*" )
    echo "  built $MPFB_ZIP"
  else
    echo "  (MPFB2 clone/package failed — 03b_build_shells will fall back or skip)"
  fi
fi

echo "==> fetch complete"
