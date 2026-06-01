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
  let html = '<div class="session-grid">';
  for (const name of sessions) {
    const short = name.replace(/^session_/, '').replace(/\.md$/, '');
    const dm = short.match(/^(\d{4}-\d{2}-\d{2})[-_]?(.*)$/);
    const date = dm ? dm[1] : '';
    const title = (dm && dm[2]) ? dm[2].replace(/[-_]+/g, ' ').trim() : short;
    const escapedAttr = name.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    html += `<div class="session-card" data-file="${escapedAttr}">
        ${date ? `<div class="sc-date">${date}</div>` : ''}
        <div class="sc-title">${DOMPurify.sanitize(title)}</div>
      </div>`;
  }
  html += '</div>';
  el.innerHTML = html;
  el.addEventListener('click', onSessionClick);
}

let currentSessionEl = null;
async function onSessionClick(e) {
  const item = e.target.closest('.session-card');
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

// 결정 박스(체인) 클릭 → 상세, 상세의 × → 제거 명령 복사.
// 상세 패널은 #decisions-list 밖(#decision-render)에 있으므로 document 위임으로 둘 다 잡는다.
document.addEventListener('click', async (e) => {
  const node = e.target.closest('.decision-node');
  if (node) {
    document.querySelectorAll('.decision-node.active').forEach(n => n.classList.remove('active'));
    node.classList.add('active');
    showDecisionDetail(Number(node.dataset.idx));
    return;
  }
  const del = e.target.closest('.del');
  if (!del) return;
  const text = del.dataset.text;
  if (!text) return;
  const uuid = window._currentUuid;
  const cmd = uuid
    ? `/hams:audit-decisions remove "${escapeForSlashCommand(text)}" --project-uuid ${uuid}`
    : `/hams:audit-decisions remove "${escapeForSlashCommand(text)}"`;  // fallback (single-project legacy view)
  const ok = await copyToClipboard(cmd);
  if (ok) {
    showToast('복사됨 — Claude 세션에 붙여넣어 실행');
  } else {
    showToast('복사 실패 — 콘솔에서 복사하세요');
    console.log('COPY THIS:', cmd);
  }
});

function parseDecisions(md) {
  // returns [{category, body, raw, session}] in document order (= append/history order)
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
      const sm = body.match(/<!--\s*session:\s*(\S+?)\s*-->/);
      const session = sm ? sm[1] : null;
      body = body.replace(/\s*<!--\s*session:\s*\S+?\s*-->\s*$/, '').trim();
      out.push({ category: currentCat, body, raw, session });
    }
  }
  return out;
}

function renderDecisions(md) {
  const el = document.getElementById('decisions-list');
  const render = document.getElementById('decision-render');
  if (!md || !md.trim()) {
    renderEmpty(el, '결정사항 없음<br><small>/hams:record 로 추가 가능</small>');
    if (render) render.innerHTML = '';
    return;
  }
  const items = parseDecisions(md);
  if (items.length === 0) {
    renderEmpty(el, '결정사항 없음');
    if (render) render.innerHTML = '';
    return;
  }
  window._decisionItems = items;
  // 문서 순서 = append 순서 = 히스토리. 박스를 → 로 이어 체인으로 표시.
  let html = '<div class="chain">';
  items.forEach((it, i) => {
    const escapedAttr = it.body.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    html += `<div class="decision-node" data-idx="${i}" data-text="${escapedAttr}">
        <div class="node-head">
          <span class="node-num">#${i + 1}</span>
          <span class="node-cat">${DOMPurify.sanitize(it.category)}</span>
        </div>
        <div class="node-text">${DOMPurify.sanitize(marked.parseInline(it.body))}</div>
      </div>`;
    if (i < items.length - 1) html += `<span class="chain-link" aria-hidden="true">→</span>`;
  });
  html += '</div>';
  el.innerHTML = html;
  if (render) render.innerHTML = '<div class="empty">결정 박스를 클릭하면 상세가 표시됩니다</div>';
}

function showDecisionDetail(idx) {
  const items = window._decisionItems || [];
  const it = items[idx];
  const render = document.getElementById('decision-render');
  if (!it || !render) return;
  const escapedAttr = it.body.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
  let sessionHtml = '';
  if (it.session) {
    const short = it.session.replace(/^session_/, '').replace(/\.md$/, '');
    sessionHtml = `<div class="dd-row"><span class="dd-key">출처 세션</span><span class="dd-val">${DOMPurify.sanitize(short)}</span></div>`;
  }
  const bodyHtml = DOMPurify.sanitize(marked.parseInline(it.body));
  render.innerHTML = `<div class="decision-detail">
      <div class="dd-head">
        <span class="node-num">#${idx + 1}</span>
        <span class="node-cat">${DOMPurify.sanitize(it.category)}</span>
        <span class="del" data-text="${escapedAttr}" title="이 결정 제거">× 제거</span>
      </div>
      <div class="dd-body">${bodyHtml}</div>
      ${sessionHtml}
    </div>`;
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
  window._currentUuid = uuid;
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
