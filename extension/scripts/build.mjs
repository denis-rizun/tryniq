import { spawnSync } from "node:child_process";
import { rmSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const dist = resolve(root, "dist");
if (existsSync(dist)) rmSync(dist, { recursive: true, force: true });

const entries = ["background", "content", "injected", "worklet", "popup"];
for (const e of entries) {
  console.log(`\n[tryniq-build] entry=${e}`);
  const res = spawnSync("pnpm", ["exec", "vite", "build"], {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, TRYNIQ_ENTRY: e },
  });
  if (res.status !== 0) process.exit(res.status ?? 1);
}
console.log("\n[tryniq-build] done");
