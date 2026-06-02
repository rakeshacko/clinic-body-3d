# Acko Clinic Body 3D

Doctor-led 3D body consultation prototype for post-screening review. The app shows a
translucent body shell with internal body systems colored by screening status, plus a review
panel for the selected system.

## Requirements

- Node.js 20 or newer
- npm
- Optional for asset pipeline work: Blender installed at
  `/Applications/Blender.app/Contents/MacOS/Blender`
- Optional for the Anny/DXA body preview: the local Anny Python environment at `/tmp/annyenv`

## Install

```bash
npm install
```

## Run the App

```bash
npm run dev -- --host 0.0.0.0
```

Vite serves the app at:

```txt
http://localhost:5173/
```

The dev server also prints LAN URLs that can be opened from another device on the same
network.

## Environment

The app runs with mock screening data by default. To create a local env file:

```bash
cp .env.example .env
```

Supported variables:

```txt
VITE_DATA_SOURCE=mock
VITE_REMOTE=
VITE_RELAY_URL=ws://localhost:8787
```

`VITE_DATA_SOURCE=mock` uses the bundled demo members in `src/data/mock/members.ts`.

## Useful Commands

```bash
npm test
npm run typecheck
npm run build
npm run preview
```

Command notes:

- `npm test` runs the scoring engine tests.
- `npm run typecheck` runs TypeScript without emitting files.
- `npm run build` creates the production build in `dist/`.
- `npm run preview` serves the production build locally.

## Routes

```txt
/         Wall-screen kiosk view
/remote   Tablet/remote-control view
```

The main app is designed to work without external services when `VITE_REMOTE` is empty.

## Anny / DXA Body Preview

The Anny preview is a separate local prototype for mapping DXA-style body-composition data
to Anny parametric body controls. It is not wired into the main Vite app yet.

Start the Anny server:

```bash
/tmp/annyenv/bin/python asset-pipeline-v2/anny_server.py
```

Open:

```txt
http://localhost:8765/
```

It serves:

```txt
/             Three.js Anny body preview
/labels       Available Anny phenotype/local controls
/members      Synthetic DXA-style demo members
/fitted       Fitted Anny parameters
/faces        Mesh triangle indices
/mesh?...     Generated body vertices for supplied parameters
```

Regenerate fitted DXA-to-Anny parameters:

```bash
/tmp/annyenv/bin/python asset-pipeline-v2/scripts/fit_dexa.py
```

Details of the mapping are documented in `docs/DXA_TO_ANNY_MAPPING.md`.

## Asset Pipeline

The live app loads GLB assets from `public/models/`.

To rebuild the current asset set:

```bash
npm run assets:build
```

This downloads/audits source assets and runs Blender scripts. The source clones under
`asset-pipeline/sources/` are ignored by git because they are large and reproducible.

To rebuild only the MakeHuman/MPFB shell variants:

```bash
npm run assets:shells
```

The newer coherent-body spike lives in `asset-pipeline-v2/`; see
`asset-pipeline-v2/README.md` and `docs/SPEC.md` for architecture notes.

## Project Structure

```txt
src/                  React app, scene, UI, scoring, data adapters
public/models/        GLBs used by the live app
config/               Body-system scoring schema
docs/                 Product and technical notes
asset-pipeline/       Current production asset pipeline
asset-pipeline-v2/    Coherent-body and Anny/DXA research spike
```

## Clinical Positioning

This prototype is a patient-communication and review tool. The body shape and organ/system
visuals are approximate and should not be presented as diagnostic reconstruction or
patient-specific internal anatomy.
