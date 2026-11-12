// Local film viewing only. No platform upload or publishing implementation.
import http from 'node:http';
import {createReadStream, existsSync, statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const pack=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(pack,'../../../.data/short-drama-49');
const files=new Map([
  ['/film.mp4',[path.join(out,'别说我们-v2.mp4'),'video/mp4','别说我们.mp4']],
  ['/subtitles.srt',[path.join(out,'别说我们.srt'),'text/plain; charset=utf-8','别说我们.srt']],
  ['/production.zip',[path.join(out,'别说我们-完整制作包-v2.zip'),'application/zip','别说我们-完整制作包.zip']],
  ['/poster.png',[path.join(pack,'assets/s01-opening-v1.png'),'image/png']],
]);
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>别说“我们” · 有招原创短剧</title><style>
*{box-sizing:border-box}body{margin:0;background:#111918;color:#edf0e9;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1160px;margin:auto;padding:40px 28px 70px}.brand{color:#a6bbaa;font-size:13px;letter-spacing:.12em}h1{font-size:clamp(32px,5vw,58px);line-height:1.3;margin:14px 0}p{max-width:740px;color:#b4c2b9}.meta{font-size:14px;color:#91aa9a}video{display:block;width:100%;aspect-ratio:16/9;background:#070c0b;border-radius:12px;margin:26px 0 20px;box-shadow:0 18px 65px #0005}nav{display:flex;gap:12px;flex-wrap:wrap}a{color:#e7efe6;text-decoration:none;border:1px solid #476352;border-radius:7px;padding:9px 18px}a:first-child{background:#dfebd9;color:#163926;border-color:transparent}a:hover{filter:brightness(1.13)}details{margin-top:28px;color:#91a597;font-size:13px}summary{cursor:pointer}.notice{font-size:12px;color:#91a597;margin-top:24px}.status{color:#c1d7c4}
</style><main><div class="brand">有招 / 原创短剧 01</div><h1>别说“我们”</h1><div class="meta">41 秒 · 真人风格 · 中文双声线</div><p>她以为，自己只改过一个小按钮。直到那个问题再次响起：“那为什么改？”</p><video id="film" controls playsinline preload="metadata" poster="/poster.png"><source src="/film.mp4" type="video/mp4"></video><nav><a href="/film.mp4?download=1" download="别说我们.mp4">保存视频</a><a href="/subtitles.srt?download=1" download>下载字幕</a><a href="/production.zip?download=1" download>完整制作包</a></nav><p id="status" class="status" aria-live="polite"></p><details><summary>制作信息</summary><p>AI 动态人物镜头、真实有招项目备注画面、合成配音与原创程序音乐。女主台词为心声，面试官为画外声音。人物、项目改动和测试次数均为虚构。</p><p>成片 1920×1080 / 30fps；动态源片 1280×704 / 24fps，经剪辑变速和补帧后合成。高清界面原始采集为 2560×1440。成片待你审看，不代表商业发行审核通过。</p></details><p class="notice">AI 剧情演绎 · 合成声音 · 虚构项目练习</p></main><script>const v=document.querySelector('video');v.addEventListener('ended',()=>{document.querySelector('#status').textContent='已播放完毕，可以保存视频。'});v.addEventListener('error',()=>{document.querySelector('#status').textContent='文件暂不可读取，请稍后刷新。'});</script></html>`;
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://127.0.0.1:8785');
  if(url.pathname==='/'||url.pathname==='/watch'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:html);return;}
  const file=files.get(url.pathname);
  if(!file||!existsSync(file[0])){res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});res.end('文件尚未生成');return;}
  const size=statSync(file[0]).size;let start=0,end=size-1,status=200;
  const headers={'Content-Type':file[1],'Accept-Ranges':'bytes','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'};
  if(url.searchParams.has('download'))headers['Content-Disposition']="attachment; filename*=UTF-8''"+encodeURIComponent(file[2]||path.basename(file[0]));
  if(req.headers.range){
    const m=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
    if(!m||(!m[1]&&!m[2])){res.writeHead(416,{'Content-Range':`bytes */${size}`});res.end();return;}
    if(!m[1])start=Math.max(0,size-Number(m[2]));else {start=Number(m[1]);if(m[2])end=Math.min(end,Number(m[2]));}
    if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=size){res.writeHead(416,{'Content-Range':`bytes */${size}`});res.end();return;}
    status=206;headers['Content-Range']=`bytes ${start}-${end}/${size}`;
  }
  headers['Content-Length']=end-start+1;res.writeHead(status,headers);
  if(req.method==='HEAD'){res.end();return;}
  const stream=createReadStream(file[0],{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
});
server.listen(8785,'127.0.0.1',()=>console.log('Local film: http://127.0.0.1:8785/watch'));
