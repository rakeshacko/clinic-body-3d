import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { Mesh, MeshStandardMaterial } from "three";
import type { SystemState } from "../scoring/types";
import { useAppStore } from "../store";
import { emissiveIntensity, statusColor } from "./colors";
import type { SystemFitTransform } from "../bodyFit";

interface Props {
  system: SystemState;
  model: string;
  /** "overview" lights every system; "focus" lights this one; "dim" pushes it back near the shell. */
  presence: "overview" | "focus" | "dim";
  /** Position in the reveal cascade (presentation order). */
  revealIndex: number;
  fit: SystemFitTransform;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const SHELL_DELAY = 0.5;
const STAGGER = 0.13;
const RAMP = 0.6;

export function SystemMesh({ system, model, presence, revealIndex, fit }: Props) {
  const { scene } = useGLTF(model);
  const matRef = useRef<MeshStandardMaterial | null>(null);
  const revealRef = useRef(0);
  const tRef = useRef(0);

  const cloned = useMemo(() => {
    const c = scene.clone(true);
    const sc = statusColor(system.status);
    const mat = new MeshStandardMaterial({
      // Tinted, lit base so the directional lights shade the surface and reveal
      // anatomical contours; emissive then adds the status glow on top.
      color: sc.clone().multiplyScalar(0.42),
      roughness: 0.5,
      metalness: 0,
      emissive: sc.clone(),
      emissiveIntensity: 0,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    c.traverse((o) => {
      if ((o as Mesh).isMesh) (o as Mesh).material = mat;
    });
    matRef.current = mat;
    return c;
  }, [scene, system.status]);

  useEffect(() => {
    const m = matRef.current;
    if (!m) return;
    const sc = statusColor(system.status);
    m.emissive.copy(sc);
    m.color.copy(sc).multiplyScalar(0.42);
  }, [system.status]);

  useFrame((_, dt) => {
    const mat = matRef.current;
    if (!mat) return;
    const revealed = useAppStore.getState().revealed;

    // Staggered cascade: advance a local timeline once the shell has appeared.
    tRef.current = revealed ? tRef.current + dt : 0;
    const start = SHELL_DELAY + revealIndex * STAGGER;
    revealRef.current = Math.min(1, Math.max(0, (tRef.current - start) / RAMP));
    const reveal = revealRef.current;

    const k = 1 - Math.pow(0.0018, dt); // frame-rate independent damping
    const full = emissiveIntensity(system.status, system.score);
    const targetIntensity =
      presence === "dim" ? 0.05 : presence === "focus" ? full * 1.15 : full;
    const targetOpacity = presence === "dim" ? 0.12 : 1;

    mat.emissiveIntensity = lerp(mat.emissiveIntensity, targetIntensity * reveal, k);
    mat.opacity = lerp(mat.opacity, targetOpacity * reveal, k);
  });

  return (
    <group position={fit.position} scale={fit.scale}>
      <primitive object={cloned} />
    </group>
  );
}
