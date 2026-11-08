// Start only the separately installed, pinned local service. No model downloads or cloud calls.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";

const root = process.cwd();
const data = path.join(root, ".data");
const source = path.join(data, "comfyui-wan");
const revision = "0decb39ee5b5e17c200334589fc317dbbe98310e";
const python = path.join(
  data,
  "video-gen-runtime",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const commit = spawnSync("git", ["-C", source, "rev-parse", "HEAD"], {
  encoding: "utf8",
});
if (
  !existsSync(python) ||
  commit.status !== 0 ||
  commit.stdout.trim() !== revision
)
  throw new Error(
    "本机生成环境未安装或 ComfyUI 版本不匹配，见 docs/implementation/LOCAL_AI_VIDEO.md",
  );
for (const name of ["user", "output", "input", "temp"])
  mkdirSync(path.join(data, `comfy-wan-${name}`), { recursive: true });
const env = {
  ...process.env,
  PYTHONUTF8: "1",
  HF_HUB_OFFLINE: "1",
  TRANSFORMERS_OFFLINE: "1",
  HF_HUB_DISABLE_TELEMETRY: "1",
  COMFYUI_DISABLE_PRODUCT_TIPS: "1",
  TEMP: path.join(data, "comfy-wan-temp"),
  TMP: path.join(data, "comfy-wan-temp"),
};
const args = [
  path.join(source, "main.py"),
  "--listen",
  "127.0.0.1",
  "--port",
  "8188",
  "--models-directory",
  path.join(data, "wan22-models"),
  "--output-directory",
  path.join(data, "comfy-wan-output"),
  "--input-directory",
  path.join(data, "comfy-wan-input"),
  "--user-directory",
  path.join(data, "comfy-wan-user"),
  "--temp-directory",
  path.join(data, "comfy-wan-temp"),
  "--lowvram",
  "--disable-auto-launch",
  "--reserve-vram",
  "2",
  "--disable-all-custom-nodes",
  "--offline",
  "--disable-metadata",
  "--disable-assets",
  "--cache-none",
];
const child = spawn(python, args, { env, stdio: "inherit", windowsHide: true });
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill());
child.on("error", (e) => {
  console.error(e.message);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
