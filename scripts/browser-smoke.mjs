// Read-only route and viewport checks against an already authenticated QA browser session.
// Requires agent-browser. First read: agent-browser skills get core
import fs from "node:fs";
import { spawnSync } from "node:child_process";

const session = process.env.SMOKE_BROWSER_SESSION || "xuliu-dev";
if (!/^[a-z0-9-]+$/.test(session)) throw new Error("Invalid browser session name");
function browser(args) {
  const result = spawnSync(process.platform === "win32" ? "agent-browser.cmd" : "agent-browser", ["--session", session, ...args], {
    encoding: "utf8", shell: process.platform === "win32", timeout: 15000,
  });
  if (result.status !== 0 || result.error || result.stdout.includes("✗")) throw new Error(result.stderr || result.stdout || String(result.error));
  return result.stdout.trim();
}
function evaluate(source) {
  const encoded = Buffer.from(source, "utf8").toString("base64");
  let result = JSON.parse(browser(["eval", "-b", encoded]));
  if (typeof result === "string") result = JSON.parse(result);
  return result;
}
function openRoute(route) {
  browser(["open", `http://localhost:3000${route}`]);
  // Wait for data-backed content after hydration / authenticated redirects.
  browser(["wait", "--fn", "Boolean(document.querySelector('main')?.querySelector('h1,h2,h3'))"]);
}
const ids = {};
for (const [key, env] of [["content", "SMOKE_CONTENT_ID"], ["video", "SMOKE_VIDEO_ID"], ["package", "SMOKE_PACKAGE_ID"], ["topic", "SMOKE_TOPIC_ID"]]) {
  if (process.env[env] && !/^[a-f0-9]{32}$/.test(process.env[env])) throw new Error(`Invalid ${env}`);
  ids[key] = process.env[env] || "missing";
}
const routes = ["/auth/login", "/onboarding/welcome", "/onboarding/brand", "/onboarding/creator", "/onboarding/preview", "/dashboard", "/creator", "/creator/edit", "/creator/activity", "/calendar", "/topics", `/topics/${ids.topic}`, "/campaigns", `/studio/article/${ids.content}`, "/studio/covers", "/studio/assets", "/studio/video/new", `/studio/video/${ids.video}`, `/studio/video/${ids.video}/storyboard`, `/studio/video/${ids.video}/render`, "/compliance", `/compliance/${ids.content}`, "/publish", `/publish/package/${ids.package}`, "/publish/guide/xiaohongshu", `/publish/record/${ids.package}`, "/analytics", "/analytics/import", "/growth", "/growth/memory", "/brand", "/settings", "/help", "/ops/diagnostics", "/ops/releases"];
routes.push(`/studio/article/${ids.content}/graphics`, "/notifications", "/ops/maintenance");
const report = { routes: [], viewports: [] };
browser(["set", "viewport", "1440", "1000"]);
for (const route of routes) {
  openRoute(route);
  const state = evaluate('JSON.stringify({title:document.title,headings:[...document.querySelectorAll("h1,h2,h3")].map(x=>x.textContent),overflow:document.documentElement.scrollWidth>innerWidth})');
  if (!state.headings.length) throw new Error(`No rendered headings: ${route}`);
  report.routes.push({ route, ...state });
}
for (const width of [375, 390, 768, 1024, 1440, 1920]) {
  browser(["set", "viewport", String(width), "1000"]);
  for (const route of ["/dashboard", "/calendar", `/topics/${ids.topic}`, "/studio/covers", `/studio/article/${ids.content}/graphics`, `/studio/video/${ids.video}`, "/growth", "/settings", "/notifications", "/publish"]) {
  openRoute(route);
  const state = evaluate('JSON.stringify({width:innerWidth,document:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth})');
  if (state.overflow) throw new Error(`Horizontal overflow at ${width}`);
  report.viewports.push({ route, ...state });
  }
}
fs.mkdirSync("artifacts", { recursive: true });
fs.writeFileSync("artifacts/browser-smoke.json", JSON.stringify(report, null, 2));
console.log(`PASS: ${report.routes.length} route renders and ${report.viewports.length} viewport checks. This does not assert completion of planned features.`);
