// Actual CDP screencast: native timestamps; real local input/save/reopen.
const fs=require('node:fs'), path=require('node:path');
const WS=require('D:/电脑面试/node_modules/ws');
const root=path.resolve(__dirname,'../../..');
const take=process.argv[2]||'ui';
if(!/^ui(?:-v[0-9]+)?$/.test(take))throw Error('Invalid take');
const out=path.join(root,'.data/short-drama-49',take);
const frames=[], events=[], pending=new Map();
const text='观察：试了三次，没找到入口。\n取舍：去掉欢迎页，入口放到第一屏。\n复测：一次就找到了。';
const q='document.querySelector('+JSON.stringify('textarea[placeholder="说明哪些模块由你负责、哪些由团队负责"]')+')';
let id=0,ws,start;
let capturing=false, captureLoop;
const screenshotMode=/^ui-v[3-9]/.test(take);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const c=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
async function evaluate(expression){const r=await c('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
function mark(name,data={}){events.push({t:(Date.now()-start)/1000,name,...data})}
async function click(x,y){await c('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});await c('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await c('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1})}
async function button(name){await evaluate(`(()=>{const e=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()===${JSON.stringify(name)});if(!e)throw Error('button missing');e.click();return true})()`)}
async function waitFor(expression){for(let n=0;n<100;n++){if(await evaluate(expression))return;await sleep(100)}throw Error('Timed out waiting for product UI')}
async function main(){
  if(fs.existsSync(path.join(out,'capture.json')))throw Error('Preserve existing take; use a new directory');
  fs.mkdirSync(path.join(out,'frames'),{recursive:true});
  const targets=await(await fetch('http://127.0.0.1:9349/json/list')).json();
  const target=targets.find(t=>t.url.includes('/apps/desktop/out/renderer/'));
  if(!target)throw Error('real renderer missing');
  ws=new WS(target.webSocketDebuggerUrl);await new Promise(r=>ws.once('open',r));
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}
    if(m.method==='Page.screencastFrame'){const p=m.params;const file=path.join(out,'frames',String(frames.length).padStart(5,'0')+'.jpg');fs.writeFileSync(file,Buffer.from(p.data,'base64'));frames.push({file,timestamp:p.metadata.timestamp,wall:(Date.now()-start)/1000});c('Page.screencastFrameAck',{sessionId:p.sessionId}).catch(()=>{});}});
  try{
    await c('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:2,mobile:false});
    await c('Emulation.setFocusEmulationEnabled',{enabled:true});
    const field=await evaluate(`(()=>{if(!document.body.innerText.includes('上传入口 · 虚构项目练习'))throw Error('synthetic project missing');const e=${q};if(!e)throw Error('note missing');const r=e.getBoundingClientRect();return {x:r.x+30,y:r.y+20}})()`);
    start=Date.now();
    if(screenshotMode){
      capturing=true;
      captureLoop=(async()=>{while(capturing){
        const began=Date.now();
        const p=await c('Page.captureScreenshot',{format:'jpeg',quality:96,captureBeyondViewport:false});
        const file=path.join(out,'frames',String(frames.length).padStart(5,'0')+'.jpg');
        fs.writeFileSync(file,Buffer.from(p.data,'base64'));
        frames.push({file,timestamp:began/1000,wall:(began-start)/1000});
        await sleep(Math.max(1,100-(Date.now()-began)));
      }})();
    }else await c('Page.startScreencast',{format:'jpeg',quality:96,maxWidth:2560,maxHeight:1440,everyNthFrame:1});
    await sleep(600);await evaluate(q+'.focus()');
    await c('Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
    await c('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
    mark('typing_start');
    for(const char of [...text]){await c('Input.insertText',{text:char});await sleep(char==='\n'?240:66)}
    mark('typing_end');await sleep(600);await button('保存设置');mark('save');await waitFor('!'+q);await sleep(500);await button('项目设置');await waitFor('!!'+q);await sleep(700);
    const saved=await evaluate(q+'.value');if(saved!==text)throw Error('persisted value mismatch');
    const ownership=await evaluate('document.querySelector("select").value');if(ownership!=='partial')throw Error('Ownership not partial');mark('saved_verified',{ownership});
    await evaluate(`(()=>{const e=${q};e.focus();e.setSelectionRange(0,0);return true})()`);await sleep(800);
    let offset=0;
    for(const [index,line] of text.split('\n').entries()){
      await evaluate(`(()=>{const e=${q};e.focus();e.setSelectionRange(${offset},${offset+line.length});return true})()`);
      mark('recall_line_'+(index+1));await sleep(3800);offset+=line.length+1;
    }
    await evaluate(q+'.setSelectionRange(0,0)');await sleep(1500);mark('end');
  }finally{
    if(screenshotMode){capturing=false;await captureLoop;}else await c('Page.stopScreencast');
    await sleep(300);
    fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify({target:target.url,viewport:[1280,720],device_scale:2,focus_emulation:true,capture_method:screenshotMode?'CDP captureScreenshot, measured wall timestamps, up to 10Hz; native high-DPI UI, not generated motion':'CDP Page.startScreencast, native timestamps',note:text,duration:(Date.now()-start)/1000,frames,events},null,2));
    console.log(JSON.stringify({frames:frames.length,events}));ws.close();
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;ws?.close()});
