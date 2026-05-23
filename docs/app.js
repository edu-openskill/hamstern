// docs/app.js
// 정적 viewer — fetch manifest → render decisions + sessions + log
// read-only. write 는 클립보드 슬래시 명령 + 사용자 세션 경유.

const DATA_PATH = 'data';

async function fetchText(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.text();
}
async function fetchJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

function setGenerated(ts) {
  document.getElementById('generated').textContent = ts ? `generated: ${ts}` : '';
}

function renderEmpty(el, msg) {
  el.innerHTML = `<div class="empty">${msg}</div>`;
}

function parseDecisions(md) {
  // returns [{category, body, raw}] in document order
  const out = [];
  let currentCat = 'Other';
  for (const ln of md.split('\n')) {
    if (ln.startsWith('## ')) {
      currentCat = ln.slice(3).trim();
      continue;
    }
    if (ln.startsWith('- ')) {
      const raw = ln;
      let body = ln.slice(2);
      body = body.replace(/\s*<!--\s*session:\s*\S+?\s*-->\s*$/, '').trim();
      out.push({ category: currentCat, body, raw });
    }
  }
  return out;
}

function renderDecisions(md) {
  const el = document.getElementById('decisions-list');
  if (!md || !md.trim()) {
    renderEmpty(el, '결정사항 없음<br><small>/hams:record 로 추가 가능</small>');
    return;
  }
  const items = parseDecisions(md);
  if (items.length === 0) {
    renderEmpty(el, '결정사항 없음');
    return;
  }
  const byCat = new Map();
  for (const it of items) {
    if (!byCat.has(it.category)) byCat.set(it.category, []);
    byCat.get(it.category).push(it);
  }
  let html = '';
  for (const [cat, list] of byCat) {
    html += `<div class="decision-category">${cat}</div>`;
    for (const it of list) {
      const escapedAttr = it.body.replace(/"/g, '&quot;');
      html += `<div class="decision-item">
        <span class="text">${DOMPurify.sanitize(it.body)}</span>
        <span class="del" data-text="${escapedAttr}" title="제거">×</span>
      </div>`;
    }
  }
  el.innerHTML = html;
}

async function load() {
  let manifest;
  try {
    manifest = await fetchJSON(`${DATA_PATH}/manifest.json`);
  } catch (e) {
    renderEmpty(document.getElementById('decisions-list'),
      'Dashboard 데이터 미생성.<br>Claude 세션에서 <code>/hams:dashboard</code> 호출 후 재방문.');
    return;
  }
  setGenerated(manifest.generated_at);

  if (manifest.decisions) {
    const md = await fetchText(`${DATA_PATH}/decisions.md`);
    renderDecisions(md);
  } else {
    renderEmpty(document.getElementById('decisions-list'), '결정사항 없음');
  }
}

load();
