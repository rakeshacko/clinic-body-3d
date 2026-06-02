import { EffectComposer, Bloom, Vignette, SMAA } from "@react-three/postprocessing";
import { KernelSize } from "postprocessing";

/**
 * Selective glow: the shell is dark/transmissive, the systems are emissive and bright.
 * A luminance-gated Bloom therefore blooms the lit systems only — glow, not haze.
 */
export function PostFX() {
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      <Bloom
        intensity={0.55}
        luminanceThreshold={0.32}
        luminanceSmoothing={0.28}
        mipmapBlur
        kernelSize={KernelSize.LARGE}
      />
      <Vignette eskil={false} offset={0.32} darkness={0.72} />
      <SMAA />
    </EffectComposer>
  );
}
