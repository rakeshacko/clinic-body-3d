import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { Group, Mesh, MeshPhysicalMaterial } from "three";
import { useAppStore } from "../store";

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Frosted-glass body envelope the lit systems sit inside. Fades in first in the reveal sequence. */
export function BodyShell({ model }: { model: string }) {
  const { scene } = useGLTF(model);
  const ref = useRef<Group>(null);
  const matRef = useRef<MeshPhysicalMaterial | null>(null);
  const revealRef = useRef(0);

  const cloned = useMemo(() => {
    const c = scene.clone(true);
    const mat = new MeshPhysicalMaterial({
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
