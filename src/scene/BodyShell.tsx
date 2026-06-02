import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { BufferAttribute, BufferGeometry, Group, Mesh, MeshPhysicalMaterial } from "three";
import { useAppStore } from "../store";
import { buildAnnyQuery, type BodyFitParams } from "../bodyFit";

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const ANNY_URL = (import.meta.env.VITE_ANNY_URL ?? "http://localhost:8765").replace(/\/$/, "");

/** Frosted-glass body envelope the lit systems sit inside. Fades in first in the reveal sequence. */
export function BodyShell({ model }: { model: string }) {
  const useAnnyShell = useAppStore((s) => s.useAnnyShell);
  const bodyFit = useAppStore((s) => s.bodyFit);

  if (useAnnyShell) return <AnnyBodyShell fallbackModel={model} params={bodyFit} />;
  return <StaticBodyShell model={model} />;
}

function makeShellMaterial() {
  return new MeshPhysicalMaterial({
    color: "#bfe2e6",
    roughness: 0.5,
    metalness: 0,
    transmission: 1,
    thickness: 0.6,
    ior: 1.2,
    attenuationColor: "#3a6b72",
    attenuationDistance: 1.4,
    transparent: true,
    opacity: 0,
    depthWrite: false,
  });
}

function StaticBodyShell({ model }: { model: string }) {
  const { scene } = useGLTF(model);
  const ref = useRef<Group>(null);
  const matRef = useRef<MeshPhysicalMaterial | null>(null);
  const revealRef = useRef(0);

  const cloned = useMemo(() => {
    const c = scene.clone(true);
    const mat = makeShellMaterial();
    c.traverse((o) => {
      if ((o as Mesh).isMesh) (o as Mesh).material = mat;
    });
    matRef.current = mat;
    return c;
  }, [scene]);

  useFrame((_, dt) => {
    const revealed = useAppStore.getState().revealed;
    const k = 1 - Math.pow(0.02, dt);
    revealRef.current = lerp(revealRef.current, revealed ? 1 : 0, k);
    const r = revealRef.current;
    if (matRef.current) matRef.current.opacity = 0.18 * r;
    if (ref.current) ref.current.visible = r > 0.01;
  });

  return (
    <group ref={ref}>
      <primitive object={cloned} />
    </group>
  );
}

function materialReveal(matRef: MutableRefObject<MeshPhysicalMaterial | null>, ref: MutableRefObject<Group | null>, revealRef: MutableRefObject<number>, dt: number) {
  const revealed = useAppStore.getState().revealed;
  const k = 1 - Math.pow(0.02, dt);
  revealRef.current = lerp(revealRef.current, revealed ? 1 : 0, k);
  const r = revealRef.current;
  if (matRef.current) matRef.current.opacity = 0.18 * r;
  if (ref.current) ref.current.visible = r > 0.01;
}

async function fetchArrayBuffer(url: string, signal: AbortSignal) {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`${url} ${res.status}`);
  return res.arrayBuffer();
}

function geometryFromAnny(facesBuffer: ArrayBuffer, verticesBuffer: ArrayBuffer) {
  const source = new Float32Array(verticesBuffer);
  const converted = new Float32Array(source.length);
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let minZ = Infinity, maxZ = -Infinity;

  for (let i = 0; i < source.length; i += 3) {
    const x = source[i];
    const y = source[i + 2];
    const z = -source[i + 1];
    converted[i] = x;
    converted[i + 1] = y;
    converted[i + 2] = z;
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
  }

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2 + 0.02;
  const cz = (minZ + maxZ) / 2;
  for (let i = 0; i < converted.length; i += 3) {
    converted[i] -= cx;
    converted[i + 1] -= cy;
    converted[i + 2] -= cz;
  }

  const faces = new Int32Array(facesBuffer);
  const geo = new BufferGeometry();
  geo.setIndex(new BufferAttribute(new Uint32Array(faces), 1));
  geo.setAttribute("position", new BufferAttribute(converted, 3));
  geo.computeVertexNormals();
  geo.computeBoundingBox();
  return geo;
}

function AnnyBodyShell({ fallbackModel, params }: { fallbackModel: string; params: BodyFitParams }) {
  const ref = useRef<Group>(null);
  const matRef = useRef<MeshPhysicalMaterial | null>(null);
  const revealRef = useRef(0);
  const facesRef = useRef<ArrayBuffer | null>(null);
  const [geometry, setGeometry] = useState<BufferGeometry | null>(null);
  const [failed, setFailed] = useState(false);

  const material = useMemo(() => {
    const mat = makeShellMaterial();
    matRef.current = mat;
    return mat;
  }, []);

  useEffect(() => {
    let disposed = false;
    const ac = new AbortController();

    async function load() {
      try {
        setFailed(false);
        if (!facesRef.current) facesRef.current = await fetchArrayBuffer(`${ANNY_URL}/faces`, ac.signal);
        const vertices = await fetchArrayBuffer(`${ANNY_URL}/mesh?${buildAnnyQuery(params)}`, ac.signal);
        if (disposed || !facesRef.current) return;
        const next = geometryFromAnny(facesRef.current, vertices);
        setGeometry((prev) => {
          prev?.dispose();
          return next;
        });
      } catch (e) {
        if (!ac.signal.aborted) setFailed(true);
      }
    }

    void load();
    return () => {
      disposed = true;
      ac.abort();
    };
  }, [params]);

  useEffect(() => () => geometry?.dispose(), [geometry]);

  useFrame((_, dt) => materialReveal(matRef, ref, revealRef, dt));

  if (failed && !geometry) return <StaticBodyShell model={fallbackModel} />;

  return (
    <group ref={ref}>
      {geometry && <mesh geometry={geometry} material={material} />}
      {!geometry && <StaticBodyShell model={fallbackModel} />}
    </group>
  );
}
