(function(){
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (btn) btn.addEventListener('click', function(){
    var n = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', n); try { localStorage.setItem('blog-theme', n); } catch(e){}
  });

  var dateEl = document.getElementById('mag-date');
  if (dateEl) dateEl.textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) + ' · VOL.1';

  function getCategoriesOf(p) {
    if (Array.isArray(p.categories)) return p.categories;
    if (p.category) return [p.category];
    return [];
  }
  function primaryCat(p) { return getCategoriesOf(p)[0] || ''; }

  var feat = document.getElementById('mag-feature');
  var grid = document.getElementById('posts-grid');
  if (!feat || !grid) return;

  fetch('posts.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      var posts = data.posts;
      if (!posts.length) { feat.innerHTML = '<p style="padding: 40px;">아직 게시된 글이 없습니다.</p>'; return; }

      var hero = posts[0];
      var rest = posts.slice(1, 5);
      var grid_items = posts.slice(1);
      var heroCat = primaryCat(hero);

      feat.innerHTML = `
        <div class="mag-feature__main">
          <div class="mag-feature__hero">${heroCat.slice(0,1).toUpperCase()}</div>
          <div class="mag-feature__cat">${heroCat}</div>
          <h2 class="mag-feature__title"><a href="${hero.filename}">${hero.title}</a></h2>
          <p class="mag-feature__summary">${hero.summary || ''}</p>
        </div>
        <aside class="mag-feature__sidebar">
          <h3>EDITOR'S PICKS</h3>
          <ul>${rest.map((p, i) => `
            <li><a href="${p.filename}">
              <span class="num">${String(i+1).padStart(2,'0')}</span>
              <span class="ttl">${p.title}</span>
            </a></li>`).join('')}</ul>
        </aside>`;

      grid.innerHTML = grid_items.map(p => {
        var c = primaryCat(p);
        return `
        <article class="mag-card"><a href="${p.filename}">
          <div class="mag-card__hero">${c.slice(0,2).toUpperCase()}</div>
          <div class="mag-card__cat">${c}</div>
          <h3 class="mag-card__title">${p.title}</h3>
          <p class="mag-card__summary">${p.summary || ''}</p>
        </a></article>`;
      }).join('');
    })
    .catch(e => grid.innerHTML = '<p>posts.json 로드 실패</p>');
})();
