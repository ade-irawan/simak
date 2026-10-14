import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

// Pengembangan lokal: `npm run dev` lalu arahkan /api ke backend (mis. docker compose di :8088).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.VITE_API_TARGET ?? "http://localhost:8088", changeOrigin: false },
      "/simak-bukti": { target: process.env.VITE_API_TARGET ?? "http://localhost:8088", changeOrigin: false },
    },
  },
});
