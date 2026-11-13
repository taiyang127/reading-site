// Shared helpers. Data is loaded via <script> files so the site works on file:// and http://
window.U=(function(){
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const loadScript=src=>new Promise((ok,no)=>{const s=document.createElement("script");s.src=src;s.onload=ok;s.onerror=no;document.head.appendChild(s)});
const qs=k=>new URLSearchParams(location.search).get(k);
const okSlug=s=>/^[\w-]+$/.test(s||"");
// e-commerce style: neutral shelf box, cover bottom-aligned with spine shading + shadow
function coverBook(b,big){const src=big?(b.cover||b.coverThumb):(b.coverThumb||b.cover);
 return src?`<span class="cv-b"><img src="${esc(src)}" alt="${esc(b.title)} 封面" loading="lazy"></span>`:`<span class="cv-b ph"><b>${esc(b.title)}</b><span>${esc(b.author||"")}</span></span>`}
function cover(b,big){return `<div class="cv">${coverBook(b,big)}</div>`}
function header(on){return `<header class="hdr"><div class="container"><a class="logo" href="index.html"><i>书</i>拆书房</a>
 <nav><a href="index.html" class="${on=="home"?"on":""}">书库</a><a href="index.html#cats" >分类</a><a href="recs.html" class="${on=="recs"?"on":""}">每日推荐</a></nav></div></header>`}
function blocks(bs,lvl=2){return (bs||[]).map(b=>{switch(b.type){
 case"section":return `<h${lvl}>${esc(b.heading)}</h${lvl}>${b.caption?`<div class="status">${esc(b.caption)}</div>`:""}${blocks(b.blocks,Math.min(lvl+1,4))}`;
 case"text":return `<p>${esc(b.text)}</p>`;
 case"callout":return `<div class="callout">${b.lead?`<b>${esc(b.lead)}</b>`:""}${esc(b.text)}</div>`;
 case"quote":return `<blockquote>${esc(b.text)}${b.cite?`<cite>—— ${esc(b.cite)}</cite>`:""}</blockquote>`;
 case"props":return `<dl class="props">${b.items.map(i=>`<dt>${esc(i.label)}</dt><dd>${esc(i.value)}</dd>`).join("")}</dl>`;
 case"rows":return `<div class="rows">${b.rows.map(r=>`<div><div class="ld">${esc(r.lead)}</div><b>${esc(r.title)}</b><div>${esc(r.detail)}</div></div>`).join("")}</div>`;
 case"list":return `<ul>${b.items.map(i=>`<li>${esc(i)}</li>`).join("")}</ul>`;
 case"table":return `<div class="tw"><table><thead><tr>${b.columns.map(c=>`<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${b.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
 case"status":return `<p class="status">${esc(b.text)}</p>`;case"divider":return"<hr>";default:return"";}}).join("")}
async function loadRecs(){try{await loadScript("recommendations/index.js")}catch(e){return[]}
 const ys=window.REC_YEARS||[];for(const y of ys){try{await loadScript(`recommendations/${y}.js`)}catch(e){}}
 return ys.flatMap(y=>(window.RECS||{})[y]||[]).sort((a,b)=>b.date.localeCompare(a.date))}
function rec(r,books){const linked=r.book&&books&&books.find(b=>b.slug===r.book);
 return `<div class="rec">${cover(r)}<div><div class="d">${esc(r.date)}</div><h3>${esc(r.title)}</h3><div class="status">${esc(r.author)}</div>
 <div class="tags" style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">${(r.tags||[]).map(t=>`<span class="t">${esc(t)}</span>`).join("")}</div>
 <p>${esc(r.why)}</p><div class="links">${linked?`<a href="book.html?b=${encodeURIComponent(r.book)}">本站书页 →</a>`:""}${(r.sources||[]).map((s,i)=>`<a href="${esc(s)}" target="_blank" rel="noopener">来源${(r.sources.length>1)?i+1:""}</a>`).join("")}</div></div></div>`}

// ---- ebook loading: plain (private local build) or encrypted (protected build) ----
const b64d=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const b64e=u=>{let s="";const a=new Uint8Array(u);for(let i=0;i<a.length;i+=0x8000)s+=String.fromCharCode.apply(null,a.subarray(i,i+0x8000));return btoa(s)};
const KEYNAME="ebookKey";
async function ebookStatus(slug){ // "plain" | "locked" | null
  try{await loadScript(`ebooks/${slug}.js`);if((window.EBOOKS||{})[slug])return"plain"}catch(e){}
  try{await loadScript(`ebooks/${slug}.enc.js`);if((window.__ENC||{})[slug])return"locked"}catch(e){}
  return null}
async function deriveKey(pw,salt,iter){const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2",hash:"SHA-256",salt:b64d(salt),iterations:iter},base,{name:"AES-GCM",length:256},true,["decrypt"])}
async function decryptWith(key,blob){const pt=await crypto.subtle.decrypt({name:"AES-GCM",iv:b64d(blob.iv)},key,b64d(blob.ct));return JSON.parse(new TextDecoder().decode(pt))}
function storedKey(){return sessionStorage.getItem(KEYNAME)||localStorage.getItem(KEYNAME)}
async function tryStored(blob){const raw=storedKey();if(!raw)return null;
  try{const k=await crypto.subtle.importKey("raw",b64d(raw),"AES-GCM",false,["decrypt"]);return await decryptWith(k,blob)}catch(e){sessionStorage.removeItem(KEYNAME);localStorage.removeItem(KEYNAME);return null}}
async function unlock(blob,pw,remember){const k=await deriveKey(pw,blob.salt,blob.iter);const data=await decryptWith(k,blob); // throws on wrong pw
  const raw=b64e(await crypto.subtle.exportKey("raw",k));sessionStorage.setItem(KEYNAME,raw);if(remember)localStorage.setItem(KEYNAME,raw);else localStorage.removeItem(KEYNAME);return data}
function forget(){sessionStorage.removeItem(KEYNAME);localStorage.removeItem(KEYNAME)}
const footer=()=>`<footer class="container">拆书房 · 静态阅读站 · 精读内容为个人阅读笔记</footer>`;
return {ebookStatus,tryStored,unlock,forget,coverBook,esc,loadScript,qs,okSlug,cover,header,blocks,loadRecs,rec,footer};
})();
