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
    const escapedAttr = name.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
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
    const md = await fetchText(`${window._currentDataPath || DATA_PATH}/sessions/${file}`);
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

function showToast(msg, ms = 3000) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.add('hidden'), ms);
}

function escapeForSlashCommand(text) {
  // `"` 를 backslash escape — audit-decisions remove.py 와 대응
  return text.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
    return ok;
  }
}

const _decisionsListEl = document.getElementById('decisions-list');
if (_decisionsListEl) {
  _decisionsListEl.addEventListener('click', async (e) => {
    const del = e.target.closest('.del');
    if (!del) return;
    const text = del.dataset.text;
    if (!text) return;
    const cmd = `/hams:audit-decisions remove "${escapeForSlashCommand(text)}"`;
    const ok = await copyToClipboard(cmd);
    if (ok) {
      showToast('복사됨 — Claude 세션에 붙여넣어 실행');
    } else {
      showToast('복사 실패 — 콘솔에서 복사하세요');
      console.log('COPY THIS:', cmd);
    }
  });
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
      const escapedAttr = it.body.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      html += `<div class="decision-item">
        <span class="text">${DOMPurify.sanitize(it.body)}</span>
        <span class="del" data-text="${escapedAttr}" title="제거">×</span>
      </div>`;
    }
  }
  el.innerHTML = html;
}

async function renderMockupsList(mockupFilenames, uuid, dataPath) {
  const el = document.getElementById('mockups-list');
  if (!el) return; // page doesn't have mockups column (e.g., index.html)
  if (!mockupFilenames || mockupFilenames.length === 0) {
    renderEmpty(el, '목업 없음');
    return;
  }

  let metaIdx = {};
  try {
    metaIdx = await fetchJSON(`${dataPath}/mockups/_index.json`);
  } catch {}

  let html = '';
  for (const fname of mockupFilenames) {
    const meta = metaIdx[fname] || {};
    const title = meta.title || fname;
    const url = `${dataPath}/mockups/${fname}`;
    html += `<a href="${url}" target="_blank" class="mockup-item">
      <div class="mockup-title">${DOMPurify.sanitize(title)}</div>
      <div class="mockup-meta">${DOMPurify.sanitize(meta.description || fname)}</div>
    </a>`;
  }
  el.innerHTML = html;
}

async function load() {
  const path = window.location.pathname;

  // Sub-F: /p/{uuid}/... → per-project view
  const projectMatch = path.match(/\/p\/([^/]+)\//);
  if (projectMatch) {
    await loadProject(projectMatch[1]);
    return;
  }

  // Default: project list (index.html)
  await loadProjectList();
}


async function loadProjectList() {
  let rootManifest;
  try {
    rootManifest = await fetchJSON(`data/manifest.json`);
  } catch (e) {
    const el = document.getElementById('projects-list');
    if (el) renderEmpty(el,
      'hamstern-data 가 아직 publish 안 됨.<br>'
      + 'Claude 세션에서 <code>/hams:dashboard --publish</code> 호출 후 재방문.');
    return;
  }
  setGenerated(rootManifest.generated_at);

  const projects = Object.entries(rootManifest.projects || {})
    .sort((a, b) => (b[1].last_active || '').localeCompare(a[1].last_active || ''));

  const el = document.getElementById('projects-list');
  if (!el) return;

  if (projects.length === 0) {
    renderEmpty(el, '프로젝트 없음. <code>/hams:init "이름"</code> 으로 첫 프로젝트 생성.');
    return;
  }

  el.innerHTML = projects.map(([uuid, info]) => `
    <a href="p/${encodeURIComponent(uuid)}/" class="project-card">
      <div class="project-name">${DOMPurify.sanitize(info.name)}</div>
      <div class="project-meta">
        decisions: ${info.decision_count} · sessions: ${info.session_count} · mockups: ${info.mockup_count}
      </div>
      <div class="project-last">last: ${info.last_active || '—'}</div>
    </a>
  `).join('');

  // Search filter
  const searchInput = document.getElementById('search');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.toLowerCase();
      document.querySelectorAll('.project-card').forEach(card => {
        const visible = card.textContent.toLowerCase().includes(q);
        card.style.display = visible ? '' : 'none';
      });
    });
  }
}


async function loadProject(uuid) {
  // Per-project view uses data path relative to docs/p/{uuid}/index.html
  const dataPath = `../../data/p/${encodeURIComponent(uuid)}`;
  window._currentDataPath = dataPath;

  let manifest;
  try {
    manifest = await fetchJSON(`${dataPath}/manifest.json`);
  } catch (e) {
    const el = document.getElementById('decisions-list');
    if (el) renderEmpty(el,
      'Dashboard 데이터 미생성.<br>Claude 세션에서 <code>/hams:dashboard --publish</code> 호출 후 재방문.');
    return;
  }
  setGenerated(manifest.generated_at);

  if (manifest.decisions) {
    const md = await fetchText(`${dataPath}/decisions.md`);
    renderDecisions(md);
  } else {
    const el = document.getElementById('decisions-list');
    if (el) renderEmpty(el, '결정사항 없음');
  }

  renderSessionsList(manifest.sessions || []);

  if (manifest.decisions_log) {
    const logMd = await fetchText(`${dataPath}/decisions-log.md`);
    renderLog(logMd);
  } else {
    const el = document.getElementById('log-list');
    if (el) renderEmpty(el, '로그 없음');
  }

  // Sub-F: mockups column
  await renderMockupsList(manifest.mockups || [], uuid, dataPath);
}

function activateTab(name) {
  document.querySelectorAll('nav.tabs button').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === name);
  });
  document.querySelectorAll('.col').forEach(c => {
    c.classList.toggle('active', c.dataset.tab === name);
  });
}

const _tabsEl = document.getElementById('tabs');
if (_tabsEl) {
  _tabsEl.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON' && e.target.dataset.tab) {
      activateTab(e.target.dataset.tab);
    }
  });
  activateTab('decisions');
}

load();
