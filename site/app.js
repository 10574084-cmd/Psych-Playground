(() => {
"use strict";
const RAW="https://raw.githubusercontent.com/ShadowMario/FNF-PsychEngine/0.7.3/assets/shared";
const BF={id:"psych:bf",name:"Boyfriend",jsonUrl:RAW+"/characters/bf.json",imageUrl:RAW+"/images/characters/BOYFRIEND.png",xmlUrl:RAW+"/images/characters/BOYFRIEND.xml"};
const $=id=>document.getElementById(id);
const S={screen:"home",mods:[],chars:[BF],preview:null,cache:new Map(),smooth:true};
const screens={home:$("home"),play:$("game"),options:$("settings"),mods:$("modsScreen")};
function toast(msg){const t=$("toast");t.textContent=msg;t.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove("show"),2500)}
function show(name){
  if(name!=="play" && $("psychEngineFrame")) $("psychEngineFrame").src="about:blank";
  S.screen=name;
  Object.keys(screens).forEach(k=>screens[k].classList.toggle("hidden",k!==name));
  if(name==="play") $("psychEngineFrame").src="./engine/index.html";
  if(name==="mods") renderMods();
}
async function text(url){const r=await fetch(url);if(!r.ok)throw Error("Asset HTTP "+r.status);return r.text()}
function atlas(xml){
  const d=new DOMParser().parseFromString(xml,"application/xml");
  if(d.querySelector("parsererror"))throw Error("Atlas XML inválido");
  return [...d.querySelectorAll("SubTexture")].map(n=>{
    const g=(k,v=0)=>Number(n.getAttribute(k)??v);
    return {name:n.getAttribute("name")||"",x:g("x"),y:g("y"),w:g("width"),h:g("height"),fx:g("frameX"),fy:g("frameY"),fw:g("frameWidth",g("width")),fh:g("frameHeight",g("height"))};
  });
}
function makeActor(char){
  if(S.cache.has(char.id))return S.cache.get(char.id);
  const task=(async()=>{
    const data=JSON.parse(char.jsonUrl?await text(char.jsonUrl):char.jsonText);
    const xml=char.xmlText??await text(char.xmlUrl);
    const frames=atlas(xml),img=new Image();
    img.crossOrigin="anonymous";img.src=char.imageUrl;
    await new Promise((ok,no)=>{img.onload=ok;img.onerror=()=>no(Error("No se pudo cargar el spritesheet de "+char.name))});
    const anim={};
    (data.animations||[]).forEach(a=>{
      let f=frames.filter(x=>x.name.startsWith(a.name||""));
      if(a.indices&&a.indices.length)f=a.indices.map(i=>f[i]).filter(Boolean);
      if(f.length)anim[a.anim]={f,fps:+a.fps||24,loop:!!a.loop};
    });
    return {data,img,anim,current:"idle",start:performance.now(),until:0,
      play(n){this.current=anim[n]?n:"idle";this.start=performance.now();this.until=this.current==="idle"?0:this.start+Math.max(420,anim[this.current].f.length*1000/anim[this.current].fps)},
      draw(ctx,x,ground,scale,flip){
        const now=performance.now();
        if(this.current!=="idle"&&this.until&&now>this.until)this.play("idle");
        const a=anim[this.current]||anim.idle||Object.values(anim)[0];if(!a)return;
        let i=Math.floor((now-this.start)/(1000/a.fps));i=a.loop||this.current==="idle"?i%a.f.length:Math.min(i,a.f.length-1);
        const f=a.f[i]||a.f[0],s=scale*(+data.scale||1),w=f.fw*s,h=f.fh*s;
        ctx.save();ctx.imageSmoothingEnabled=S.smooth;if(flip){ctx.translate(2*x,0);ctx.scale(-1,1)}
        ctx.drawImage(img,f.x,f.y,f.w,f.h,x-w/2+f.fx*s,ground-h+f.fy*s,f.w*s,f.h*s);ctx.restore();
      }
    };
  })();
  S.cache.set(char.id,task);task.catch(()=>S.cache.delete(char.id));return task;
}
function background(ctx,w,h){
  const g=ctx.createLinearGradient(0,0,0,h);g.addColorStop(0,"#202438");g.addColorStop(.62,"#252a40");g.addColorStop(.621,"#191c27");g.addColorStop(1,"#11131b");
  ctx.fillStyle=g;ctx.fillRect(0,0,w,h);ctx.strokeStyle="#ffffff22";ctx.beginPath();ctx.moveTo(0,h*.72);ctx.lineTo(w,h*.72);ctx.stroke();
}
function render(){
  if(S.screen==="home"){
    const c=$("preview"),ctx=c.getContext("2d");background(ctx,c.width,c.height);
    S.preview?.draw(ctx,c.width*.54,c.height*.88,1,true);
  }
  requestAnimationFrame(render);
}
function suffixFile(zip,image,ext){
  const base=image.replace(/^\/+ /,"").replace(/\.(png|xml)$/i,"");
  const paths=Object.keys(zip.files).filter(p=>!zip.files[p].dir);
  return paths.find(p=>p.toLowerCase().endsWith(("/images/"+base+"."+ext).toLowerCase()))||paths.find(p=>p.toLowerCase().endsWith("/"+base.split("/").pop().toLowerCase()+"."+ext));
}
async function importZip(file){
  if(!window.JSZip)throw Error("JSZip no cargó. Recarga e inténtalo de nuevo.");
  const zip=await JSZip.loadAsync(file),paths=Object.keys(zip.files).filter(p=>!zip.files[p].dir);
  const jsons=paths.filter(p=>/(^|\/)characters\/[^/]+\.json$/i.test(p)),found=[];
  for(const p of jsons){
    try{
      const jsonText=await zip.file(p).async("text"),d=JSON.parse(jsonText);
      if(!d.image||!Array.isArray(d.animations))continue;
      const png=suffixFile(zip,d.image,"png"),xml=suffixFile(zip,d.image,"xml");
      if(!png||!xml)continue;
      const blob=await zip.file(png).async("blob"),xmlText=await zip.file(xml).async("text");
      found.push({id:"mod:"+file.name+":"+p,name:d.displayName||d.name||p.split("/").pop().replace(/\.json$/i,""),source:file.name,jsonText,imageUrl:URL.createObjectURL(blob),xmlText});
    }catch(err){console.warn("Skipped character",p,err)}
  }
  if(!found.length)throw Error("No encontré personajes compatibles. El ZIP debe incluir JSON de personaje, PNG y XML.");
  S.mods.push({id:String(Date.now())+Math.random(),name:file.name.replace(/\.zip$/i,""),fileName:file.name,chars:found});
  S.chars=[BF,...S.mods.flatMap(m=>m.chars)];renderMods();return found.length;
}
function renderMods(){
  $("modCount").textContent=S.mods.length;$("modTotal").textContent=S.mods.length+" MODS";$("charTotal").textContent=S.chars.length;$("modList").innerHTML="";
  if(!S.mods.length)$("modList").innerHTML='NO MODS LOADED <span>BF seguirá disponible en Psych Engine.</span>';
  S.mods.forEach(m=>{
    const row=document.createElement("div");row.className="mod-entry";
    const info=document.createElement("div");info.textContent=m.name;
    const sm=document.createElement("small");sm.textContent=m.chars.length+" character(s) · "+m.fileName;info.append(sm);
    const b=document.createElement("button");b.textContent="REMOVE";b.onclick=()=>removeMod(m.id);row.append(info,b);$("modList").append(row);
  });
  $("charList").innerHTML="";
  S.chars.forEach((c,i)=>{const chip=document.createElement("span");chip.className="chip";chip.textContent=c.name;const b=document.createElement("b");b.textContent=i===0?"DEFAULT":"LIBRARY";chip.append(b);$("charList").append(chip)});
}
function removeMod(id){
  const m=S.mods.find(x=>x.id===id);if(!m)return;
  m.chars.forEach(c=>URL.revokeObjectURL(c.imageUrl));S.mods=S.mods.filter(x=>x.id!==id);S.chars=[BF,...S.mods.flatMap(x=>x.chars)];renderMods();toast("Mod removed");
}
$("play").onclick=()=>$("modal").classList.remove("hidden");
$("options").onclick=()=>show("options");$("mods").onclick=()=>show("mods");
$("close").onclick=()=>$("modal").classList.add("hidden");
$("solo").onclick=()=>{$("modal").classList.add("hidden");show("play")};
$("two").onclick=()=>toast("El modo de 2 jugadores todavía requiere adaptar el PlayState de Psych Engine.");
document.querySelectorAll(".back").forEach(b=>b.onclick=()=>show("home"));
$("zip").onchange=async e=>{
  for(const f of [...e.target.files]){
    $("importStatus").textContent="Importando "+f.name+"…";
    try{const n=await importZip(f);$("importStatus").textContent=f.name+": "+n+" personaje(s) detectado(s).";toast(n+" character(s) imported")}
    catch(err){$("importStatus").textContent=f.name+": "+err.message;toast("No se pudo importar el ZIP")}
  }
  e.target.value="";
};
$("smooth").onchange=e=>{S.smooth=e.target.checked;localStorage.setItem("pp-smooth",S.smooth)};
$("touchToggle").onchange=e=>{localStorage.setItem("pp-touch",e.target.checked);toast("Los controles táctiles de la interfaz se guardaron.")};
$("motion").onchange=e=>{document.body.classList.toggle("reduce-motion",e.target.checked);localStorage.setItem("pp-motion",e.target.checked)};
window.addEventListener("DOMContentLoaded",async()=>{
  S.smooth=localStorage.getItem("pp-smooth")!=="false";$("smooth").checked=S.smooth;
  $("touchToggle").checked=localStorage.getItem("pp-touch")==="true";
  $("motion").checked=localStorage.getItem("pp-motion")==="true";document.body.classList.toggle("reduce-motion",$("motion").checked);
  renderMods();render();
  try{S.preview=await makeActor(BF);S.preview.play("idle")}catch(e){console.error(e);toast("No se pudo cargar el preview de BF.")}
});
})();