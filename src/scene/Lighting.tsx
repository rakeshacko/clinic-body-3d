/** Low ambient, one soft key, a cool rim to separate the shell from the background. */
export function Lighting() {
  return (
    <>
      <ambientLight intensity={0.18} color="#9fb8c4" />
      {/* Soft warm key from front-upper-left */}
      <directionalLight position={[-1.6, 2.2, 2.4]} intensity={0.9} color="#ffe9d2" />
      {/* Cool rim from behind to carve the silhouette */}
      <directionalLight position={[1.4, 1.0, -2.6]} intensity={1.1} color="#7fb6d8" />
      {/* Gentle fill */}
      <pointLight position={[0, -0.6, 1.8]} intensity={0.25} color="#bfe2e6" distance={6} />
    </>
  );
}
