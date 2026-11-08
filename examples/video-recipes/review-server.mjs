// Local review gallery for real API outputs; no approval or publish action.
import { createServer } from "node:http";
import { createReadStream, readFileSync, statSync } from "node:fs";
import path from "node:path";

const directory = path.resolve(
  process.argv[2] || ".data/多类型视频验收-20261108",
);
const projects = JSON.parse(
  readFileSync(path.join(directory, "projects.json"), "utf8"),
);
const escape = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll('"', "&quot;");
const media = new Map(
  projects.map((p, i) => [
    `/media/${i}.mp4`,
    path.join(directory, path.basename(p.path)),
  ]),
);
const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>有招 · 五种视频制作预览</title><style>
*{box-sizing:border-box}body{margin:0;background:#101819;color:#f1f0e8;font:16px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1260px;margin:auto;padding:56px 28px}header{max-width:850px;margin-bottom:42px}small{color:#a8cbad;letter-spacing:.14em}h1{font-size:clamp(30px,5vw,52px);line-height:1.2;margin:18px 0}p{color:#b6c3bf}a{color:#bceba8}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,370px),1fr));gap:28px}article{border:1px solid #34423f;border-radius:16px;overflow:hidden;background:#17211f}video{display:block;width:100%;height:330px;object-fit:contain;background:#080e0d}article div{padding:20px}h2{margin:0;font-size:23px}article p{font-size:14px;margin:8px 0 0}.meta{color:#a8cbad;font-size:13px}footer{margin-top:36px;border-top:1px solid #34423f;padding-top:24px;font-size:14px}</style>
<main><header><small>YOUZHAO / LOCAL PRODUCTION REVIEW</small><h1>同一个产品，<br>五种讲述方式。</h1><p>以下均由软件的真实制作链输出，含本地配音与同步字幕。带水印预览尚未人工批准，不是高清发布成片。</p><a href="http://localhost:3000/studio/video/new">进入视频工作台，制作自己的内容 →</a></header><section>${projects.map((p, i) => `<article><video controls preload="metadata" playsinline src="/media/${i}.mp4"></video><div><h2>${escape(p.name)}</h2><p class="meta">${escape(p.receipt.duration_sec)} 秒 · ${p.receipt.width} × ${p.receipt.height} · 30fps</p><p>${escape({ mg: "流程节点与动态标记", screen_demo: "真实项目设置操作，合成演示资料", montage: "授权实拍素材，全画幅竖屏剪辑", illustrated: "AI 插画分镜与镜头运动，无角色表演", mixed: "图解、实拍与真实界面同片组合" }[p.mode])}</p></div></article>`).join("")}</section><footer><p>素材与声音来源已记入验收回执。人物情节为演绎；AI 动态场景生成、角色表演及三维引擎仍未接入。最终高清与发布包须回到工作台审看、确认，第三方发布由用户自行完成。</p></footer></main></html>`;

createServer((req, res) => {
  if (!["GET", "HEAD"].includes(req.method)) {
    res.writeHead(405).end();
    return;
  }
  const url = new URL(req.url, "http://127.0.0.1").pathname;
  const common = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
  };
  if (url === "/" || url === "/watch") {
    res.writeHead(200, {
      ...common,
      "Content-Type": "text/html; charset=utf-8",
    });
    res.end(req.method === "HEAD" ? undefined : html);
    return;
  }
  const file = media.get(url);
  if (!file) {
    res.writeHead(404, common).end();
    return;
  }
  const size = statSync(file).size;
  const range = req.headers.range?.match(/^bytes=(\d+)-(\d*)$/);
  if (req.headers.range && !range) {
    res.writeHead(416, common).end();
    return;
  }
  const start = range ? Number(range[1]) : 0;
  const end =
    range && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
  if (start > end || start >= size) {
    res.writeHead(416, { ...common, "Content-Range": `bytes */${size}` }).end();
    return;
  }
  res.writeHead(range ? 206 : 200, {
    ...common,
    "Content-Type": "video/mp4",
    "Accept-Ranges": "bytes",
    "Content-Length": end - start + 1,
    ...(range ? { "Content-Range": `bytes ${start}-${end}/${size}` } : {}),
  });
  if (req.method === "HEAD") res.end();
  else createReadStream(file, { start, end }).pipe(res);
}).listen(8787, "127.0.0.1", () =>
  console.log("Local video review: http://127.0.0.1:8787/watch"),
);
