(function(){
  const toc=document.getElementById("toc");
  const mask=document.getElementById("tocMask");
  const tocBtn=document.getElementById("tocBtn");
  const noteBtn=document.getElementById("noteBtn");
  const root=document.body;

  function openToc(on){
    if(!toc)return;
    toc.classList.toggle("open",on);
    if(mask) mask.classList.toggle("open",on);
    document.body.style.overflow=on && window.matchMedia("(max-width:959px)").matches?"hidden":"";
  }
  if(tocBtn) tocBtn.addEventListener("click",()=>openToc(!toc.classList.contains("open")));
  if(mask) mask.addEventListener("click",()=>openToc(false));
  if(toc) toc.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>{
    if(window.matchMedia("(max-width:959px)").matches) openToc(false);
  }));

  function setNotes(hide){
    root.classList.toggle("hide-notes",hide);
    if(noteBtn){
      noteBtn.setAttribute("aria-pressed", hide?"true":"false");
      noteBtn.textContent=hide?"显示注解":"收起注解";
    }
    try{localStorage.setItem("fuzhi-hide-notes", hide?"1":"0")}catch(e){}
  }
  let hide=false;
  try{hide=localStorage.getItem("fuzhi-hide-notes")==="1"}catch(e){}
  setNotes(hide);
  if(noteBtn) noteBtn.addEventListener("click",()=>setNotes(!root.classList.contains("hide-notes")));

  const links=[...document.querySelectorAll("#toc a[href^='#']")];
  const els=links.map(a=>document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)))).filter(Boolean);
  if(els.length && "IntersectionObserver" in window){
    const vis=new Map();
    const io=new IntersectionObserver(entries=>{
      entries.forEach(e=>vis.set(e.target.id,e.isIntersecting && e.intersectionRatio>0));
      let cur=null;
      for(const el of els){if(vis.get(el.id)){cur=el;break}}
      if(!cur){
        const y=window.scrollY+80;
        for(const el of els){if(el.offsetTop<=y)cur=el}
      }
      links.forEach(a=>a.classList.toggle("on",cur && a.getAttribute("href")==="#"+cur.id));
    },{rootMargin:"-20% 0px -65% 0px",threshold:[0,.1,.5]});
    els.forEach(el=>io.observe(el));
  }
})();
