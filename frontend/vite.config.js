import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backendUrl =
    env.VITE_BACKEND_URL ||
    env.SKILLLOCK_BACKEND_URL ||
    "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": backendUrl,
        "/uploads": backendUrl,
      },
    },
  };
});
