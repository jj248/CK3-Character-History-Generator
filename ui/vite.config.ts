import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(async () => ({
  plugins: [react()],

  // Prevent Vite from obscuring Rust compiler errors
  clearScreen: false,

  server: {
    port: 5173,
    // Fail if port is already in use rather than trying the next one
    strictPort: true,
    // Proxy all /api/* requests to the FastAPI backend during development
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
        changeOrigin: true,
      },
    },
    watch: {
      // Watch the Tauri src directory so hot-reload triggers on Rust changes
      ignored: ["**/src-tauri/**"],
    },
  },
}));