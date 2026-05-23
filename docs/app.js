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

function renderSessionsList(sessions) {
  const el = document.getElementById('sessions-list');
  if (!sessions || sessions.length === 0) {
    renderEmpty(el, '세션 없음');
    return;
  }
  let html = '';
  for (const name of sessions) {
    const short = name.replace(/^session_/, '').replace(/\.md$/, '');
    const escapedAttr = name.replace(/"/g, '&quot;');
    html += `<div class="session-item" data-file="${escapedAttr}">${short}</div>`;
  }
  el.innerHTML = html;
  el.addEventListener('click', onSessionClick);
}

let currentSessionEl = null;
async function onSessionClick(e) {
  const item = e.target.closest('.session-item');
  if (!item) return;
  const file = item.dataset.file;
  if (currentSessionEl) currentSessionEl.classList.remove('active');
  item.classList.add('active');
  currentSessionEl = item;

  const render = document.getElementById('session-render');
  render.innerHTML = '<em>loading…</em>';
  try {
    const md = await fetchText(`${DATA_PATH}/sessions/${file}`);
    render.innerHTML = DOMPurify.sanitize(marked.parse(md));
  } catch (err) {
    render.innerHTML = `<div class="empty">파일 로드 실패: ${file}</div>`;
  }
}

function parseLog(md) {
  // decisions-log.md 의 `## YYYY-MM-DDTHH:MM:SS | 핀 추가|제거` 블럭 파싱.
  // 반환: [{time, event, body}], 최신순.
  const blocks = [];
  const lines = md.split('\n');
  let current = null;
  for (const ln of lines) {
    const m = ln.match(/^##\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?)\s*\|\s*(.+)$/);
    if (m) {
      if (current) blocks.push(current);
      current = { time: m[1], event: m[2].trim(), body: [] };
    } else if (current) {
      current.body.push(ln);
    }
  }
  if (current) blocks.push(current);
  blocks.reverse();
  return blocks;
}

function renderLog(md) {
  const el = document.getElementById('log-list');
  if (!md || !md.trim()) { renderEmpty(el, '로그 없음'); return; }
  const blocks = parseLog(md);
  if (blocks.length === 0) { renderEmpty(el, '로그 없음'); return; }
  let html = '';
  for (const b of blocks) {
    const cls = b.event.includes('추가') ? 'event-pin'
              : b.event.includes('제거') ? 'event-unpin' : '';
    const bodyHtml = DOMPurify.sanitize(marked.parse(b.body.join('\n').trim() || ''));
    html += `<div class="log-card">
      <div class="time">${b.time}</div>
      <div class="${cls}">${b.event}</div>
      <div>${bodyHtml}</div>
    </div>`;
  }
  el.innerHTML = html;
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

  renderSessionsList(manifest.sessions || []);

  if (manifest.decisions_log) {
    const logMd = await fetchText(`${DATA_PATH}/decisions-log.md`);
    renderLog(logMd);
  } else {
    renderEmpty(document.getElementById('log-list'), '로그 없음');
  }
}

load();
