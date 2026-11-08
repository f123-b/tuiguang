// Local review of the two fictional AI test shots; no approval, generation or publishing.
import http from "node:http";
import { createReadStream, statSync } from "node:fs";
import path from "node:path";
const directory = path.resolve(".data/ai-drama-proof");
const files = new Map([
  ["/realistic.mp4", "realistic-http.mp4"],
  ["/anime.mp4", "anime-http.mp4"],
]);
const movie = path.resolve(
  ".data/ai-drama-quality-v2/youzhao-choice-v2-b-review.mp4",
);
const moviePage = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>有招 · 那个选择 · 重拍审看</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101818;color:#eff3ef;font:16px/1.8 system-ui,"Microsoft Yahei",sans-serif}main{max-width:1080px;margin:auto;padding:42px 24px}small{color:#a7c8b5}h1{font-size:34px;margin:10px 0}p{color:#b1c1b7}video{display:block;width:100%;border-radius:16px;background:#000;margin:24px 0}a{color:#b1d2f8;margin-right:24px}aside{border-top:1px solid #324338;margin-top:28px;padding-top:14px}@media(max-width:600px){main{padding:24px 16px}h1{font-size:26px}}</style>
<main><small>有招 / 重拍审看版 V2</small><h1>那个选择</h1><p>约16秒有声短片：被追问，停顿，找到当时的选择，再回到人物。真人动态镜头、真实产品备注操作、双声线画外音与字幕。</p>
<video controls playsinline preload="metadata" src="/film.mp4"></video><a href="/film.mp4" download="有招-那个选择-AI重拍审看V2.mp4">保存审看版</a><a href="http://localhost:3000/studio/video/ai">进入短剧工作台</a><aside><p>人物与项目是虚构演绎，界面来自真实产品的隔离示例。声音为本机合成画外音，无人物对口型。生成源画面1280×704，审看合成1280×720。当前等待你审看，尚未记录质量通过或发布。</p><a href="/previous">查看已否决旧试片的问题记录</a></aside></main></html>`;
const page = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>有招 · AI动态试镜</title>
<style>*{box-sizing:border-box}body{margin:0;background:#10151d;color:#edf2f7;font:16px/1.7 system-ui,"Microsoft Yahei",sans-serif}main{max-width:1200px;margin:auto;padding:48px 24px}small{color:#a8d9c1}h1{font-size:36px;margin:12px 0}p{color:#aeb8c7}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:32px}article{background:#1a222e;border:1px solid #2b3748;border-radius:20px;overflow:hidden}video{width:100%;display:block;background:#080b10}section{padding:20px}h2{margin:0 0 8px;font-size:22px}a{color:#b7d3ff}aside{padding:20px;border:1px solid #3f5065;border-radius:16px;margin-top:28px}@media(max-width:720px){.grid{grid-template-columns:1fr}main{padding:24px 16px}h1{font-size:28px}}</style>
<main><small>有招 / 已否决的旧试片 · 2026.11.08</small><h1>这版未达到交付要求，正在重做。</h1><p>保留两段旧片作问题记录：存在脸/手形变、背景闪烁与清晰度不足。每段仅2.04秒、无声，没有形成剧情。它们不是交付成片；新版先验证稳定镜头，再剪辑有声故事。</p>
<div class="grid"><article><video src="/realistic.mp4" controls playsinline preload="metadata" muted></video><section><h2>01 · 真人旧试片（未通过）</h2><p>雨夜书桌，落笔、低头与表情变化。脸、手和背景的连续性不合格。</p><a href="/realistic.mp4" download>保存问题记录</a></section></article>
<article><video src="/anime.mp4" controls playsinline preload="metadata" muted></video><section><h2>02 · 动漫旧试片（未通过）</h2><p>参考图已修正，但动态画面仍有漂移与变形。</p><a href="/anime.mp4" download>保存问题记录</a></section></article></div>
<aside><strong>制作入口已经接入工作台</strong><p>参考图 → 动态镜头 → 逐镜检查 → 排序 → 旁白与字幕 → 成片预览 → 用户确认后高清合成。现在仍有中间帧偏软和细节漂移，不提供人物对口型，也不保证跨镜头角色完全一致。</p><a href="http://localhost:3000/studio/video/ai">进入 AI 动态短剧工作台</a></aside></main></html>`;
http
  .createServer((req, res) => {
    if (req.url === "/film.mp4") {
      try {
        const stat = statSync(movie);
        res.writeHead(200, {
          "Content-Type": "video/mp4",
          "Content-Length": stat.size,
          "Cache-Control": "no-store",
        });
        createReadStream(movie).pipe(res);
      } catch {
        res.writeHead(404);
        res.end("New review edit not available on this machine");
      }
      return;
    }
    const file = files.get(req.url);
    if (file) {
      const target = path.join(directory, file);
      try {
        const stat = statSync(target);
        res.writeHead(200, {
          "Content-Type": "video/mp4",
          "Content-Length": stat.size,
          "Cache-Control": "no-store",
        });
        createReadStream(target).pipe(res);
      } catch {
        res.writeHead(404);
        res.end("Test shot not generated on this machine");
      }
    } else if (
      req.url === "/watch" ||
      req.url === "/" ||
      req.url === "/previous"
    ) {
      res.writeHead(200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
        "Content-Security-Policy":
          "default-src 'self'; style-src 'unsafe-inline'; media-src 'self'; frame-ancestors 'none'",
      });
      res.end(req.url === "/previous" ? page : moviePage);
    } else {
      res.writeHead(404);
      res.end();
    }
  })
  .listen(8788, "127.0.0.1", () =>
    console.log("AI试镜审看: http://127.0.0.1:8788/watch"),
  );
