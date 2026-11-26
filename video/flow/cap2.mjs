
import { writeFileSync, mkdirSync } from 'node:fs';
import { spawn } from 'node:child_process';
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const OUT = 'C:/dev/cti-platform/video/flow/frames';
mkdirSync(OUT, { recursive: true });
const PORT = 9410;
console.log('launching edge');
spawn(EDGE, ['--headless=new','--disable-gpu','--no-sandbox','--no-first-run','--disable-crash-reporter','--hide-scrollbars','--force-device-scale-factor=1','--window-size=1600,1000','--user-data-dir=C:/dev/cti-platform/video/flow/.edge2','--remote-debugging-port='+PORT,'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function targetWs(){
  for(let i=0;i<60;i++){
    try{ const r=await fetch('http://127.0.0.1:'+PORT+'/json/list'); const l=await r.json(); const p=l.find(t=>t.type==='page'); if(p) { console.log('target ok', i); return p.webSocketDebuggerUrl; } }catch(e){ if(i%10===0) console.log('wait target', i, String(e.message).slice(0,40)); }
    await sleep(500);
  }
  throw new Error('no target');
}
const ws = new WebSocket(await targetWs());
await new Promise((res,rej)=>{ws.addEventListener('open',res);ws.addEventListener('error',rej);});
console.log('ws open');
let id=0; const pending=new Map();
ws.addEventListener('message',(ev)=>{const m=JSON.parse(ev.data); if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}});
const send=(method,params={})=>new Promise((res)=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async(e)=>{const r=await send('Runtime.evaluate',{expression:e,awaitPromise:true,returnByValue:true}); return r.result&&r.result.result?r.result.result.value:null;};
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
console.log('navigate');
await send('Page.navigate',{url:'https://cti-risk-platform.onrender.com/'});
let awake = false;
for (let i=0;i<120;i++){
  await sleep(1000);
  const t = await ev("document.title");
  if (i%10===0) console.log('wait wake', i, String(t).slice(0,40));
  const ok = await ev("!!document.querySelector('[data-tab=\"overview\"]')");
  if (ok) { awake = true; console.log('awake at', i); break; }
}
console.log('awake final', awake);
await sleep(2500);
let n = 0;
async function frames(k, gap=90){
  for (let i=0;i<k;i++){
    const r = await send('Page.captureScreenshot',{format:'jpeg',quality:92});
    writeFileSync(OUT + '/' + String(n).padStart(4,'0') + '.jpg', Buffer.from(r.result.data,'base64'));
    n++; await sleep(gap);
  }
  console.log('captured', n);
}
await frames(10);
await ev("document.querySelector('[data-tab=\"assess\"]').click()");
await frames(12);
console.log('score before', await ev("(() => !!document.querySelector('#cveId'))()"));
await ev("(() => { const e=document.querySelector('#cveId'); e.focus(); e.value=''; e.dispatchEvent(new Event('input',{bubbles:true})); return 1; })()");
for (const ch of 'CVE-2024-3400') {
  await ev("(() => { const e=document.querySelector('#cveId'); e.value += " + JSON.stringify(ch) + "; e.dispatchEvent(new Event('input',{bubbles:true})); return 1; })()");
  await frames(1, 60);
}
await frames(5);
await ev("(() => { const s=document.querySelector('#exposure'); const o=[...s.options].find(x=>x.textContent.includes('公開')); if(!o) return 'noopt'; s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return 'ok'; })()");
await frames(8);
await ev("(() => { const e=document.querySelector('#cvss'); e.value='10'; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return 'ok'; })()");
await frames(8);
await ev("(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('EDR 端點偵測')); if(b) b.click(); return b?'ok':'nobtn'; })()");
await frames(6);
await ev("(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('執行風險評估')); if(b) b.click(); return b?'ok':'nobtn'; })()");
await frames(36, 100);
const score = await ev("(() => { const t=document.body.innerText.replace(/\\s+/g,' '); const m=t.match(/評估結果(.{0,100})/); return m?m[1]:'?'; })()");
console.log('SCORE:', String(score).slice(0,120));
console.log('DONE frames', n);
await send('Browser.close');
