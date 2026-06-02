# Acko Clinic — Post-Screening 3D Body Consultation: Spec & Build Guide

> **Purpose of this document.** A self-contained spec for continuing this project in a fresh
> session. It captures what we're building, what we tried, what worked, what didn't and *why*,
> and — most importantly — the **right architecture for showing patients of different shapes and
> sizes with organs that stay correctly aligned**, which is the one problem still open.
>
> Read "The body-type problem" and "Recommended architecture" first; the rest is context.

---

## 1. What we're building

A **doctor-led, in-clinic kiosk**. A patient finishes a health screening; the doctor uses this
app to show them a 3D human body where **body systems are colored by the patient's screening
results** (green = in range, amber = watch, red = needs attention). The doctor walks them through
each system. It's a **communication and reassurance tool**, not a diagnostic instrument.

### Product principles (these drive every trade-off)
1. **Clarity over completeness.** The message is "your heart needs attention, your liver is fine."
   Hyper-detailed anatomy (every bone, every nerve) is intimidating and buries the message.
   Curate a clean, recognizable set per system.
2. **Coherence and trust.** Calm, premium, legible. The patient may be anxious post-screening.
3. **Relatability.** The body should read as *a person like them* — which is why **body type
   (size, build, sex, roughly age) matters**. This is the open problem (§4–5).
4. **Open-source, license-clean anatomy only** (see §8).

### Non-goals
- Medical-grade anatomical accuracy or measurement.
- Surgical/diagnostic detail.
- Interactive free exploration (it's doctor-driven, system-by-system).

---

## 2. Current state (what's built and working — keep this)

Stack: **React 18 + TypeScript + Vite**, **three.js + @react-three/fiber + @react-three/drei**,
**@react-three/postprocessing**, **zustand**. App lives in `clinic-body-3d/`.

**Working and good — do not rebuild:**
- **Scoring engine** (`src/scoring/`): markers → per-system status + 0..1 severity score, driven
  by `config/body-systems.schema.json`. Solid, tested (`src/scoring/engine.test.ts`, 11 tests).
- **7 body systems**: cardiovascular, digestive, endocrine, respiratory, urinary, nervous,
  skeletal. (Muscular was removed earlier by request.)
- **Doctor-led navigation**: overview ↔ per-system focus, prev/next, per-system camera framing
  (`src/systems/registry.ts`), zustand store (`src/store.ts`).
- **Left/right UI**: 3D on the left, data panel on the right (no overlay). `src/App.tsx`,
  `src/ui/DetailPanel.tsx`, `src/styles/app.css`. (`Annotation.tsx` in-scene labels were removed.)
- **The frosted-glass X-ray aesthetic** — this is a genuine product asset, keep it:
  - `src/scene/BodyShell.tsx`: `MeshPhysicalMaterial`, `transmission:1`, `depthWrite:false`,
    opacity ramps to ~0.18. Frosted translucent skin.
  - `src/scene/SystemMesh.tsx`: organ material is a **lit tinted base color + emissive glow**
    (`color = statusColor*0.42`, plus `emissive`) with **`depthWrite:false`** so interior organs
    read *through* the skin and each other (the X-ray look). One shared material applied to all
    meshes via `traverse` — mesh names don't matter for rendering.
  - `src/scene/colors.ts`: status → THREE.Color (from CSS tokens) + emissive intensity by status.
- **Mock data**: `src/data/mock/members.ts` — 3 patients (Asha 34F all-healthy; Vikram 47M
  metabolic flags; Meera 52F mixed). Default member is Vikram.

**Asset pipeline** (`asset-pipeline/`, run via `npm run assets:build`):
- `01_fetch.sh` — clones sources into `sources/` (gitignored): BodyParts3D, Z-Anatomy, MPFB2.
- `02_audit_licenses.py` — verifies every source is CC BY-SA *or* CC0; writes `LICENSE-AUDIT.md`,
  `ATTRIBUTION.md`, `flagged_sources.json`; **hard-stops if a geometry source is non-compliant**.
- `03_build_glb.py` — BodyParts3D STLs → per-system `system_<id>.glb` + `body_shell.glb`.
- `03b_build_shells.py` — MakeHuman/MPFB2 body-type skin shells (see §3, this is the part to replace).
- `04_validate.py` — checks GLBs exist, mesh names, triangle budget.
- Output: `public/models/*.glb` (loaded by `useGLTF`).

---

## 3. What we tried, and the verdict on each

### A. BodyParts3D organs (works, shipping)
- Per-structure STL geometry (`FMA<id>.stl`), CC BY-SA 2.1 Japan, mapped to systems via
  `asset-pipeline/fma-to-system.json`, joined per system, decimated, exported as `system_<id>.glb`.
- **Worked.** Real organ geometry, scoring drives color correctly.
- Limitations: it's a **curated subset** — skeletal is ~13 representative bones (no ribs/limbs),
  nervous is brain-only (no nerves). Cardiovascular was extended (pulmonary artery, IVC,
  aortic-arch branches) and looks good.

### B. MakeHuman / MPFB2 body-type skin shells (works mechanically, **wrong architecture**)
- Goal: vary the **skin envelope** per patient (fat/thin/sex/age) while keeping fixed organs.
- Built `03b_build_shells.py`: generates `shell_neutral / female-young / male-heavy / female-older`
  via MPFB2, wired `bodyType` onto members, `BodyShell` loads per-member shell.
- **What worked:** MPFB2 runs headless on Blender 5.1.2; parametric bodies generate and export fine.
- **What did NOT work — and this is the central lesson:** MakeHuman is a **different body** from
  the BodyParts3D organs. Compositing a foreign skin over fixed organs caused a cascade of
  alignment problems, each of which we diagnosed and patched but never *solved*:
  - Front/back **facing flip** (export_yup axis math; see §7).
  - Organs **poking out** because we centered the shell on its full-body bbox, not its torso.
  - **Depth-size deficit**: at 1.8 m the MakeHuman torso is ~0.27 deep vs the organs' source body
    ~0.30, so organs poked the chest/back; we "fixed" it with a depth-inflation hack (1.32×).
  - Thin bodies were **shallower than the organs themselves** → organs inside the ribcage (unphysical).
- **Verdict:** swapping in skins from a *different* body can't be made correct. The technique
  (MPFB2 parametric shapes) is valuable; applying it as a *replacement mesh over foreign organs*
  is the mistake. (See §5 for how to use it correctly.)

### C. Z-Anatomy as a richer single source (spike done, promising)
- Z-Anatomy = a CC BY-SA 4.0 re-working of BodyParts3D: one coherent body, skin + skeleton +
  organs + vessels + nerves, **system-organized**, TA2-named, in one `Startup.blend` (306 MB,
  inside `Z-Anatomy.zip`, committed in the `sources/z-anatomy` repo as an 86.7 MB git blob).
- Spike extracted **full skeleton (1,244 bones)** and **full nervous system (incl. peripheral
  nerves, 674 objects, 2.4M raw tris)** headless — vastly richer than our subset.
- **What worked:** geometry is rich, clean, extractable; one consistent body.
- **What didn't:** dropping Z-Anatomy's skeleton *next to* the BodyParts3D organs + MakeHuman
  shell = **three different bodies = misaligned** (skeleton beside the body, arms in anatomical
  spread vs shell's arms down). Also stray atlas label/text objects leak in; nerves are CURVE
  objects (must convert); most collections are disabled in the view layer (must enable).
- **Verdict:** Z-Anatomy is the best **single coherent source**. But it does **not by itself solve
  body types** — it's one fixed (male) body.

### The meta-lesson
Every hard bug came from **assembling one human out of multiple unrelated bodies**. The fix is a
**single coherent body**; body-type variation must then come from **deforming that one body**, not
from swapping in parts of other bodies.

---

## 4. The body-type problem (the thing still unsolved)

**Requirement:** patients of different **size (BMI), build, sex, and roughly age** should see a
body that looks like them, with **organs that stay correctly inside and aligned**.

**Why it's hard:** organs are authored for one body shape. A different shape needs the organs to
fit its cavity. Naively swapping skins (what we did) breaks alignment because the skins come from a
*different* body whose torso may even be shallower than our organs.

**The key physical insight that makes it tractable:**
> Two people of different weight have **the same organs and skeleton**; the difference is mostly
> **soft tissue (fat) added *outside* the core**. The skin envelope varies **outward** from a
> fixed anatomical core — it never goes *inside* it.

So body type is a property of the **soft-tissue skin layer**, applied as an **outward-only**
deformation over an invariant **core (skeleton + organs)**. This guarantees organs never poke out
(skin ≥ core, always) and still produces visibly different bodies. Sex and age are likewise mostly
surface/soft-tissue morphs (breasts, hips, shoulder width, skin slackness), with optional skeletal
tweaks later.

---

## 5. Recommended architecture (converge on this)

### 5.1 One coherent body, two layers
- **Source:** a single coherent body where skin and all organs are mutually registered. Use
  **Z-Anatomy** (richest, system-organized, CC BY-SA) — or BodyParts3D if simpler — but **one body**.
- **Core layer (invariant):** skeleton + organs, curated per system for legibility (§1.1),
  normalized **once** to scene space. Because everything is from one body, it aligns by construction
  — none of the per-system fitting/centering/inflation hacks are needed.
- **Skin layer (parametric):** a single-topology skin envelope that wraps the core, with
  **body-type morph targets (blendshapes)** that only displace the surface **outward**:
  - `weight` (BMI): inflate abdomen, flanks, limbs, face.
  - `sex`: chest (breasts), hip width, shoulder width, fat distribution.
  - `age`: mild slackening/proportion shifts (optional for v1).
  The patient's profile maps to blend weights. **Thinnest = skin hugging the core** (so it can never
  go inside it); **heavier = inflated from there**.

This keeps the X-ray aesthetic (frosted skin + glowing organs) and makes organs-stay-aligned a
*property of the construction*, not a fight.

### 5.2 Where the morph shapes come from (ranked)
1. **Hand-sculpted blendshapes (recommended v1).** Sculpt 3–5 targets (lean / average / heavy,
   plus a female target) on the base skin in Blender. Full control, guaranteed outward, fast to ship.
2. **MakeHuman/MPFB2 shape *transfer* (recommended v2, data-driven).** Use MPFB2 to generate
   body-type *shapes*, then **wrap/transfer that shape onto our base skin** (Blender Surface Deform
   / shrinkwrap + corrective), so the *topology and organ-fit stay ours* but the *shape* comes from
   MakeHuman's parametric space. This reuses MPFB2's knowledge **without** adopting its mis-fitting
   mesh — the correct way to use the work from attempt (B). Clamp so the result never intrudes past
   the core (shrinkwrap-to-core as the floor).
3. **Non-rigid organ fitting (overkill).** Warp organs per body via landmark/cage deformation.
   Most faithful, most complex; not needed for a kiosk.

### 5.3 What to keep / replace / defer
- **Keep:** scoring engine, system navigation + framings, left/right UI, frosted X-ray materials,
  status colors, mock-data shape, the whole `src/` app layer.
- **Replace:** the asset pipeline's geometry source. Add `03c_extract_zanatomy.py` (single body →
  curated skin + 7 system GLBs, aligned once, license-scrubbed). Retire `03_build_glb.py`
  (BodyParts3D) and `03b_build_shells.py` (foreign-skin shells) once the new path is proven.
- **Re-do correctly:** body type as **skin blendshapes on the one body** (§5.1–5.2), replacing the
  `shell_<bodytype>.glb` swap. Runtime: instead of loading a different shell GLB per member, load
  **one skin with morph targets** and set blend weights from `member.bodyType` (or derive from
  sex/age/BMI). drei/three support morph target influences on a `SkinnedMesh`/`Mesh`.
- **Delete (dead once converged):** torso-depth-centering, `DEPTH_INFLATE`, the per-shell alignment
  code — all artifacts of fighting multi-body composition.

### 5.4 Proposed phases
- **Phase 1 — single coherent body.** `03c` extracts from Z-Anatomy: a clean **skin envelope** +
  **curated** cardiovascular + skeletal (proof systems), aligned, one normalize. Confirm whole-body
  coherence in one screenshot. Then fill in the other 5 systems. Drop BodyParts3D path.
- **Phase 2 — body-type morphs (the actual goal).** Add 3–5 outward skin blendshapes (hand-sculpt
  first). Wire `member.bodyType` → morph weights. Verify organs stay inside across the full weight
  range, **in profile** (this is where it breaks — always check the side view, see §7).
- **Phase 3 — data-driven + sex/age.** MPFB2 shape-transfer for richer/parametric body types;
  female morph; mild age. Optionally a sex-specific pelvis tweak.
- **Phase 4 — polish.** Curation pass for legibility, triangle budget, framings per system,
  attribution/credits, NC-scrub verification.

### 5.5 How to verify body-type fit (don't repeat our mistake)
- **Always check the PROFILE (side) view**, not just the front — depth poke-through is invisible
  head-on. The flaky in-browser orbit isn't reliable; **render front+side offline in Blender** from
  the actual GLBs (we have a working script: see `render_fit` pattern in §7 / git history).
- Programmatic check: per vertical slice, organ bounds must be within skin bounds, front and back.
- With the outward-only skin layer this should pass by construction; the check is a guardrail.

---

## 6. Asset inventory & where things are

- App: `clinic-body-3d/` (Vite). `npm run dev`, `npm run typecheck`, `npm test`, `npm run assets:build`.
- Pipeline: `clinic-body-3d/asset-pipeline/` (`01_fetch.sh`, `02_audit_licenses.py`,
  `03_build_glb.py`, `03b_build_shells.py`, `04_validate.py`, `fma-to-system.json`).
  Prototype kept: `asset-pipeline/zanatomy-extract.prototype.py` (Z-Anatomy extraction spike).
- Sources (gitignored, fetched by `01`): `asset-pipeline/sources/{bodyparts3d,z-anatomy,mpfb}`.
- Models served to the app: `clinic-body-3d/public/models/*.glb`.
- Config: `clinic-body-3d/config/body-systems.schema.json` (systems, markers, ranges, scoring).
- Key source: `src/store.ts`, `src/systems/registry.ts`, `src/scene/{Scene,BodyShell,SystemMesh,
  CameraRig,Lighting,PostFX,colors}.tsx`, `src/scoring/*`, `src/ui/*`, `src/data/*`.

---

## 7. Hard-won technical facts (so the next session doesn't re-discover them)

**Blender (this machine has 5.1.2):**
- EEVEE engine enum is `'BLENDER_EEVEE'` (NOT `BLENDER_EEVEE_NEXT`). STL import = `bpy.ops.wm.stl_import`.
- **`export_yup` (glTF default) axis mapping** — critical for facing: Blender Z-up → glTF Y-up via
  −90° about X. **Blender +Y → glTF −Z; Blender −Y → glTF +Z; X preserved; Blender +Z → glTF +Y.**
- **Scene facing:** camera sits at +Z looking toward −Z, so a model's **anterior must end up at
  glTF +Z** to face the camera. Our organs' anterior is +Z (correct). MakeHuman's native anterior is
  Blender −Y, which maps to glTF +Z with **no rotation** — adding a 180° spin flips it backwards
  (this caused the facing bug). Verify facing whenever a new source is introduced.

**MPFB2 (MakeHuman in Blender):**
- Only loads on Blender 5.1.2 when **installed as an extension** (`bl_ext.user_default.mpfb`), via
  `bpy.ops.extensions.package_install_files`. Loading by `sys.path` fails (`extension_path_user`).
- Bundles CC0 base mesh + 1,258 morph targets (offline, no GUI download).
- `HumanService.create_human(macro_detail_dict=...)`; default dict keys: `gender, age, muscle,
  weight, proportions, height, cupsize, firmness, race{asian,caucasian,african}` (all 0..1).
- Morphs are applied as **shape keys**, which block `modifier_apply`. **Bake** via the depsgraph
  evaluated mesh (`new_from_object(eval_obj)`) to flatten shape keys + modifiers (and to apply the
  "Hide helpers" MASK that strips the clothes-fitting cage).

**Z-Anatomy:**
- `Startup.blend` (306 MB) inside `Z-Anatomy.zip`; the zip is a normal git blob in `sources/z-anatomy`.
  Extract: `git cat-file -p HEAD:Z-Anatomy.zip > /tmp/Z.zip` then unzip.
- 4,569 meshes. Top collections: `1: Skeletal system` (1244), `2: Muscular insertions`,
  `3: Joints`, `4: Muscular system` (789), `5: Cardiovascular system` (60),
  `6: Lymphoid organs`, `7: Nervous system & Sense organs` (460 mesh + 249 **curve** nerves +
  133 **font** labels), `8: Visceral systems` (254 — digestive/respiratory/urinary/endocrine here),
  `9: Regions of human body` (299 — body surface/regions). Also a `Bonus collection` (extras).
- Gotchas: most collections **disabled in the view layer** → enable recursively
  (`layer_collection.exclude=False, hide_viewport=False`) before `bpy.ops` selection works.
  **Nerves/vessels are CURVE objects** → `convert(target='MESH')` to get tube geometry.
  **Labels are FONT** (+ some stray text) → exclude. Names use TA2 with `.l/.r/.j` suffixes.
  Body is ~1.79 m tall, Z-up, feet ≈ 0, **X-center offset ≈ −0.33** (center on bbox when normalizing).

**Rendering / app:**
- X-ray look needs `depthWrite:false` on translucent materials (both skin and organs).
- Organ legibility: don't use a near-black base + pure emissive (flat blob); use a **lit tinted
  base color + moderate emissive** so lighting reveals contours.
- Triangle budget: `SYSTEM_TRI_BUDGET = 150_000` total across systems (enforced by `04`), shell ~45k.
  Decimation is global in `03`; the validator fails over budget.
- The in-browser preview viewport is **flaky on reload** (resets size; occasional black/anti-scaled
  screenshots). For reliable visual checks, **render the GLBs offline in Blender** (front + side).

---

## 8. Licensing (strict — this is a clinic product)

- Acceptable: **CC BY-SA** (organs/naming) and **CC0** (e.g., MakeHuman assets). Share-alike applies
  to CC BY-SA-derived GLBs. `02_audit_licenses.py` detects CC0 *before* CC BY-SA (CC0 text also says
  "Creative Commons"), records all three sources, and hard-stops if a geometry source is non-compliant.
- **BodyParts3D**: CC BY-SA 2.1 Japan. **Z-Anatomy**: CC BY-SA 4.0 overall. **MakeHuman/MPFB2**: CC0.
- ⚠️ **Z-Anatomy bundles a few NON-COMMERCIAL parts** (per its README): **inner ear** (Dundee,
  CC BY-NC-SA 4.0) and a **kidney** (Lissie Cowley, CC BY-NC). These **must be excluded** for a
  commercial kiosk. Filter them out in `03c` (by name/collection); use BodyParts3D/Z-Anatomy
  CC-BY-SA kidneys instead. Cranial nerves (Dundee, CC BY 4.0) are fine.

---

## 9. Open decisions for the next session
1. **Source for the single body:** Z-Anatomy (rich, but extraction work + NC scrub) vs BodyParts3D
   (simpler, sparser). Recommendation: Z-Anatomy, curated.
2. **Default body & sex coverage:** Z-Anatomy is male. Female = a morph target (v2/3) or a second
   source body. Decide how much sexual dimorphism v1 needs.
3. **Body-type input:** explicit `member.bodyType`, or derive blend weights from `sex/age/BMI`
   markers (we already have BMI-ish data). Recommendation: derive, with explicit override.
4. **Curation depth per system:** how much anatomy per system maximizes clarity (not completeness).

---

## 10. TL;DR for the next session
- The app layer (scoring, navigation, UI, X-ray aesthetic) is good — **keep it**.
- Stop compositing multiple bodies. **One coherent source body** (Z-Anatomy, curated).
- **Body type = outward-only soft-tissue skin morphs over a fixed organ/skeleton core**, weighted
  by patient profile. This is what makes "different shapes and sizes" work *with aligned organs* —
  it's the fix for everything attempt (B) got wrong.
- Build it in phases (§5.4). Always verify fit in **profile**, via **offline Blender renders**.
- Mind the **NC parts** in Z-Anatomy and the **export_yup facing** math.
