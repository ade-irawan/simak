import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

// Aplikasi dapat dipasang di sub-path (mis. https://kampus.ac.id/simak/): set BASE_PATH=/simak saat build.
// Kosong = dilayani dari akar.
const dasar = (process.env.BASE_PATH ?? "").trim().replace(/^\/*/, "/").replace(/\/+$/, "");
const base = dasar === "/" ? "" : dasar;

// Pengembangan lokal: `npm run dev` lalu arahkan /api ke backend (mis. docker compose di :8088).
export default defineConfig({
  base: `${base}/`,
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      [`${base}/api`]: { target: process.env.VITE_API_TARGET ?? "http://localhost:8088", changeOrigin: false },
      [`${base}/simak-bukti`]: { target: process.env.VITE_API_TARGET ?? "http://localhost:8088", changeOrigin: false },
    },
  },
});
