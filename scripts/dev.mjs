import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const root = process.cwd();
const python = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) throw new Error("请先执行 README 中的 Python 安装步骤，创建 .venv");
const env = { ...process.env, PYTHONPATH: path.join(root, "services/api"), PYTHONUTF8: "1" };
const migration = spawnSync(python, ["-m", "alembic", "upgrade", "head"], { cwd: root, env, stdio: "inherit" });
if (migration.status !== 0) process.exit(migration.status ?? 1);
const processes = [
  spawn(python, ["-m", "uvicorn", "creator.main:app", "--host", "127.0.0.1", "--port", "8000"], { env, stdio: "inherit" }),
  spawn(python, ["-m", "creator.worker"], { env, stdio: "inherit" }),
  spawn(process.execPath, [path.join(root, "node_modules/next/dist/bin/next"), "dev", "--hostname", "127.0.0.1", "--webpack"], { cwd: path.join(root, "apps/web"), env, stdio: "inherit" })
];
let stopping = false;
function stop(code = 0) { if (stopping) return; stopping = true; processes.forEach(p => p.kill()); process.exit(code); }
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
processes.forEach(p => { p.on("error", e => { console.error(e.message); stop(1); }); p.on("exit", code => stop(code ?? 0)); });
