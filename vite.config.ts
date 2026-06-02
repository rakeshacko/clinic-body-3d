import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173 },
  // GLBs ship pre-compressed; keep them out of the inline-asset path.
  assetsInclude: ["**/*.glb"],
});
