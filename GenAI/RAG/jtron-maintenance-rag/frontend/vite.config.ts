import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During `npm run dev`, forward API calls to the backend so the browser
// stays on a single origin (no CORS). In production, nginx does the same job.
const BACKEND = process.env.VITE_BACKEND_URL ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": { target: BACKEND, changeOrigin: true },
      "/sessions": { target: BACKEND, changeOrigin: true },
      "/healthz": { target: BACKEND, changeOrigin: true },
    },
  },
});
