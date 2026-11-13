import http from 'node:http';
import {createReadStream,existsSync,readFileSync,statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const pack=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(pack,'../../../..'),out=path.join(root,'.data/short-drama-53/v4');
const files=new Map([
 ['/film.mp4',[path.join(out,'你来试试-v4-超分成片.mp4'),'video/mp4']],
 ['/baseline.mp4',[path.join(out,'你来试试-v4-超分前对照.mp4'),'video/mp4']],
 ['/production.zip',[path.join(out,'你来试试-v4-制作包.zip'),'application/zip']],
 ['/subtitles.srt',[path.join(out,'你来试试-v4.srt'),'application/x-subrip']],
 ['/trial.mp4',[path.join(out,'takes/S04-audio-driven-v1.mp4'),'video/mp4']],
 ['/chen.wav',[path.join(out,'voices/chen-master-v2.wav'),'audio/wav']],
 ['/lin.wav',[path.join(out,'voices/lin-master-v2.wav'),'audio/wav']],
 ['/poster.png',[path.join(pack,'../v3/assets/s04-close-v3.png'),'image/png']],
]);
for(const name of ['lin-three-view-v1','chen-three-view-v1','scene-empty-v1','s02-close-v3','s03-hands-v3','s04-close-v3','s06-close-v3'])files.set('/'+name+'.png',[path.join(pack,'../v3/assets',name+'.png'),'image/png']);
function ready(){
 try{
  const proof=JSON.parse(readFileSync(path.join(pack,'validation.json'),'utf8'));
  const manifest=JSON.parse(readFileSync(path.join(pack,'edit-manifest.json'),'utf8'));
  const hash=createHash('sha256').update(readFileSync(path.join(pack,'edit.json'))).digest('hex');
  return proof.status==='technical_checks_passed'&&proof.edit_sha256===hash&&manifest.edit_sha256===hash&&manifest.outputs.length===2&&
   manifest.outputs.every(o=>existsSync(path.join(root,o.path))&&statSync(path.join(root,o.path)).size===o.bytes&&proof.outputs.some(p=>p.sha256===o.sha256));
 }catch{return false;}
}
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>你来试试 · 修订4</title><style>
*{box-sizing:border-box}body{margin:0;background:#171b18;color:#f0ede3;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1080px;margin:auto;padding:28px}h1{font-size:36px;margin:6px 0}p{color:#bac3b4}video{width:100%;max-height:69vh;aspect-ratio:16/9;background:#050705;border-radius:8px}audio{width:100%;max-width:430px}a,button{display:inline-block;color:#edf2e4;background:transparent;border:1px solid #657359;border-radius:6px;padding:9px 14px;text-decoration:none;margin:8px 8px 8px 0;font:inherit;cursor:pointer}.primary{background:#d7e6bd;color:#1b2716;border-color:#d7e6bd}button[aria-pressed="true"]{border-color:#d7e6bd;background:#2d3c25}section{display:grid;grid-template-columns:1fr 1fr;gap:20px}.note,small{font-size:13px;color:#99a68f}details{border-top:1px solid #35432e;padding:14px 0}summary{cursor:pointer}.refs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.refs img{width:100%;display:block}figure{margin:0}figcaption{font-size:13px;color:#b7c2ac}@media(max-width:650px){main{padding:18px}h1{font-size:28px}section{grid-template-columns:1fr}.refs{grid-template-columns:1fr 1fr}}</style>
<main><span class="note">有招 / AI短剧 · 修订4 · 18秒</span><h1>你来试试</h1><p>“不是你不会用，是我藏得太深了。”</p>
<video id="film" controls playsinline preload="metadata" poster="/poster.png" src="/film.mp4"></video>
<nav><button data-src="/film.mp4" aria-pressed="true">超分成片</button><button data-src="/baseline.mp4" aria-pressed="false">超分前对照</button><a class="primary" href="/film.mp4?download=1">保存成片</a><a href="/production.zip?download=1">完整制作包</a><a href="/subtitles.srt?download=1">字幕</a></nav>
<p class="note" id="version">当前：超分成片 · 1920×1080 / 24fps。AI虚构人物、合成声音与虚构练习数据，艺术质量待审。</p>
<details><summary>这次如何处理声音和表演</summary><p>每个角色固定一条连续声音母带；嘴部、表情和身体以同一音轨生成。对白之后没有再单独变速或挪动声音，也没有糊嘴覆盖。切镜后保持原对白时点。</p><p class="note">原生人物镜头832×480 / 16fps，逐镜插帧至24fps，实际神经x2超分后合成1080p；不是原生1080p。超分不能补回真实拍摄细节，也不能保证逐字口型准确。没有真人声音克隆。</p><section><div><p>陈 · 声音母带</p><audio controls preload="none" src="/chen.wav"></audio></div><div><p>小林 · 声音母带</p><audio controls preload="none" src="/lin.wav"></audio></div></section></details>
<details><summary>人物、场景与分镜资料</summary><p>故事：找不到入口 → 想放弃 → 设计者承认问题 → 拿掉欢迎页 → 重试成功 → 记录这次选择。真实有招界面出现在片尾，示例记录为虚构。</p><div class="refs">${[['lin-three-view-v1','小林 · 三视图'],['chen-three-view-v1','陈 · 三视图'],['scene-empty-v1','场景'],['s02-close-v3','叫停与承认问题'],['s03-hands-v3','操作与改动'],['s04-close-v3','重试与回应']].map(([n,t])=>`<figure><a href="/${n}.png?download=1"><img loading="lazy" src="/${n}.png" alt="${t}"></a><figcaption>${t}</figcaption></figure>`).join('')}</div><p class="note">完整剧本、提示词、生成回执、版本、失败尝试及原生片段均在制作包。技术检查通过不代表人工艺术审核通过。</p></details></main>
<script>const film=document.querySelector('#film');document.querySelectorAll('[data-src]').forEach(b=>b.onclick=()=>{film.pause();film.src=b.dataset.src;film.load();document.querySelectorAll('[data-src]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelector('#version').textContent='当前：'+b.textContent+' · 1920×1080 / 24fps。AI虚构人物、合成声音与虚构练习数据，艺术质量待审。';});document.querySelectorAll('video,audio').forEach(m=>m.addEventListener('play',()=>document.querySelectorAll('video,audio').forEach(other=>{if(other!==m)other.pause();})));</script></html>`;
http.createServer((req,res)=>{
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);res.end();return;}
 const u=new URL(req.url,'http://127.0.0.1:8792');
 if(u.pathname==='/'||u.pathname==='/watch'){
  const ok=ready();res.writeHead(ok?200:503,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:ok?html:'成片检查尚未完成，请稍后刷新。');return;
 }
 const item=files.get(u.pathname);if(!item||!existsSync(item[0])){res.writeHead(404);res.end();return;}
 if(['/film.mp4','/baseline.mp4','/production.zip','/subtitles.srt'].includes(u.pathname)&&!ready()){res.writeHead(503);res.end();return;}
 const size=statSync(item[0]).size;let start=0,end=size-1,status=200;const headers={'Content-Type':item[1],'Accept-Ranges':'bytes','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'};
 if(u.searchParams.has('download'))headers['Content-Disposition']="attachment; filename*=UTF-8''"+encodeURIComponent(path.basename(item[0]));
 if(req.headers.range){const m=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);if(!m||(!m[1]&&!m[2])){res.writeHead(416);res.end();return;}if(!m[1])start=Math.max(0,size-Number(m[2]));else{start=Number(m[1]);if(m[2])end=Math.min(end,Number(m[2]));}if(start>end||start>=size||!Number.isSafeInteger(start)||!Number.isSafeInteger(end)){res.writeHead(416,{'Content-Range':'bytes */'+size});res.end();return;}status=206;headers['Content-Range']='bytes '+start+'-'+end+'/'+size;}
 headers['Content-Length']=end-start+1;res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return;}const stream=createReadStream(item[0],{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
}).listen(8792,'127.0.0.1',()=>console.log('Audio-led film: http://127.0.0.1:8792/watch'));
