#!/usr/bin/env python3
"""Phase 0.4 — validate exported GLBs.

Headless-parses every GLB in ../public/models/ (no Blender needed — reads the glTF JSON
chunk; Draco-compressed primitives still declare their accessor `count`, so triangle counts
are exact). Asserts:

  * one GLB per system listed in config/body-systems.schema.json
  * each system_<id>.glb contains a mesh/node named exactly `system_<id>` (the name the
    runtime loads by)
  * body_shell.glb is present
  * combined system triangle count is within SYSTEM_TRI_BUDGET

Prints per-system + total triangle counts and exits non-zero on any failure.
"""
import json, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = (HERE / "../public/models").resolve()
SCHEMA = (HERE / "../config/body-systems.schema.json").resolve()
SYSTEM_TRI_BUDGET = 150_000

GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def read_gltf_json(path: Path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise ValueError(f"{path.name}: not a GLB (bad magic)")
    off = 12
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == JSON_CHUNK:
            return json.loads(chunk.decode("utf-8"))
    raise ValueError(f"{path.name}: no JSON chunk")


def triangles(gltf):
    accessors = gltf.get("accessors", [])
    total = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            mode = prim.get("mode", 4)  # 4 = TRIANGLES
            if "indices" in prim:
                count = accessors[prim["indices"]]["count"]
            else:
                count = accessors[prim["attributes"]["POSITION"]]["count"]
            if mode == 4:
                total += count // 3
            elif mode in (5, 6):  # strip/fan
                total += max(0, count - 2)
    return total


def names(gltf):
    out = set()
    for mesh in gltf.get("meshes", []):
        if mesh.get("name"):
            out.add(mesh["name"])
    for node in gltf.get("nodes", []):
        if node.get("name"):
            out.add(node["name"])
    return out


def main():
    schema = json.loads(SCHEMA.read_text())
    system_ids = [s["id"] for s in schema["systems"]]

    failures = []
    print("==> validating GLBs in", OUT)
    if not OUT.is_dir():
        print(f"FATAL: output dir missing: {OUT}", file=sys.stderr)
        sys.exit(2)

    per_system = {}
    for sid in system_ids:
        f = OUT / f"system_{sid}.glb"
        if not f.is_file():
            failures.append(f"missing GLB: {f.name}")
            continue
        gltf = read_gltf_json(f)
        nm = names(gltf)
        expected = f"system_{sid}"
        tris = triangles(gltf)
        per_system[sid] = tris
        ok_name = expected in nm
        if not ok_name:
            failures.append(f"{f.name}: expected mesh/node named '{expected}', found {sorted(nm)}")
        print(f"  {f.name:<34} tris={tris:>8,}   name '{expected}': {'OK' if ok_name else 'MISSING'}")

    # shell
    shell = OUT / "body_shell.glb"
    shell_tris = 0
    if not shell.is_file():
        failures.append("missing GLB: body_shell.glb")
    else:
        gltf = read_gltf_json(shell)
        shell_tris = triangles(gltf)
        print(f"  {'body_shell.glb':<34} tris={shell_tris:>8,}   (skin shell)")

    total = sum(per_system.values())
    print(f"  {'-'*34}")
    print(f"  {'SYSTEM TOTAL':<34} tris={total:>8,}   budget={SYSTEM_TRI_BUDGET:,}")
    print(f"  {'GRAND TOTAL (incl. shell)':<34} tris={total + shell_tris:>8,}")

    if total > SYSTEM_TRI_BUDGET:
        failures.append(f"system triangle total {total:,} exceeds budget {SYSTEM_TRI_BUDGET:,}")

    if failures:
        print("\n==> VALIDATION FAILED:")
        for fl in failures:
            print(f"   - {fl}")
        sys.exit(1)
    print("==> validation passed")


if __name__ == "__main__":
    main()
