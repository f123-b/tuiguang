import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";
const code = path.dirname(fileURLToPath(import.meta.url));
const vendor = path.resolve(".data/motion-runtime/node_modules/three");
const root = path.resolve(".data/有招那个选择-本地成片-20261108");
const frames = path.join(root, "diagram-frames");
await fs.mkdir(frames, { recursive: true });
const token = randomBytes(24).toString("hex");
let received = 0;
http
  .createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://127.0.0.1:8785");
      if (req.method === "POST") {
        if (
          req.headers["x-render-token"] !== token ||
          req.headers.origin !== "http://127.0.0.1:8785"
        ) {
          res.writeHead(403).end();
          return;
        }
        if (url.pathname === "/reset") {
          received = 0;
          res.end("ok");
          return;
        }
        const n = Number(url.searchParams.get("index"));
        if (
          url.pathname !== "/frame" ||
          !Number.isInteger(n) ||
          n !== received ||
          n < 0 ||
          n >= 360
        ) {
          res.writeHead(400).end();
          return;
        }
        const chunks = [];
        let bytes = 0;
        for await (const b of req) {
          bytes += b.length;
          if (bytes > 16 * 1024 * 1024) throw Error("frame too large");
          chunks.push(b);
        }
        const body = Buffer.concat(chunks);
        if (body.readUInt32BE(0) !== 0x89504e47) throw Error("not PNG");
        await fs.writeFile(
          path.join(frames, String(n).padStart(5, "0") + ".png"),
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
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(
          (await fs.readFile(path.join(code, "diagram.html"), "utf8")).replace(
            "__TOKEN__",
            token,
          ),
        );
        return;
      }
      if (url.pathname === "/diagram.js") file = path.join(code, "diagram.js");
      else if (url.pathname.startsWith("/vendor/")) {
        file = path.resolve(vendor, url.pathname.slice(8));
        if (!file.startsWith(vendor + path.sep)) throw Error("invalid path");
      } else if (url.pathname === "/film.mp4") {
        file = path.join(root, "交付文件/有招-那个选择-完整版.mp4");
        res.setHeader("Content-Type", "video/mp4");
      } else if (url.pathname === "/watch") {
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(
          '<meta charset="utf-8"><title>有招 · 那个选择</title><style>body{margin:0;background:#101716;display:grid;min-height:100vh;place-items:center}video{width:100%;max-height:100vh}</style><video src="/film.mp4" controls playsinline></video>',
        );
        return;
      } else {
        res.writeHead(404).end();
        return;
      }
      if (file.endsWith(".js"))
        res.setHeader("Content-Type", "text/javascript; charset=utf-8");
      res.end(await fs.readFile(file));
    } catch (error) {
      res.writeHead(400).end(String(error.message));
    }
  })
  .listen(8785, "127.0.0.1", () =>
    console.log("choice diagram at 127.0.0.1:8785"),
  );
