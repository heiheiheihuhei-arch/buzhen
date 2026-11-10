const sleep=ms=>new Promise(r=>setTimeout(r,ms)); await sleep(2000);
const q=new URLSearchParams(location.search), hz=__hz; for (const k of ['p0','pG']) if (q.has(k)) hz.TUNE[k]=+q.get(k);
const draw=q.get('draw')==='1', to=+(q.get('to')||5), log=[];
hz.startPrep();
const fill=()=>{ for (const k of ['shield','spear','bow','horse']) { const rows=k==='bow'?[41,42,43,44]:k==='horse'?[46,47]:[33,34,35,38,39,40];
  for (const r of rows) for (let d=0; d<18 && countOf(k)<ownOf(k); d++) for (const c of [17-d,18+d]) if (countOf(k)<ownOf(k) && !grid[r*COLS+c] && drawable(c,r)) place(c,r,k); }
  recalcBuffs(); };
for (let w=1; w<=to; w++) {
  await sleep(200); if (draw) { for (let any = true; any; ) { any = false; for (const k of ['spear','shield','bow','spear','shield','horse']) if (buyTroops(k)) any = true; } fill(); }
  const army=sp.army, n0=hz.mine, foes=foesLeft(), junxin0=junxin;
  hz.startFight(); let t=0; while (hz.state==='fight' && t<120000) { await sleep(250); t+=250; }
  if (hz.state==='pick') { const g=document.querySelector('.grade').textContent, rw=document.querySelector('.reward').innerText.replace(/\n/g,' ');
    log.push(`波${w} ${army}${sp.big?'':'(同)'} 军心${junxin0} 我${n0} 敌${foes} 胜 ${g} ${rw.split('基础')[0]} ${t/1000}s`); document.getElementById('card0').click(); }
  else { log.push(`波${w} ${army} 我${n0} 敌${foes} ${hz.state==='over'?'败':'超时 剩'+enemies.length+' '+JSON.stringify(enemies.slice(0,3).map(e=>[e.kind,Math.round(e.x),Math.round(e.y)]))} ${t/1000}s`); break; }
}
log.push('errs:'+JSON.stringify(window.__errs||"未注入"));
return {'log.txt':'data:text/plain;base64,'+btoa(unescape(encodeURIComponent(log.join('\n')))), 'end.png':document.querySelector('canvas').toDataURL()};
