(function(){
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (btn) btn.addEventListener('click', function(){
    var n = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', n); try { localStorage.setItem('blog-theme', n); } catch(e){}
  });

  var listEl = document.getElementById('posts-list');
  if (!listEl) return;
  fetch('posts.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      listEl.innerHTML = data.posts.map(p => {
        var d = new Date(p.date).toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' });
        return `<li class="post-item">
          <a href="${p.filename}">
            <div class="post-item__date">${d}</div>
            <h2 class="post-item__title">${p.title}</h2>
            <p class="post-item__summary">${p.summary || ''}</p>
            <span class="post-item__category">${p.category}</span>
          </a></li>`;
      }).join('');
    })
    .catch(e => listEl.innerHTML = `<li>posts.json 로드 실패</li>`);
})();
