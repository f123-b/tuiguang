import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
const code = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(".data/motion-lab");
const out = path.resolve(".data/有招动效试片-20261108/frames");
await fs.mkdir(out, { recursive: true });
const token = randomBytes(24).toString("hex");
let received = 0;
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://127.0.0.1:8769");
    if (req.method === "POST") {
      if (
        req.headers["x-render-token"] !== token ||
        req.headers.origin !== "http://127.0.0.1:8769"
      ) {
        res.writeHead(403).end();
        return;
      }
      if (url.pathname === "/reset") {
        received = 0;
        res.end("ok");
        return;
      }
      const index = Number(url.searchParams.get("index"));
      if (
        url.pathname !== "/frame" ||
        !Number.isInteger(index) ||
        index !== received ||
        index < 0 ||
        index >= 1800
      ) {
        res.writeHead(400).end();
        return;
      }
      const chunks = [];
      let bytes = 0;
      for await (const chunk of req) {
        bytes += chunk.length;
        if (bytes > 16 * 1024 * 1024) throw Error("frame too large");
        chunks.push(chunk);
      }
      const body = Buffer.concat(chunks);
      if (body.readUInt32BE(0) !== 0x89504e47) throw Error("not PNG");
      await fs.writeFile(
        path.join(out, `${String(index).padStart(5, "0")}.png`),
        body,
      );
      received++;
      res.end("ok");
      return;
    }
    if (url.pathname === "/state") {
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ received }));
      return;
    }
    let file;
    if (url.pathname === "/") {
      let html = await fs.readFile(path.join(code, "index.html"), "utf8");
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.end(html.replaceAll("__RENDER_TOKEN__", token));
      return;
    }
    if (url.pathname === "/scene.js") {
      res.setHeader("Content-Type", "application/javascript");
      res.end(await fs.readFile(path.join(code, "scene.js")));
      return;
    }
    const vendor = url.pathname.startsWith("/vendor/");
    const base = vendor
      ? path.resolve(".data/motion-runtime/node_modules/three")
      : root;
    file = path.resolve(
      base,
      "." + decodeURIComponent(url.pathname.replace(/^\/vendor/, "")),
    );
    if (!file.startsWith(base + path.sep)) {
      res.writeHead(403).end();
      return;
    }
    res.setHeader(
      "Content-Type",
      {
        ".js": "application/javascript",
        ".json": "application/json",
        ".jpg": "image/jpeg",
        ".png": "image/png",
      }[path.extname(file)] || "application/octet-stream",
    );
    res.end(await fs.readFile(file));
  } catch (e) {
    res.writeHead(400).end("local render error");
    console.log(e.message);
  }
});
server.listen(8769, "127.0.0.1", () =>
  console.log(
    "Local motion sample http://127.0.0.1:8769; no external model requests",
  ),
);
