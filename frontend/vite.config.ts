/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The frontend talks to the backend through the absolute URL in VITE_API_URL
// (see src/services/config.ts), so no dev proxy is configured here.
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 3000, strictPort: true },
  preview: { host: true, port: 3000, strictPort: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
