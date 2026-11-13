import http from 'node:http';
import {createReadStream,existsSync,statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const pack=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(pack,'../../../..'),out=path.join(root,'.data/short-drama-53');
const files=new Map([
 ['/film.mp4',[path.join(out,'你来试试-v3-1080p.mp4'),'video/mp4']],
 ['/sr.mp4',[path.join(out,'你来试试-v3-2K超分.mp4'),'video/mp4']],
 ['/native.mp4',[path.join(out,'你来试试-v3-原片对照.mp4'),'video/mp4']],
 ['/production.zip',[path.join(out,'你来试试-v3-制作包.zip'),'application/zip']],
 ['/subtitles.srt',[path.join(out,'你来试试.srt'),'text/plain; charset=utf-8']],
 ['/script.md',[path.join(pack,'剧本与连续性.md'),'text/plain; charset=utf-8']],
 ['/prompts.json',[path.join(pack,'production.json'),'application/json; charset=utf-8']],
]);
const assets=[['lin-three-view-v1','小林 · 人物三视图'],['chen-three-view-v1','陈 · 人物三视图'],['scene-empty-v1','工作室 · 空场景'],['s02-close-v3','02 · 停手'],['s03-hands-v3','03 · 修改'],['s04-close-v3','04 · 重试'],['s06-close-v3','05 · 回应']];
for(const [id] of assets)files.set('/'+id+'.png',[path.join(pack,'assets',id+'.png'),'image/png']);
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>你来试试 · 短剧制作版</title><style>
*{box-sizing:border-box}body{margin:0;background:#191d18;color:#eeece1;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1120px;margin:auto;padding:24px 24px 64px}.brand{font-size:12px;letter-spacing:.12em;color:#a6b39c}h1{font-size:38px;margin:8px 0 0}p{color:#bbc1b1;margin:8px 0}video{display:block;width:100%;aspect-ratio:16/9;background:#050705;margin:18px 0;border-radius:8px}nav{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}button,a{font:inherit;color:#e9eadf;background:#303d29;border:1px solid #59674c;border-radius:6px;padding:8px 14px;text-decoration:none;cursor:pointer}button[aria-pressed=true]{background:#e1e8d4;color:#26351d}.muted{font-size:13px;color:#929f86}details{margin-top:26px}summary{cursor:pointer}section{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}figure{margin:0}figure img{width:100%;display:block;border-radius:6px}figcaption{padding:6px 0;color:#b8c4ad;font-size:13px}@media(max-width:650px){section{grid-template-columns:1fr}h1{font-size:30px}main{padding:16px}}
</style><main><div class="brand">有招 / 原创微短剧 · 制作修订3</div><h1>你来试试</h1><p>他把手机递过来，她却没有接。</p><video id="film" controls playsinline preload="metadata" poster="/s04-close-v3.png" src="/film.mp4"></video><nav aria-label="画质对照"><button data-src="/film.mp4" aria-pressed="true">1080p 成片</button><button data-src="/sr.mp4" aria-pressed="false">2K 超分版</button><button data-src="/native.mp4" aria-pressed="false">超分前对照</button></nav><nav><a href="/sr.mp4?download=1">保存2K视频</a><a href="/film.mp4?download=1">保存1080p视频</a><a href="/production.zip?download=1">完整制作包</a><a href="/subtitles.srt?download=1">字幕</a></nav><p class="muted">22秒 · AI剧情演绎 · 合成声音 · 虚构项目 · 待你审看</p><details><summary>查看剧本、人物、场景与分镜资料</summary><p class="muted">动态原片1280×704；神经x2得到2560×1408，再加上下留边形成2K画幅。对照版仅常规放大。字幕与真实项目备注最后合成，未经神经重绘。超分不保证人物细节或表演正确。</p><nav><a href="/script.md?download=1">剧本与连续性</a><a href="/prompts.json?download=1">逐镜动作提示词</a></nav><section>${assets.map(([id,label])=>'<figure><a href="/'+id+'.png"><img loading="lazy" src="/'+id+'.png" alt="'+label+'"></a><figcaption>'+label+'</figcaption></figure>').join('')}</section></details></main><script>
const v=document.querySelector('video');document.querySelectorAll('button[data-src]').forEach(b=>b.onclick=()=>{const t=v.currentTime,playing=!v.paused;document.querySelectorAll('button[data-src]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));v.src=b.dataset.src;v.addEventListener('loadedmetadata',()=>{v.currentTime=Math.min(t,v.duration);if(playing)v.play().catch(()=>{});},{once:true});v.load();});
</script></html>`;
http.createServer((req,res)=>{
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'});res.end();return;}
 const u=new URL(req.url,'http://127.0.0.1:8791');
 if(u.pathname==='/'||u.pathname==='/watch'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:html);return;}
 const item=files.get(u.pathname);if(!item||!existsSync(item[0])){res.writeHead(404);res.end('文件尚未完成');return;}
 const size=statSync(item[0]).size;let start=0,end=size-1,status=200;const headers={'Content-Type':item[1],'Accept-Ranges':'bytes','X-Content-Type-Options':'nosniff','Cache-Control':'no-cache'};
 if(u.searchParams.has('download'))headers['Content-Disposition']="attachment; filename*=UTF-8''"+encodeURIComponent(path.basename(item[0]));
 if(req.headers.range){const m=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);if(!m||(!m[1]&&!m[2])){res.writeHead(416,{'Content-Range':'bytes */'+size});res.end();return;}if(!m[1])start=Math.max(0,size-Number(m[2]));else{start=Number(m[1]);if(m[2])end=Math.min(end,Number(m[2]));}if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=size){res.writeHead(416,{'Content-Range':'bytes */'+size});res.end();return;}status=206;headers['Content-Range']='bytes '+start+'-'+end+'/'+size;}
 headers['Content-Length']=end-start+1;res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return;}const ranged=createReadStream(item[0],{start,end});ranged.on('error',()=>res.destroy());res.on('close',()=>ranged.destroy());ranged.pipe(res);
}).listen(8791,'127.0.0.1',()=>console.log('Review: http://127.0.0.1:8791/watch'));
