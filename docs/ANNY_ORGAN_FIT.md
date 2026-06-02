# Anny Shell and Organ Fit

## Goal

Fit the existing internal organ/system GLBs inside an Anny-derived outer body shell while
preserving the doctor review experience. The fit is intended to keep anatomy visually coherent
across body presets, not to reconstruct patient-specific internal anatomy.

## Runtime Path

The app has a **Body fit** tuning panel with:

- body presets
- Anny shell enable/disable
- body-shape controls
- organ response controls

When enabled, the shell is fetched from the local Anny server:

```txt
VITE_ANNY_URL=http://localhost:8765
```

The shell component requests:

```txt
/faces
/mesh?<body params and local controls>
```

Anny vertices are converted into the app's body space:

```txt
appX = annyX
appY = annyZ
appZ = -annyY
```

The converted mesh is centered around the origin so it shares the same approximate coordinate
space as the existing GLB organ systems. If the Anny server is unavailable, the app falls back
to the existing static body shell GLB.

## Body Parameters

The current runtime controls are:

- `gender`
- `age`
- `height`
- `weight`
- `muscle`
- `proportions`
- `torsoWidth`
- `torsoDepth`
- `abdomen`
- `hips`
- `centrality`

These map to Anny global controls and a bounded set of Anny local controls such as waist,
torso width/depth, hips, abdomen, and limb girth.

Implementation:

```txt
src/bodyFit.ts
src/scene/BodyShell.tsx
src/ui/BodyFitPanel.tsx
```

## Organ Fit Rule

Organ fitting distinguishes placement from organ-size implication.

Primary drivers:

- height
- torso length
- ribcage width/depth
- pelvis/hip region
- abdomen forward placement

Secondary or avoided drivers:

- adiposity should mostly affect the shell and abdomen envelope
- muscle should mostly affect the shell
- neither adiposity nor muscle should uniformly enlarge organs

This means a high-adiposity person and a muscular person at the same height may have very
different outer shells, but their internal systems should remain similar in size unless the
torso/ribcage/pelvis fit requires mild visual adjustment.

## System-Specific Behavior

Cardiovascular:

- follows chest/ribcage width and depth
- mild height response for placement and scale

Respiratory:

- follows ribcage width/depth and torso height

Digestive:

- follows torso length and abdomen/pelvis placement
- abdomen depth affects fit mildly, not as direct organ enlargement

Endocrine:

- follows body-space height and torso envelope

Urinary:

- follows pelvis/hip region and lower torso placement

Nervous:

- follows height and centerline

Skeletal:

- follows height, torso width, and chest depth as the broad frame reference

## Limitations

- This does not deform organs from anatomical landmarks.
- It does not infer disease-state organ enlargement.
- It does not use DXA to infer internal anatomy.
- It is approximate visual registration for patient communication.

Further improvement should use registered landmarks from the outer shell or a coherent
internal anatomy template before attempting more detailed organ deformation.

## Verification

Run:

```bash
npm run verify:body-fit
```

The verifier loads the compressed organ/system GLBs in Blender, fetches generated Anny meshes
for the representative presets, applies the same coarse transforms used by the app, and checks
the transformed system vertices against the shell's vertical cross-section envelope.

This proves the current visualization fit does not obviously place systems outside the outer
shell for the tested presets. It does not prove medical anatomical correctness.
