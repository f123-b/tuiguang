// Independent local film review. No publishing or social platform calls.
import http from 'node:http';
import {createReadStream,existsSync,statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const pack=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(pack,'../../../.data/short-drama-51');
const files=new Map([
 ['/film.mp4',[path.join(out,'你来试试-v2.mp4'),'video/mp4','你来试试.mp4']],
 ['/subtitles.srt',[path.join(out,'你来试试.srt'),'text/plain; charset=utf-8','你来试试.srt']],
 ['/production.zip',[path.join(out,'你来试试-制作包-v2.zip'),'application/zip','你来试试-制作包.zip']],
 ['/poster.png',[path.join(pack,'assets/s01-two-shot-v1.png'),'image/png']],
]);
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>你来试试 · 有招原创短剧</title><style>
*{box-sizing:border-box}body{margin:0;background:#20251f;color:#f2eee3;font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1180px;margin:auto;padding:38px 28px 72px}.brand{font-size:12px;color:#b2bea2;letter-spacing:.14em}h1{font-size:clamp(34px,5vw,62px);line-height:1.3;margin:12px 0}p{color:#c4c7b6;max-width:740px}.meta{font-size:14px;color:#a7b69a}video{display:block;width:100%;aspect-ratio:16/9;background:#080c08;border-radius:10px;margin:24px 0;box-shadow:0 20px 60px #0005}nav{display:flex;flex-wrap:wrap;gap:12px}a{color:#ebeedd;text-decoration:none;border:1px solid #657256;border-radius:6px;padding:9px 18px}a:first-child{background:#e5ead6;color:#293d20;border-color:transparent}a:hover{filter:brightness(1.12)}details{font-size:13px;margin-top:30px;color:#a1ad93}summary{cursor:pointer}.notice{font-size:12px;color:#9faa90}#status{color:#d1e0bd}
</style><main><div class="brand">有招 / 原创短剧 02</div><h1>你来试试</h1><div class="meta">21.9 秒 · 真人风格 · 中文对白</div><p>他把手机递过来，她却没有接。</p><video id="film" controls playsinline preload="metadata" poster="/poster.png"><source src="/film.mp4" type="video/mp4"></video><nav><a href="/film.mp4?download=1" download="你来试试.mp4">保存视频</a><a href="/subtitles.srt?download=1" download>下载字幕</a><a href="/production.zip?download=1" download>完整制作包</a></nav><p id="status" aria-live="polite"></p><details><summary>制作记录</summary><p>两位虚构人物的一次试用。AI 动态表演、合成对白、音频驱动口型、操作特写与真实有招项目备注画面。项目经历和测试结果均为虚构，成片待你审看。</p><p>1920×1080 / 30fps 为成片画幅；动态原片为1280×704 / 24fps，包含裁切和补帧。口型在独立本地试验中制作，尚未接入软件正式生成服务。制作包保留原片、参数、字幕和回执；不包含模型或私人资料。</p></details><p class="notice">AI 剧情演绎 · 合成声音 · 虚构项目</p></main><script>const v=document.querySelector('video');v.addEventListener('ended',()=>document.querySelector('#status').textContent='已播放完毕，可以保存视频。');v.addEventListener('error',()=>document.querySelector('#status').textContent='文件暂不可读取，请稍后刷新。');</script></html>`;
const server=http.createServer((req,res)=>{
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'});res.end();return;}
 const url=new URL(req.url,'http://127.0.0.1:8790');
 if(url.pathname==='/'||url.pathname==='/watch'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:html);return;}
 const file=files.get(url.pathname);if(!file||!existsSync(file[0])){res.writeHead(404);res.end('文件尚未生成');return;}
 const size=statSync(file[0]).size;let start=0,end=size-1,status=200;
 const headers={'Content-Type':file[1],'Accept-Ranges':'bytes','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'};
 if(url.searchParams.has('download'))headers['Content-Disposition']="attachment; filename*=UTF-8''"+encodeURIComponent(file[2]||path.basename(file[0]));
 if(req.headers.range){
  const m=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
  if(!m||(!m[1]&&!m[2])){res.writeHead(416,{'Content-Range':'bytes */'+size});res.end();return;}
  if(!m[1])start=Math.max(0,size-Number(m[2]));else{start=Number(m[1]);if(m[2])end=Math.min(end,Number(m[2]));}
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=size){res.writeHead(416,{'Content-Range':'bytes */'+size});res.end();return;}
  status=206;headers['Content-Range']='bytes '+start+'-'+end+'/'+size;
 }
 headers['Content-Length']=end-start+1;res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return;}
 const stream=createReadStream(file[0],{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
});
server.listen(8790,'127.0.0.1',()=>console.log('Local film: http://127.0.0.1:8790/watch'));
