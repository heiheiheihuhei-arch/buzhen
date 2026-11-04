const sleep=ms=>new Promise(r=>setTimeout(r,ms)); await sleep(2500); const hz=__hz; hz.TUNE.hp=1.5; hz.TUNE.dmg=1.5; hz.setThick(false);
const out={}, log=[]; const shot=n=>out[n]=document.querySelector('canvas').toDataURL();
try{localStorage.clear();}catch(e){}
hz.startPrep(); await sleep(300);
const m0=hz.mine;
document.getElementById('fsave').click(); document.getElementById('f0').click();
log.push(`存阵: 场上${m0} 存了${forms[0]&&forms[0].length} 按钮=${document.getElementById('forms').textContent}`);
hz.setTool('erase'); for (let y=5;y<600;y+=10) for(let x=5;x<360;x+=10) hz.stamp(x,y);
log.push(`擦光后 ${hz.mine}`);
document.getElementById('f0').click(); await sleep(100);
log.push(`读阵后 ${hz.mine}`);
// 换兵种：在第36行盾上画枪
const sh0=soldiers.filter(s=>s.type==='shield').length, spOwn=T.spear.cap, spCnt=soldiers.filter(s=>s.type==='spear').length;
hz.setTool('spear'); for(let x=95;x<150;x+=10) hz.stamp(x,365);
log.push(`换兵: 盾 ${sh0}→${soldiers.filter(s=>s.type==='shield').length} 枪 ${spCnt}→${soldiers.filter(s=>s.type==='spear').length}/${spOwn}`);
// 框选平移
tool='move'; selDown({x:85,y:355}); selMove({x:275,y:395}); selUp();
const n=selSoldiers().length, before=soldiers.map(s=>s.r).reduce((a,b)=>a+b,0)/soldiers.length;
selDown({x:150,y:375}); selMove({x:150,y:455}); shot('drag.png'); selUp();
const after=soldiers.map(s=>s.r).reduce((a,b)=>a+b,0)/soldiers.length;
log.push(`框选 ${n} 个，平均行 ${before.toFixed(1)}→${after.toFixed(1)}，总数 ${hz.mine}`);
selDown({x:150,y:455}); selMove({x:150,y:5}); selUp(); log.push(`拖进出生区: 平均行 ${(soldiers.map(s=>s.r).reduce((a,b)=>a+b,0)/soldiers.length).toFixed(1)}`);
await sleep(300); shot('moved.png');
// 大波小波
const seq=[`1 ${sp.army} big=${sp.big}`];
for(let k=0;k<9;k++){ hz.startPrep(); seq.push(`${wave} ${sp.army} ${sp.big?'变':'同'} ${sp.groups.map(g=>g.d+Math.round(g.ax)+','+Math.round(g.ay)+g.form).join(' ')} 敌${foesLeft()} ${sp.mods.map(m=>m.name)}`); }
log.push(...seq); log.push('intel: '+document.getElementById('intel').textContent.slice(0,80));
shot('w10.png');
log.push('errs:'+JSON.stringify(window.__errs||"未注入"));
out['log.txt']='data:text/plain;base64,' + btoa(unescape(encodeURIComponent(log.join('\n'))));
return out;
