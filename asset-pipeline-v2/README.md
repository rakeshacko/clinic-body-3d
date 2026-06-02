# asset-pipeline-v2 — coherent-body rebuild + body-type morph

This folder is the **converged architecture** from `docs/SPEC.md` §5, built fresh and
**kept separate** from the live `asset-pipeline/` + `public/models/` so the current app
keeps working untouched while this is proven. Nothing here is wired into the running app yet.

## The idea (two layers, one body)

- **Core (invariant):** skeleton + 7 organ systems, extracted from the *single* Z-Anatomy
  body and normalized **once**. Because every part comes from one body and gets the **same**
  transform, organs-stay-inside-skin is true **by construction** — none of the per-system
  centering / `DEPTH_INFLATE` hacks the old multi-body path needed.
- **Skin (parametric):** the Z-Anatomy body-surface, with body type applied as a
  **procedural outward-only morph** (see below).

## What's here

| path | what |
|---|---|
| `zanatomy-to-system.json` | TA2-name → system map; visceral-collection split; NC/genitalia/artifact excludes |
| `scripts/extract_core.py` | Z-Anatomy `Startup.blend` → `out/{body_shell,system_*}.glb`, one normalize |
| `scripts/render_check.py` | offline front+side coherence render (the poke-through test) |
| `scripts/spike_skin_morph.py` | procedural outward body-type morph, profile sweep |
| `out/*.glb` + `manifest.json` | extracted core (skin + 7 systems) |
| `renders/*.png` | `front`/`side` coherence; `morph_{lean,mid,heavy}_side`, `morph_heavy_front` |

Run: `blender -b -P scripts/extract_core.py` then `... render_check.py` / `... spike_skin_morph.py`
(Blender 5.1.2; needs `Startup.blend` unzipped to `/tmp/zanat/` from `sources/z-anatomy/Z-Anatomy.zip`).

## Results

1. **Coherence (`front.png`/`side.png`).** Skin + full skeleton + all 7 systems read as one
   person; in **profile** the spine, ribcage and organs sit cleanly inside the skin — no
   poke-through. This is the thing every prior multi-body attempt failed; here it's free.
   We had never rendered the whole Z-Anatomy body through our pipeline before — now we have.

2. **Body-type morph (`morph_*`).** A procedural radial outward displacement (belly-centred
   vertical profile + forward belly bias + limb damping) produces believable lean→heavy
   variation **in profile**, with organs guaranteed inside at every weight.

## Decision

**Body type = procedural outward-only morph on the one coherent Z-Anatomy skin.**
This supersedes SPEC §5.2's MakeHuman-shape-transfer as the *primary* path because it is:
single-source (no two-body registration), outward-only **by construction** (organs can't
escape), and **topology-free** (works on the 248-patch skin — no single-mesh blendshape
requirement). MakeHuman/MPFB2 is demoted to an *optional v2 realism boost* (data-driven fat
distribution) — `asset-pipeline/03b_build_shells.py` keeps that knowledge if ever wanted.
The `DEPTH_INFLATE` / `torso_depth_center` hacks are **not used** and not needed here.

## Mapping notes

- **Visceral collection (8)** holds 4 systems mixed; split by name, first-match priority
  `endocrine → urinary → respiratory → digestive` (so "supra**renal**" → endocrine, not urinary).
- **Excluded:** `.j/.i/.g` landmark/label anchors (0-tri); **genitalia** (no reproductive
  system; clinic kiosk); **NC parts** — inner ear (Dundee CC-BY-NC-SA); `ciliary body-curve`
  (broken construction curve) + a generous outlier-vertex clip as backstop.
- ⚠️ **Kidney license flag.** Z-Anatomy kidney provenance is ambiguous (Lissie Cowley
  CC-BY-NC vs BodyParts3D CC-BY-SA). Included for the spike, flagged in `manifest.json`;
  **verify / swap to a CC-BY-SA kidney before commercial use.**

## Open / next (not done — pending go-ahead)

- **Triangle budget:** systems total ≈337k now (spike-level); the app budget is 150k —
  needs a **curation pass** (clarity over completeness, esp. cardiovascular's 654 vessel
  curves and the dense brain).
- **Bake the morph as shape keys** on `body_shell.glb` (a `weight` morph target) so the
  runtime can drive it via drei `morphTargetInfluences` from `member` profile — then a
  small in-app demo.
- **Refine the morph:** reduce arm-separation from pure radial push (torso mask); add a
  `sex` morph (chest/hips/shoulders) and mild `age`.
- **Wire into the app** (only when approved): point `shellForMember` at the single skin +
  morph weights; replace `public/models/*`; retune per-system framings; retire the
  BodyParts3D `03_build_glb.py` and foreign-shell `03b_build_shells.py` paths.
