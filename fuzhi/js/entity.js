(function(){
  const ents=window.FUZHI_ENTITIES||{people:[],places:[],alias:{}};
  function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]))}
  function loadScript(src){
    return new Promise((ok,no)=>{
      const s=document.createElement("script");
      s.src=src;s.onload=ok;s.onerror=no;document.head.appendChild(s);
    });
  }
  const raw=new URLSearchParams(location.search).get("n")||"";
  const name=(ents.alias&&ents.alias[raw])||raw;
  const all=[...(ents.people||[]),...(ents.places||[])];
  const meta=all.find(e=>e.name===name);
  const hName=document.getElementById("entName");
  const hKind=document.getElementById("entKind");
  const hAlias=document.getElementById("entAlias");
  const main=document.getElementById("entMain");
  if(!name){hName.textContent="未指定词条";main.innerHTML="<p class=\"miss\">请从人物或地名索引进入。</p>";return}
  document.title=name+" · 乾隆《泉州府志》";
  hName.textContent=name;
  if(meta){
    hKind.textContent=meta.kind==="person"?"人物":"地名 · 建筑";
    const al=meta.aliases||[];
    hAlias.textContent=(al.length?"又作 "+al.join("、")+"。 ":"")+"全书 "+meta.hits+" 处，见于 "+meta.secs+" 篇。";
  }else{
    hKind.textContent="词条";
    hAlias.textContent="目录中没有这一条，仍尝试读取检索结果。";
  }
  const shard=meta?meta.shard:"";
  if(!shard){main.innerHTML="<p class=\"miss\">没有找到相关篇目。</p>";return}
  loadScript("data/e/"+shard+".js").then(()=>{
    const pack=(window.FUZHI_HITS||{})[name];
    if(!pack||!pack.hits||!pack.hits.length){main.innerHTML="<p class=\"miss\">没有找到相关篇目。</p>";return}
    const hits=pack.hits;
    const bios=hits.filter(h=>h.bio);
    let html="";
    if(bios.length){
      html+="<div class=\"bio-card\"><div class=\"k\">本传 / 本条</div>"+bios.map(h=>"<div><a href=\""+esc(h.href)+"\">"+esc(h.juan)+(h.vt?"《"+esc(h.vt)+"》":"")+" · "+esc(h.sec)+"</a><p class=\"snip\">"+esc(h.snip)+"</p></div>").join("")+"</div>";
    }
    const rest=hits.filter(h=>!h.bio);
    const groups=[];
    const map=new Map();
    for(const h of rest){
      if(!map.has(h.vol)){const g={vol:h.vol,juan:h.juan,vt:h.vt,items:[]};map.set(h.vol,g);groups.push(g)}
      map.get(h.vol).items.push(h);
    }
    html+=groups.map(g=>{
      const href="v/"+g.vol+".html";
      return "<section class=\"hit-vol\"><h2><a href=\""+esc(href)+"\">"+esc(g.juan)+(g.vt?"　"+esc(g.vt):"")+"</a></h2>"+
        g.items.map(h=>{
          const sn=esc(h.snip).replaceAll(esc(name),"<b>"+esc(name)+"</b>");
          return "<div class=\"hit\"><a class=\"sec\" href=\""+esc(h.href)+"\">"+esc(h.sec)+"<small> · "+h.n+" 处</small></a><p class=\"snip\">"+sn+"</p></div>";
        }).join("")+"</section>";
    }).join("");
    main.innerHTML=html||"<p class=\"miss\">没有找到相关篇目。</p>";
  }).catch(()=>{main.innerHTML="<p class=\"miss\">检索数据未能载入。</p>"});
})();
