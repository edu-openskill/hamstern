(function(){
  // theme toggle
  var tg=document.getElementById('theme-toggle');
  if(tg)tg.addEventListener('click',function(){
    var n=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',n);
    try{localStorage.setItem('lec-theme',n);}catch(e){}
  });

  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c];});}

  function card(l){
    var acts='';
    acts+=l.slide
      ? '<a class="act act--slide" href="'+esc(l.slide)+'"><span class="dot">▶</span>판서 슬라이드</a>'
      : '<span class="act act--slide act--off"><span class="dot">▶</span>슬라이드</span>';
    acts+=l.sim
      ? '<a class="act act--sim" href="'+esc(l.sim)+'"><span class="dot">🧪</span>시뮬레이터</a>'
      : '';
    if(l.script){
      acts+='<a class="act act--lock" href="'+esc(l.script)+'"><span class="dot">🔒</span>판서 대본</a>';
    }
    return '<article class="lec">'
      +'<div class="lec__no">'+esc(l.no||'')+'</div>'
      +'<div class="lec__body">'
      +'<h3 class="lec__title">'+esc(l.title)+'</h3>'
      +(l.summary?'<p class="lec__summary">'+esc(l.summary)+'</p>':'')
      +'<div class="lec__acts">'+acts+'</div>'
      +'</div></article>';
  }

  fetch('lectures.json?'+Date.now()).then(function(r){return r.json();}).then(function(data){
    var root=document.getElementById('lecture-groups');
    var lecs=(data&&data.lectures)||[];
    if(!lecs.length){document.getElementById('empty-hint').hidden=false;return;}
    // group by section, preserve declared section order then first-seen
    var order=(data.sections&&data.sections.length)?data.sections.slice():[];
    var groups={};
    lecs.forEach(function(l){
      var s=l.section||'';
      (groups[s]=groups[s]||[]).push(l);
      if(order.indexOf(s)<0)order.push(s);
    });
    var html='';
    order.forEach(function(s){
      if(!groups[s])return;
      if(s)html+='<h3 class="section-title">'+esc(s)+'</h3>';
      html+=groups[s].map(card).join('');
    });
    root.innerHTML=html;
  }).catch(function(){document.getElementById('empty-hint').hidden=false;});
})();
