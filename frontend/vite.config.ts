import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const PYODIDE_EXCLUDE = [
  "!**/*.{md,html}",
  "!**/*.d.ts",
  "!**/*.whl",
  "!**/pyodide/node_modules",
];

function viteStaticCopyPyodide() {
  const pyodideDir = dirname(
    fileURLToPath(import.meta.resolve("pyodide"))
  );

  return viteStaticCopy({
    targets: [
      {
        src: [
          join(pyodideDir, "*").replace(/\\/g, "/"),
          ...PYODIDE_EXCLUDE,
        ],
        dest: "assets",
      },
    ],
  });
}

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopyPyodide(),
  ],

  optimizeDeps: {
    exclude: ["pyodide"],
  },
});