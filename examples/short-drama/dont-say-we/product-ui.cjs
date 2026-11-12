// Read/operate only the fresh, network-blocked renderer from capture-launch.cjs.
const fs = require('node:fs');
const path = require('node:path');
const WS = require('D:/电脑面试/node_modules/ws');
const out = path.resolve(__dirname, '../../../.data/short-drama-49/ui');
fs.mkdirSync(out, {recursive:true});
async function main() {
  const targets = await (await fetch('http://127.0.0.1:9349/json/list')).json();
  const target = targets.find(t=>t.url.includes('/apps/desktop/out/renderer/'));
  if(!target) throw Error('Real product renderer not found');
  const ws = new WS(target.webSocketDebuggerUrl);
  await new Promise(r=>ws.once('open',r));
  let next=0; const pending=new Map();
  ws.on('message', raw=>{const m=JSON.parse(raw); if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}});
  const c=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++next,{resolve,reject});ws.send(JSON.stringify({id:next,method,params}))});
  try {
    await c('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:2,mobile:false});
    if(process.argv[2]) {
      const r=await c('Runtime.evaluate',{expression:process.argv[2],returnByValue:true,awaitPromise:true});
      if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));
      console.log(JSON.stringify(r.result.value));
    }
    if(process.argv[3]) await c('Input.insertText', {text:process.argv[3]});
    const r=await c('Runtime.evaluate',{expression:'document.body.innerText',returnByValue:true});
    console.log(r.result.value);
    const shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join(out,'latest.png'),Buffer.from(shot.data,'base64'));
  } finally {ws.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
