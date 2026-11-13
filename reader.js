(async function(){
const {esc}=U,slug=U.qs("b");let mode=U.qs("m")||"ebook";
const $=id=>document.getElementById(id);
if(!U.okSlug(slug))return;
try{await U.loadScript(`books/${slug}.js`)}catch(e){}
const book=(window.BOOKS||{})[slug];
let eb=null;if(mode==="ebook"){const st0=await U.ebookStatus(slug);
 if(st0==="plain")eb=window.EBOOKS[slug];
 else if(st0==="locked"){const blob=window.__ENC[slug];eb=await U.tryStored(blob);if(!eb)eb=await gate(blob)}
 if(!eb)mode="guide"}
function gate(blob){return new Promise(res=>{
 const g=document.createElement("div");g.className="gate";
 g.innerHTML=`<form class="gate-card" autocomplete="off"><div class="gate-ic">🔒</div><h2>全文需要密码</h2>
  <p>此书全文仅供本人阅读。输入密码解锁；导读内容无需密码。</p>
  <input type="password" id="gpw" placeholder="输入密码" autocomplete="current-password" autofocus>
  <label class="gate-rm"><input type="checkbox" id="grm"> 记住此设备</label>
  <div class="gate-err" id="gerr" hidden></div>
  <button type="submit" class="gate-go" id="ggo">解锁阅读</button>
  <button type="button" class="gate-alt" id="galt">先看精读版</button></form>`;
 document.body.appendChild(g);
 const f=g.querySelector("form"),err=g.querySelector("#gerr"),go=g.querySelector("#ggo");
 f.onsubmit=async e=>{e.preventDefault();const pw=g.querySelector("#gpw").value;if(!pw)return;
  go.disabled=true;go.textContent="解锁中…";err.hidden=true;
  try{const d=await U.unlock(blob,pw,g.querySelector("#grm").checked);g.remove();res(d)}
  catch(x){err.textContent="密码不对，再试一次。";err.hidden=false;go.disabled=false;go.textContent="解锁阅读";g.querySelector("#gpw").select();f.classList.remove("shake");void f.offsetWidth;f.classList.add("shake")}};
 g.querySelector("#galt").onclick=()=>{g.remove();res(null)};
})}
if(!book&&!eb){$("ti").textContent="找不到这本书";return}
$("back").href=`book.html?b=${encodeURIComponent(slug)}`;
// normalise to [{id,title,html,part}]
const ebHtml=c=>`<h1>${esc(c.title)}</h1>`+c.blocks.map((b,i)=>b.t==="img"?`<img src="${esc(b.src)}" alt="${esc(b.alt)}">`:b.t==="h"?(i<3&&c.title.replace(/\s/g,"").includes(b.x.replace(/\s/g,""))?"":`<h3>${esc(b.x)}</h3>`):b.t==="q"?`<blockquote>${esc(b.x)}</blockquote>`:`<p>${esc(b.x)}</p>`).join("");
// lazy ebooks (eb.lazy): each chapter has src; blocks are loaded on demand
const CH=mode==="ebook"&&eb.lazy?eb.chapters.map(c=>({id:c.id,title:c.title,src:c.src,part:false,html:null}))
 :mode==="ebook"?eb.chapters.map(c=>({id:c.id,title:c.title,part:!/^第.+章|^[一二三四五六七八九十]+——/.test(c.title)&&c.blocks.filter(b=>b.x).length<6,
  html:`<h1>${esc(c.title)}</h1>`+c.blocks.map((b,i)=>b.t==="img"?`<img src="${esc(b.src)}" alt="${esc(b.alt)}">`:b.t==="h"?(i<3&&c.title.replace(/\s/g,"").includes(b.x.replace(/\s/g,""))?"":`<h3>${esc(b.x)}</h3>`):b.t==="q"?`<blockquote>${esc(b.x)}</blockquote>`:`<p>${esc(b.x)}</p>`).join("")}))
 :book.chapters.map(c=>({id:c.id,title:c.title,part:c.kind!=="chapter",html:`<h1>${esc(c.title)}</h1>${c.caption?`<p class="ni" style="text-align:center;color:var(--mute)">${esc(c.caption)}</p>`:""}`+U.blocks(c.blocks,2).replace(/<p>/g,'<p class="ni">')}));
const title=(book&&book.title)||eb.title;document.title=title+" · 阅读";
$("ti").innerHTML=`${esc(title)}<span class="mode">${mode==="ebook"?"全文":"按章精读版"}</span>`;
const KEY=`pos:${slug}:${mode}`;let st={};try{st=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
let fs=+localStorage.getItem("reader:fs")||0;
let ci=0,page=0,pages=1,per=1,stepW=0,flipping=false;
const h=new URLSearchParams(location.hash.slice(1));
const want=h.get("c")||st.c;ci=Math.max(0,CH.findIndex(c=>c.id===want));let frac=h.get("c")&&h.get("c")!==st.c?0:(st.f||0);
// drawer
$("drawer").innerHTML=(book?`<div style="display:flex;gap:14px;align-items:flex-end;padding:18px 18px 6px"><div style="width:64px;flex:none">${U.coverBook(book)}</div><div><div style="font-family:var(--serif);font-weight:700;font-size:16px">${esc(book.title)}</div><div style="font-size:12.5px;color:var(--mute)">${esc(book.author)}</div></div></div>`:"")+`<h3>目录</h3>`+CH.map((c,i)=>`<a href="#" data-i="${i}" class="${c.part?"pt":""}">${esc(c.title)}</a>`).join("");
const openD=o=>{$("drawer").classList.toggle("open",o);$("mask").classList.toggle("open",o)};
$("tocBtn").onclick=()=>openD(true);$("mask").onclick=()=>openD(false);
$("drawer").onclick=e=>{const a=e.target.closest("a");if(!a)return;e.preventDefault();openD(false);go(+a.dataset.i,0)};
function layout(){
 const W=innerWidth,H=innerHeight-48-44,spread=W>=1100 && W/H>1.15;per=spread?2:1; // never two-page on phone/portrait
 const bh=spread?Math.min(H-28,880):H-(W<700?4:28);const pw=spread?Math.min((W-100)/2,bh*.7):Math.min(W-(W<700?8:48),Math.round(bh/1.38));
 const book=$("book");book.classList.toggle("spread",spread);book.style.width=pw*per+"px";book.style.height=bh+"px";
 const padX=W<700?Math.max(22,Math.round(pw*.08)):Math.round(pw*.12),padT=W<700?42:52,padB=W<700?44:54;
 const vp=$("vp");vp.style.left=padX+"px";vp.style.top=padT+"px";vp.style.width=(pw*per-2*padX)+"px";vp.style.height=(bh-padT-padB)+"px";
 const f=$("flow");const base=(W<700?17.5:18.5)+fs;f.style.fontSize=base+"px";f.style.lineHeight=W<700?"1.9":"1.95";
 f.style.columnWidth=(pw-2*padX)+"px";f.style.columnGap=(2*padX)+"px";f.style.setProperty("--ph",(bh-padT-padB-20)+"px");
 stepW=pw;
 [["hdL",0],["hdR",1]].forEach(([id,k])=>{const e=$(id);e.style.left=(k*pw+padX)+"px";e.style.width=(pw-2*padX)+"px";e.style.textAlign=k?"right":"left";e.style.display=(!spread&&k===0)?"none":""});
 [["pnL",0],["pnR",1]].forEach(([id,k])=>{const e=$(id);e.style.left=(k*pw)+"px";e.style.width=pw+"px";e.style.textAlign="center";e.style.display=(!spread&&k)?"none":""});
 const fl=$("flip");fl.style.width=pw+"px";
}
function measure(){const f=$("flow");f.style.transition="none";f.style.transform="none";
 const last=f.lastElementChild;const vpl=$("vp").getBoundingClientRect().left;
 const right=last?last.getBoundingClientRect().right-vpl:0;pages=Math.max(1,Math.ceil((right+5)/stepW));if(pages%per)pages+=per-pages%per;
 $("prog").max=Math.max(0,pages/per-1);}
function draw(anim){const f=$("flow");f.style.transition=anim?"":"none";f.style.transform=`translateX(${-page*stepW}px)`;
 const c=CH[ci];$("hdL").textContent=title;$("hdR").textContent=c.title;
 if(per===1){$("hdL").style.display="none";$("hdR").style.display="";$("hdR").style.left=$("hdL").style.left;$("hdR").style.textAlign="right"}
 $("pnL").textContent=per===2?`${page+1}`:`${page+1} / ${pages}`;$("pnR").textContent=page+2<=pages?`${page+2}`:"";
 $("chi").textContent=`${ci+1}/${CH.length} · ${c.title}`;$("pg").textContent=`本章 ${Math.floor(page/per)+1}/${pages/per} ${per===2?"跨页":"页"}`;$("prog").value=Math.floor(page/per);
 document.querySelectorAll("#drawer a").forEach((a,i)=>a.classList.toggle("on",i===ci));
 frac=pages>1?page/pages:0;try{localStorage.setItem(KEY,JSON.stringify({c:c.id,f:frac,t:Date.now()}))}catch(e){}
 history.replaceState(null,"",`#c=${encodeURIComponent(c.id)}`);}
async function ensure(i){const c=CH[i];if(!c||c.html!=null)return;const k=`${slug}/${c.id}`;
 try{if(!(window.EBCH||{})[k])await U.loadScript(c.src);c.html=ebHtml({title:c.title,blocks:window.EBCH[k]||[]});delete window.EBCH[k]}catch(e){c.html=`<h1>${esc(c.title)}</h1><p>本卷加载失败，请检查网络后重试。</p>`}}
async function render(toFrac){if(CH[ci].html==null){$("flow").innerHTML='<p class="chap-end">加载中…</p>';await ensure(ci)}
 $("flow").innerHTML=CH[ci].html+`<p class="chap-end">· ${ci<CH.length-1?"本篇完":"全书完"} ·</p>`;layout();
 const imgs=[...$("flow").querySelectorAll("img")];
 const fin=()=>{measure();page=toFrac==="end"?pages-per:Math.min(pages-per,Math.round((toFrac||0)*pages/per)*per);draw(false)};
 fin();imgs.forEach(im=>{if(!im.complete)im.onload=im.onerror=()=>{const keep=page/pages;measure();page=Math.min(pages-per,Math.round(keep*pages/per)*per);draw(false)}});}
function go(i,fr){if(i<0||i>=CH.length)return;ci=i;if(eb&&eb.lazy)CH.forEach((c,j)=>{if(c.src&&Math.abs(j-i)>1)c.html=null});render(fr)}
function flip(dir){if(flipping)return;const fl=$("flip");
 const nextOk=dir>0?(page+per<pages||ci<CH.length-1):(page>0||ci>0);if(!nextOk){note(dir>0?"已是最后一页":"已是第一页");return}
 if(per===2&&!matchMedia("(prefers-reduced-motion: reduce)").matches){flipping=true;
  fl.style.left=(dir>0?stepW:0)+"px";fl.style.transformOrigin=dir>0?"left center":"right center";fl.style.transition="none";fl.style.transform="rotateY(0deg)";fl.classList.add("go");
  requestAnimationFrame(()=>requestAnimationFrame(()=>{fl.style.transition="transform .55s cubic-bezier(.32,.72,.25,1)";fl.style.transform=`rotateY(${dir>0?-180:180}deg)`;}));
  setTimeout(()=>step(dir,false),280);setTimeout(()=>{fl.classList.remove("go");flipping=false},580)}
 else step(dir,true)}
function step(dir,anim){if(dir>0){if(page+per<pages){page+=per;draw(anim)}else go(ci+1,0)}else{if(page>0){page-=per;draw(anim)}else go(ci-1,"end")}}
let nt;function note(t){const n=$("note");n.textContent=t;n.hidden=false;clearTimeout(nt);nt=setTimeout(()=>n.hidden=true,1200)}
$("eN").onclick=()=>flip(1);$("eP").onclick=()=>flip(-1);
addEventListener("keydown",e=>{if(e.key==="ArrowRight"||e.key==="PageDown"||e.key===" "){e.preventDefault();flip(1)}else if(e.key==="ArrowLeft"||e.key==="PageUp"){e.preventDefault();flip(-1)}else if(e.key==="Escape")openD(false)});
let tx=null,ty=0;$("stage").addEventListener("touchstart",e=>{tx=e.touches[0].clientX;ty=e.touches[0].clientY},{passive:true});
$("stage").addEventListener("touchend",e=>{if(tx==null)return;const dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;tx=null;if(Math.abs(dx)>40&&Math.abs(dx)>Math.abs(dy))flip(dx<0?1:-1)});
$("prog").oninput=e=>{page=+e.target.value*per;draw(true)};
$("fs-").onclick=()=>{fs=Math.max(-3,fs-1);localStorage.setItem("reader:fs",fs);render(frac)};$("fs+").onclick=()=>{fs=Math.min(6,fs+1);localStorage.setItem("reader:fs",fs);render(frac)};
let rt;addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(()=>render(frac),150)});
addEventListener("hashchange",()=>{const c=new URLSearchParams(location.hash.slice(1)).get("c");const i=CH.findIndex(x=>x.id===c);if(i>=0&&i!==ci)go(i,0)});
(document.fonts?document.fonts.ready:Promise.resolve()).then(()=>render(frac));
})();
