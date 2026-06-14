(function(){
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (btn) btn.addEventListener('click', function(){
    var n = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', n); try { localStorage.setItem('blog-theme', n); } catch(e){}
  });

  function getCategoriesOf(p) {
    if (Array.isArray(p.categories)) return p.categories;
    if (p.category) return [p.category];
    return [];
  }

  var listEl = document.getElementById('posts-list');
  var tocEl = document.getElementById('toc-list');
  if (!listEl) return;

  fetch('posts.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      var html = '';
      var toc = '';
      data.posts.forEach(function(p, i){
        var n = `[${String(i+1).padStart(2,'0')}]`;
        var d = new Date(p.date).toLocaleDateString('en-CA');
        var primary = getCategoriesOf(p)[0] || '';
        html += `<a class="nb-post" href="${p.filename}">
          <div class="nb-post__num">In ${n}: # ${primary}</div>
          <div class="nb-post__title">${p.title}</div>
          <div class="nb-post__summary">${p.summary || ''}</div>
          <div class="nb-post__meta">${d} · ${(p.tags||[]).map(t=>'#'+t).join(' ')}</div>
        </a>`;
        toc += `<li><a href="${p.filename}">${n} ${p.title}</a></li>`;
      });
      listEl.innerHTML = html;
      if (tocEl) tocEl.innerHTML = toc;
    })
    .catch(e => listEl.innerHTML = '<p>posts.json 로드 실패</p>');
})();
