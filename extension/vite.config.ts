import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { copyFileSync, mkdirSync, existsSync, rmSync } from "node:fs";
import type { Plugin } from "vite";

const ENTRY = process.env.TRYNIQ_ENTRY ?? "popup";

interface EntryDef {
  inputs: Record<string, string>;
  format: "iife" | "es";
  outDir: string;
  entryFileNames?: string;
  preserveEntryHTML?: boolean;
  emptyOutDir: boolean;
}

const entries: Record<string, EntryDef> = {
  background: {
    inputs: { background: resolve(__dirname, "src/background.ts") },
    format: "iife",
    outDir: "dist",
    entryFileNames: "[name].js",
    emptyOutDir: false,
  },
  content: {
    inputs: { content: resolve(__dirname, "src/content.ts") },
    format: "iife",
    outDir: "dist",
    entryFileNames: "[name].js",
    emptyOutDir: false,
  },
  injected: {
    inputs: { injected: resolve(__dirname, "src/injected.ts") },
    format: "iife",
    outDir: "dist",
    entryFileNames: "[name].js",
    emptyOutDir: false,
  },
  worklet: {
    inputs: { "audio-worklet": resolve(__dirname, "src/audio-worklet.ts") },
    format: "iife",
    outDir: "dist",
    entryFileNames: "[name].js",
    emptyOutDir: false,
  },
  popup: {
    inputs: { popup: "index.html" },
    format: "es",
    outDir: "../../dist/popup",
    emptyOutDir: false,
  },
};

const def = entries[ENTRY];
if (!def) throw new Error(`unknown TRYNIQ_ENTRY=${ENTRY}`);

function copyStatics(): Plugin {
  return {
    name: "tryniq-copy-statics",
    closeBundle() {
      if (ENTRY !== "popup") return;
      const dist = resolve(__dirname, "dist");
      copyFileSync(resolve(__dirname, "manifest.json"), resolve(dist, "manifest.json"));
      const vad = resolve(__dirname, "vendor/silero_vad.onnx");
      if (existsSync(vad)) {
        mkdirSync(resolve(dist, "vendor"), { recursive: true });
        copyFileSync(vad, resolve(dist, "vendor/silero_vad.onnx"));
      }
      const iconsSrc = resolve(__dirname, "public/icons");
      if (existsSync(iconsSrc)) {
        mkdirSync(resolve(dist, "icons"), { recursive: true });
        for (const size of [16, 32, 48, 128]) {
          const f = resolve(iconsSrc, `icon-${size}.png`);
          if (existsSync(f)) copyFileSync(f, resolve(dist, `icons/icon-${size}.png`));
        }
      }
      const ortSrc = resolve(__dirname, "node_modules/onnxruntime-web/dist");
      if (existsSync(ortSrc)) {
        mkdirSync(resolve(dist, "ort"), { recursive: true });
        for (const f of [
          "ort-wasm-simd-threaded.wasm",
          "ort-wasm-simd-threaded.mjs",
          "ort-wasm-simd-threaded.jsep.wasm",
          "ort-wasm-simd-threaded.jsep.mjs",
        ]) {
          const p = resolve(ortSrc, f);
          if (existsSync(p)) copyFileSync(p, resolve(dist, "ort", f));
        }
      }
    },
  };
}

function emptyOnce(): Plugin {
  return {
    name: "tryniq-empty-once",
    enforce: "pre",
    buildStart() {
      if (process.env.TRYNIQ_FIRST === "1") {
        const dist = resolve(__dirname, "dist");
        if (existsSync(dist)) rmSync(dist, { recursive: true, force: true });
      }
    },
  };
}

export default defineConfig({
  root: ENTRY === "popup" ? resolve(__dirname, "src/popup") : __dirname,
  base: "./",
  plugins: def.format === "es" ? [react(), copyStatics(), emptyOnce()] : [emptyOnce(), copyStatics()],
  build: {
    outDir: def.outDir,
    emptyOutDir: def.emptyOutDir,
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      input: ENTRY === "popup" ? resolve(__dirname, "src/popup/index.html") : def.inputs,
      output: {
        format: def.format,
        entryFileNames: def.entryFileNames ?? "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
      onLog(level, log, defaultHandler) {
        if (log.code === "EMPTY_IMPORT_META") return;
        defaultHandler(level, log);
      },
      ...(def.format === "iife"
        ? { codeSplitting: false, transform: { define: { "import.meta": "{}" } } }
        : {}),
    },
  },
});
