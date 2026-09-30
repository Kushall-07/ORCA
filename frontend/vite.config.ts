/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The frontend talks to the backend through the absolute URL in VITE_API_URL
// (see src/services/config.ts), so no dev proxy is configured here.
//
// server.watch.usePolling: the dev container's source is a bind mount of the
// Windows host filesystem (docker-compose.yml's `./frontend:/app`), and
// Windows/Docker Desktop bind mounts don't deliver inotify events into the
// Linux container - without polling, Vite's dev server never notices edits
// made on the host and keeps serving whatever it had at container start.
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 3000, strictPort: true, watch: { usePolling: true, interval: 300 } },
  preview: { host: true, port: 3000, strictPort: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
