// Isolated real Electron renderer. No recreated interface or fake AI result.
const fs=require('node:fs'), path=require('node:path'), WS=require('D:/电脑面试/node_modules/ws');
const out=path.resolve('.data/有招剧情制作-20261108'), frames=[], events=[], pending=new Map();
let id=0,ws,start; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function command(method,params={}){return new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
function mark(name,data={}){events.push({t:(Date.now()-start)/1000,name,...data})}
async function move(from,to,duration=650){const steps=Math.ceil(duration/16);for(let n=1;n<=steps;n++){const t=n/steps,u=t*t*(3-2*t);await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:from.x+(to.x-from.x)*u,y:from.y+(to.y-from.y)*u});await sleep(duration/steps)}}
async function click(p){await command('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});await command('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1})}
(async()=>{
 const targets=await(await fetch('http://127.0.0.1:9349/json/list')).json();const target=targets.find(t=>t.url.includes('/apps/desktop/out/renderer/'));if(!target)throw Error('isolated real renderer missing');
 ws=new WS(target.webSocketDebuggerUrl);await new Promise(r=>ws.once('open',r));
 const frameDir=path.join(out,'ui-frames-v1');fs.mkdirSync(frameDir,{recursive:true});
 ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}
 if(m.method==='Page.screencastFrame'){const p=m.params;const file=path.join(frameDir,String(frames.length).padStart(5,'0')+'.jpg');fs.writeFileSync(file,Buffer.from(p.data,'base64'));frames.push({file,timestamp:p.metadata.timestamp,wall:(Date.now()-start)/1000});command('Page.screencastFrameAck',{sessionId:p.sessionId}).catch(()=>{});}});
 await command('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
 const field=await evaluate(`(()=>{if(!document.body.innerText.includes('团队知识库 · 示例'))throw Error('synthetic project not selected');const e=document.querySelector('textarea[placeholder="可记录项目范围或复习备注"]');if(!e)throw Error('actual note field missing');const r=e.getBoundingClientRect();return {x:r.x+110,y:r.y+40}})()`);
 // A visible editorial pointer is the only overlay; product controls and content stay real.
 await evaluate(`(()=>{const e=document.createElement('div');e.id='editorial-pointer-39';e.style.cssText='position:fixed;left:0;top:0;width:18px;height:22px;background:#111;clip-path:polygon(0 0,0 100%,30% 73%,55% 100%,70% 90%,46% 62%,90% 62%);filter:drop-shadow(0 0 1px white);pointer-events:none;z-index:2147483647;';document.body.append(e);window.__pointer39=ev=>{e.style.transform='translate('+ev.clientX+'px,'+ev.clientY+'px)'};document.addEventListener('pointermove',window.__pointer39);return true})()`);
 start=Date.now();await command('Page.startScreencast',{format:'jpeg',quality:96,maxWidth:1920,maxHeight:1080,everyNthFrame:1});
 try{
 await move({x:1100,y:850},field);await click(field);mark('focus_note',field);
 await command('Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});await command('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
 const text='演示练习：团队知识库\n我负责：文档列表与筛选\n当时怎么选：从全量改成分批加载\n怎样验证：对比加载时间和滚动体验';mark('typing_start');
 for(const char of [...text]){await command('Input.insertText',{text:char});await sleep(char==='\n'?270:76)}
 mark('typing_end');await sleep(1600);
 const save=await evaluate(`(()=>{const e=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()==='保存设置');const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
 await move(field,save,700);mark('click_save',save);await click(save);await sleep(1800);
 const reopened=await evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()==='项目设置');if(!b)throw Error('drawer did not close');b.click();return true})()`);await sleep(800);
 const saved=await evaluate(`document.querySelector('textarea[placeholder="可记录项目范围或复习备注"]').value`);if(saved!==text)throw Error('saved note mismatch');mark('saved_value_verified');
 await sleep(1800);mark('end');
 }finally{
 await command('Page.stopScreencast');await sleep(300);
 await evaluate(`(()=>{document.removeEventListener('pointermove',window.__pointer39);document.getElementById('editorial-pointer-39')?.remove();return true})()`);
 const manifest={target:target.url,source_commit:'521e1f479c02fc4f00992ef5bcd128ff7fba77cf',viewport:[1920,1080],capture_method:'CDP Page.startScreencast; native timestamps; not interval screenshots',overlay:'editorial pointer only',duration:(Date.now()-start)/1000,frames,events};fs.writeFileSync(path.join(out,'ui-pickup-v1.json'),JSON.stringify(manifest,null,2));
 console.log(JSON.stringify({frames:frames.length,duration:manifest.duration,events}));ws.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;ws?.close()});
