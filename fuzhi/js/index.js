(function(){
  const data=window.FUZHI_INDEX;
  const ents=window.FUZHI_ENTITIES||{people:[],places:[],alias:{}};
  const input=document.getElementById("q");
  const out=document.getElementById("searchOut");
  const cats=document.getElementById("cats");
  if(!data||!input||!out)return;
  function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]))}
  function mark(s,q){
    const i=s.toLowerCase().indexOf(q.toLowerCase());
    if(i<0)return esc(s);
    return esc(s.slice(0,i))+"<mark>"+esc(s.slice(i,i+q.length))+"</mark>"+esc(s.slice(i+q.length));
  }
  function entHref(name){return "e.html?n="+encodeURIComponent(name)}
  function search(q){
    q=q.trim();
    if(!q){out.innerHTML="";if(cats)cats.style.display="";return}
    const hits=[];
    for(const list of [ents.people||[],ents.places||[]]){
      for(const e of list){
        const hay=e.name+(e.aliases||[]).join("");
        if(hay.includes(q)){
          const kind=e.kind==="person"?"人物":"地名";
          hits.push({href:entHref(e.name),vol:kind,sec:e.name+((e.aliases&&e.aliases.length)?"（"+e.aliases.join("、")+"）":""),rank:0,extra:e.secs+" 篇"});
        }
      }
    }
    for(const v of data.volumes){
      const hay=v.juan+" "+v.title+" "+(v.fullTitle||"");
      if(hay.includes(q)){
        hits.push({href:v.href,vol:v.juan+"　"+v.title,sec:"",rank:1});
      }
      for(const s of (v.sections||[])){
        if(s.title.includes(q)){
          hits.push({href:v.href+"#"+s.id,vol:v.juan+"　"+v.title,sec:s.title,rank:2});
        }
      }
    }
    hits.sort((a,b)=>a.rank-b.rank);
    if(cats)cats.style.display=hits.length?"none":"";
    if(!hits.length){out.innerHTML="<div class=\"miss\">没有找到「"+esc(q)+"」相关的篇目、人名或地名</div>";return}
    const shown=hits.slice(0,80);
    out.innerHTML=shown.map(h=>"<a class=\"hit\" href=\""+esc(h.href)+"\"><span class=\"h-vol\">"+mark(h.vol,q)+"</span>"+(h.sec?"<span class=\"h-sec\">"+mark(h.sec,q)+"</span>":"")+(h.extra?"<span class=\"h-sec\">"+esc(h.extra)+"</span>":"")+"</a>").join("")
      +(hits.length>80?"<div class=\"miss\">另有 "+(hits.length-80)+" 条，请再缩小关键词</div>":"");
  }
  let t;
  input.addEventListener("input",()=>{clearTimeout(t);t=setTimeout(()=>search(input.value),80)});
  input.addEventListener("keydown",e=>{if(e.key==="Escape"){input.value="";search("")}});
  const u=new URLSearchParams(location.search).get("q");
  if(u){input.value=u;search(u)}
})();
