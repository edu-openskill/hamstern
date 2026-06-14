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

  var el = document.getElementById('lecture-groups');
  if (!el) return;
  fetch('posts.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      // Group by first category (syllabus primary section)
      var groups = {};
      data.posts.forEach(p => {
        var cat = getCategoriesOf(p)[0] || '기타';
        (groups[cat] = groups[cat] || []).push(p);
      });
      var html = '';
      Object.keys(groups).forEach(cat => {
        html += `<section class="group"><h3 class="group__heading">${cat}</h3><ul class="group__list">`;
        groups[cat].forEach((p, i) => {
          var d = new Date(p.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
          html += `<li class="lec-item">
            <div class="lec-item__num">L${String(i+1).padStart(2,'0')}</div>
            <div class="lec-item__body"><a href="${p.filename}">
              <div class="lec-item__title">${p.title}</div>
              <div class="lec-item__summary">${p.summary || ''}</div>
            </a></div>
            <div class="lec-item__meta">${d}</div>
          </li>`;
        });
        html += `</ul></section>`;
      });
      el.innerHTML = html;
    })
    .catch(e => el.innerHTML = '<p>posts.json 로드 실패</p>');
})();
