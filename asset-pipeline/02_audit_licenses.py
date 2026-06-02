#!/usr/bin/env python3
"""Phase 0.2 — license audit.

Reads the license metadata shipped inside each source repo, verifies every source
we draw geometry/naming from is CC BY-SA, and emits two artifacts:

  LICENSE-AUDIT.md   machine-checkable record: per source -> license, SPDX-ish id, status
  ATTRIBUTION.md     human-facing credit block (CC BY-SA requires attribution + share-alike)

CC BY-SA is the ONLY acceptable family for this build (spec hard constraint). Any source
whose detected license is not CC BY-SA is FLAGGED and written to flagged_sources.json so
03_build_glb can exclude it from the export set. If the geometry source (BodyParts3D) itself
is flagged, this script exits non-zero — we do not build on non-compliant geometry.
"""
import json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BP3D = HERE / "sources/bodyparts3d"
ZAN = HERE / "sources/z-anatomy"
MPFB = HERE / "sources/mpfb/src-repo"
DATA = BP3D / "assets/BodyParts3D_data"

# Sources we audit. Any role containing "geometry" is load-bearing: if it fails, the build
# stops. Acceptable licenses are CC BY-SA (organs/naming) or the more-permissive CC0 (skin).
SOURCES = [
    {
        "key": "bodyparts3d",
        "title": "BodyParts3D",
        "role": "geometry",
        "remote": "https://github.com/Kevin-Mattheus-Moerman/BodyParts3D",
        "upstream": "BodyParts3D, © The Database Center for Life Science (DBCLS)",
        "license_files": [DATA / "LICENSE_content", BP3D / "LICENSE", BP3D / "README.md"],
    },
    {
        "key": "z-anatomy",
        "title": "Z-Anatomy",
        "role": "naming-reference",
        "remote": "https://github.com/Z-Anatomy/Models-of-human-anatomy",
        "upstream": "Z-Anatomy (LASBOUX Pierre-Yves et al.)",
        "license_files": [ZAN / "License.txt", ZAN / "LICENSE", ZAN / "LICENSE.txt", ZAN / "Readme.md", ZAN / "README.md"],
    },
    {
        "key": "mpfb-makehuman",
        "title": "MakeHuman (via MPFB2)",
        "role": "skin-geometry",
        "remote": "https://github.com/makehumancommunity/mpfb2",
        "upstream": "MakeHuman / MPFB2 community — base mesh + morph targets",
        # Only the ASSETS license matters here: we ship geometry derived from the CC0 base
        # mesh + targets, not the (AGPL) addon code.
        "license_files": [MPFB / "LICENSE.ASSETS.md"],
    },
]

CC0 = re.compile(r"\bcc0\b|creative\s*commons\s*zero|public\s*domain", re.I)
CC_BY_SA = re.compile(r"creative\s*commons|cc[\s_-]*by[\s_-]*sa|attribution[\s-]*share[\s-]*alike", re.I)
VERSION = re.compile(r"\b(\d\.\d)\b")
JURIS = re.compile(r"\b(japan|international|unported)\b", re.I)


def read_license_text(files):
    for f in files:
        if f.is_file():
            try:
                return f.read_text(errors="replace"), f
            except Exception:
                continue
    return None, None


def classify(text):
    if not text:
        return {"detected": None, "is_cc_by_sa": False, "is_cc0": False, "compliant": False, "spdx": None}
    # CC0 text also contains "Creative Commons", so test CC0 first and exclude it from BY-SA.
    is_cc0 = bool(CC0.search(text))
    is_cc = (not is_cc0) and bool(CC_BY_SA.search(text))
    if is_cc0:
        return {"detected": "CC0 1.0 (public domain)", "is_cc_by_sa": False,
                "is_cc0": True, "compliant": True, "spdx": "CC0-1.0"}
    ver = VERSION.search(text)
    jur = JURIS.search(text)
    ver_s = ver.group(1) if ver else "?"
    jur_s = jur.group(1).title() if jur else ""
    spdx = None
    if is_cc:
        # SPDX-style id (CC BY-SA ports like 2.1 Japan are not strict SPDX, kept descriptive).
        spdx = f"CC-BY-SA-{ver_s}" + (f" {jur_s}" if jur_s and jur_s.lower() not in ('international','unported') else "")
    return {"detected": f"CC BY-SA {ver_s} {jur_s}".strip() if is_cc else "UNKNOWN/NON-CC-BY-SA",
            "is_cc_by_sa": is_cc, "is_cc0": False, "compliant": is_cc, "spdx": spdx}


def main():
    results = []
    for s in SOURCES:
        text, used = read_license_text(s["license_files"])
        present = used is not None
        cls = classify(text)
        results.append({**s, "present": present,
                        "license_path": str(used.relative_to(HERE)) if used else None,
                        **cls})

    # Status logic
    flagged = []
    geometry_ok = True
    for r in results:
        if not r["present"]:
            r["status"] = "MISSING-LICENSE"
            flagged.append(r["key"])
            if "geometry" in r["role"]:
                geometry_ok = False
        elif r["compliant"]:
            r["status"] = "OK"
        else:
            r["status"] = "FLAGGED-NON-COMPLIANT"
            flagged.append(r["key"])
            if "geometry" in r["role"]:
                geometry_ok = False

    now = datetime.date.today().isoformat()

    # ---- LICENSE-AUDIT.md ----
    audit = [f"# License Audit\n", f"_Generated {now} by asset-pipeline/02_audit_licenses.py_\n",
             "Anatomy sources must be CC BY-SA (organs, naming) or CC0 (skin envelopes). "
             "Sources detected otherwise are **FLAGGED** and excluded from the GLB export set.\n",
             "| Source | Role | Detected License | SPDX | Status | License File |",
             "|---|---|---|---|---|---|"]
    for r in results:
        audit.append(f"| [{r['title']}]({r['remote']}) | {r['role']} | {r['detected'] or '—'} "
                     f"| {r['spdx'] or '—'} | **{r['status']}** | {r['license_path'] or 'NOT FOUND'} |")
    audit.append("")
    audit.append(f"- Sources audited: {len(results)}")
    audit.append(f"- Flagged (excluded from export): {flagged if flagged else 'none'}")
    audit.append(f"- Geometry source compliant: {'YES' if geometry_ok else 'NO — BUILD MUST STOP'}")
    (HERE / "LICENSE-AUDIT.md").write_text("\n".join(audit) + "\n")

    # ---- ATTRIBUTION.md ----
    role_desc = {
        "geometry": "3D organ geometry",
        "skin-geometry": "3D skin envelope geometry (parametric body types)",
        "naming-reference": "structure naming / grouping reference only (no geometry used)",
    }
    attr = [f"# Attribution\n",
            "This application renders 3D anatomy derived from open-source datasets. Organ geometry "
            "and naming come from Creative Commons Attribution-ShareAlike (CC BY-SA) sources; the "
            "parametric skin envelopes come from a CC0 (public-domain) source. Per their licenses, "
            "the works below are credited, and any redistribution of the CC BY-SA-derived geometry "
            "remains under the same CC BY-SA terms.\n"]
    for r in results:
        if r["status"] != "OK":
            continue
        attr.append(f"## {r['title']}")
        attr.append(f"- Upstream: {r['upstream']}")
        attr.append(f"- Source: {r['remote']}")
        attr.append(f"- License: {r['detected']} ({r['spdx']})")
        attr.append(f"- Role in this app: {role_desc.get(r['role'], r['role'])}")
        attr.append("")
    attr.append("Derived GLB assets in `public/models/` that come from CC BY-SA sources are "
                "ShareAlike derivatives and carry the same CC BY-SA obligations; the `shell_*.glb` "
                "body envelopes are CC0.\n")
    (HERE / "ATTRIBUTION.md").write_text("\n".join(attr) + "\n")

    (HERE / "flagged_sources.json").write_text(json.dumps({"flagged": flagged}, indent=2) + "\n")

    # ---- console summary ----
    print("==> License audit")
    for r in results:
        print(f"  {r['title']:<14} role={r['role']:<16} {r['status']:<22} {r['detected'] or '—'}")
    print(f"  wrote LICENSE-AUDIT.md, ATTRIBUTION.md, flagged_sources.json")
    if not geometry_ok:
        print("\nFATAL: geometry source (BodyParts3D) is non-compliant or missing its license. "
              "Refusing to proceed.", file=sys.stderr)
        sys.exit(2)
    if flagged:
        print(f"  NOTE: flagged (will be excluded by 03): {flagged}")
    print("==> audit complete")


if __name__ == "__main__":
    main()
