import fs from "node:fs";
import path from "node:path";

const roots = ["services/api", "apps/web", "packages"];
const forbidden = [/publish\.submit\s*\(/, /social-auto-upload/i, /xiaohongshu-mcp/i, /send_dm\s*\(/, /post_comment\s*\(/, /platform_accounts/];
let checked = 0;
function scan(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", ".next", "__pycache__"].includes(entry.name)) continue;
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) scan(file);
    else if (/\.(py|ts|tsx|json|mjs)$/.test(file)) {
      const source = fs.readFileSync(file, "utf8");
      checked++;
      for (const pattern of forbidden) if (pattern.test(source)) throw new Error(`Boundary violation: ${file}: ${pattern}`);
    }
  }
}
roots.forEach(scan);
console.log(`PASS: ${checked} source/config files scanned. Runtime egress is verified separately in pytest.`);
