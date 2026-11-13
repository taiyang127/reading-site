(function(){
  const ents=window.FUZHI_ENTITIES||{people:[],places:[],alias:{}};
  const input=document.getElementById("q");
  const out=document.getElementById("searchOut");
  const main=document.getElementById("idxMain");
  if(!input||!out||!main)return;
  const kind=main.dataset.kind==="place"?"places":"people";
  function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]))}
  function search(q){
    q=q.trim();
    if(!q){out.innerHTML="";main.style.display="";return}
    const hits=(ents[kind]||[]).filter(e=>e.name.includes(q)||(e.aliases||[]).some(a=>a.includes(q)));
    main.style.display=hits.length?"none":"";
    if(!hits.length){out.innerHTML="<div class=\"miss\">没有找到「"+esc(q)+"」</div>";return}
    out.innerHTML=hits.slice(0,80).map(e=>"<a class=\"hit\" href=\"e.html?n="+encodeURIComponent(e.name)+"\"><span class=\"h-vol\">"+esc(e.name)+"</span><span class=\"h-sec\">"+(e.aliases&&e.aliases.length?esc(e.aliases.join("、"))+" · ":"")+e.secs+" 篇</span></a>").join("");
  }
  let t;
  input.addEventListener("input",()=>{clearTimeout(t);t=setTimeout(()=>search(input.value),60)});
})();
