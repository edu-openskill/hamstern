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

// R1: 결정 목차 — 결정 클릭 → 그 결정이 나온 세션 상세(② 결정사항으로 스크롤),
// × → 제거(메커니즘 B: serve.py do_POST. 정적 모드 fallback = 클립보드 명령).
// .del 을 먼저 검사 (× 는 .toc-item 안에 있으므로 행 클릭과 충돌 방지).
document.addEventListener('click', async (e) => {
  const del = e.target.closest('.del');
  if (del) {
    const text = del.dataset.text;
    if (text) await removeDecision(text);
    return;
  }
  const item = e.target.closest('.toc-item');
  if (item) {
    document.querySelectorAll('.toc-item.active').forEach(n => n.classList.remove('active'));
    item.classList.add('active');
    showDecisionSession(item.dataset.session || '', item.dataset.dindex || '');
    return;
  }
});

// 삭제: 로컬 서버(serve.py do_POST) 가 있으면 서버사이드 삭제+커밋+push,
// 없으면(publish 정적) 클립보드 명령으로 graceful fallback.
async function removeDecision(text) {
  const uuid = window._currentUuid;
  try {
    const r = await fetch('/api/remove-decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uuid, text }),
    });
    if (r.ok) {
      const data = await r.json();
      if (data && data.ok) {
        showToast('삭제됨 — GitHub 반영' + (data.pushed ? ' 완료' : ' 대기(오프라인)'));
        if (window._currentDataPath) await reloadDecisions();
        return;
      }
      throw new Error((data && data.error) || 'remove failed');
    }
    throw new Error('no server endpoint');
  } catch {
    // fallback: 정적 호스팅(gh-pages) — 서버 없음 → 클립보드 명령
    const cmd = uuid
      ? `/hams:audit-decisions remove "${escapeForSlashCommand(text)}" --project-uuid ${uuid}`
      : `/hams:audit-decisions remove "${escapeForSlashCommand(text)}"`;
    const ok = await copyToClipboard(cmd);
    showToast(ok ? '복사됨 — Claude 세션에 붙여넣어 실행' : '복사 실패 — 콘솔 확인');
    if (!ok) console.log('COPY THIS:', cmd);
  }
}

async function reloadDecisions() {
  try {
    const md = await fetchText(`${window._currentDataPath}/decisions.md`);
    renderDecisions(md);
  } catch { /* keep current view */ }
}

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
      // 마커 형식: {session_id} 또는 {session_id}#{dIndex} (d번호 = 세션 내 ADR D번호)
      let session = null, dindex = null;
      if (sm) {
        const hash = sm[1].indexOf('#');
        session = hash >= 0 ? sm[1].slice(0, hash) : sm[1];
        if (hash >= 0) dindex = sm[1].slice(hash + 1);
      }
      body = body.replace(/\s*<!--\s*session:\s*\S+?\s*-->\s*$/, '').trim();
      out.push({ category: currentCat, body, raw, session, dindex });
    }
  }
  return out;
}

function renderDecisions(md) {
  const el = document.getElementById('decisions-toc');
  const pane = document.getElementById('decision-session');
  if (!el) return;
  if (!md || !md.trim()) {
    renderEmpty(el, '결정사항 없음<br><small>/hams:context-save 로 추가</small>');
    if (pane) renderEmpty(pane, '결정을 클릭하면 그 결정이 나온 세션이 여기 표시됩니다');
    return;
  }
  const items = parseDecisions(md);
  if (items.length === 0) {
    renderEmpty(el, '결정사항 없음');
    if (pane) renderEmpty(pane, '결정을 클릭하면 그 결정이 나온 세션이 여기 표시됩니다');
    return;
  }
  // R1 목차: 카테고리별 묶되 "무엇을 결정했나" 추적용 순번 목록. 화살표 없음.
  const byCat = new Map();
  for (const it of items) {
    if (!byCat.has(it.category)) byCat.set(it.category, []);
    byCat.get(it.category).push(it);
  }
  let n = 0;
  let html = '';
  for (const [cat, list] of byCat) {
    html += `<div class="toc-cat">${DOMPurify.sanitize(cat)}</div>`;
    for (const it of list) {
      n++;
      const escapedAttr = it.body.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      const sess = (it.session || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      const dindex = (it.dindex || '').replace(/[^0-9]/g, '');
      html += `<div class="toc-item" data-session="${sess}" data-dindex="${dindex}" data-text="${escapedAttr}" title="클릭 → 출처 세션">
          <span class="toc-num">${n}</span>
          <span class="toc-text">${DOMPurify.sanitize(marked.parseInline(it.body))}</span>
          <span class="del" data-text="${escapedAttr}" title="이 결정 제거">×</span>
        </div>`;
    }
  }
  el.innerHTML = html;
  if (pane) renderEmpty(pane, '결정을 클릭하면 그 결정이 나온 세션이 여기 표시됩니다');
}

// R1: 결정 클릭 → 출처 세션 distill 렌더 + 그 결정의 ADR(D{dIndex}) 블록으로 스크롤(c).
// dIndex 없으면(구 데이터) ② 결정사항 섹션 헤딩으로 fallback(b).
async function showDecisionSession(sessionFile, dIndex) {
  const pane = document.getElementById('decision-session');
  if (!pane) return;
  if (!sessionFile) {
    renderEmpty(pane, '이 결정의 출처 세션 정보가 없습니다');
    return;
  }
  pane.innerHTML = '<em>loading…</em>';
  // decisions.md 의 session 마커는 확장자 없는 SESSION_ID — 실제 파일은 {id}.md
  const file = /\.md$/.test(sessionFile) ? sessionFile : `${sessionFile}.md`;
  try {
    const md = await fetchText(`${window._currentDataPath || DATA_PATH}/sessions/${file}`);
    pane.innerHTML = DOMPurify.sanitize(marked.parse(md));

    let target = null;
    const k = parseInt(dIndex, 10);
    if (k > 0) {
      // ADR 헤딩 "### Dk. ..." 매칭 (정확 → 그 결정 블록). 없으면 k번째 h3.
      const re = new RegExp('^\\s*D' + k + '\\b');
      const hs = pane.querySelectorAll('h1, h2, h3, h4');
      hs.forEach((h) => { if (!target && re.test(h.textContent)) target = h; });
      if (!target) {
        const h3s = pane.querySelectorAll('h3');
        if (h3s.length >= k) target = h3s[k - 1];
      }
    }
    if (!target) {
      // fallback(b): ② 결정사항 섹션 헤딩
      pane.querySelectorAll('h1, h2, h3').forEach((h) => {
        if (!target && /결정사항|②/.test(h.textContent)) target = h;
      });
    }
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      target.classList.add('dd-highlight');
      setTimeout(() => target.classList.remove('dd-highlight'), 1600);
    } else {
      pane.scrollTop = 0;
    }
  } catch {
    renderEmpty(pane, `세션 로드 실패: ${sessionFile}`);
  }
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

function renderSsotList(ssot) {
  const el = document.getElementById('ssot-list');
  if (!el) return; // page doesn't have ssot column
  if (!ssot || ssot.length === 0) {
    renderEmpty(el, 'SSOT 문서 없음');
    return;
  }
  let html = '';
  for (const e of ssot) {
    const icon = e.kind === 'glob' ? '📁' : '📄';
    const label = DOMPurify.sanitize(e.label);
    if (e.url && /^https?:\/\//.test(e.url)) {
      const url = DOMPurify.sanitize(e.url);
      html += `<a href="${url}" target="_blank" rel="noopener noreferrer" class="ssot-item">${icon} ${label}</a>`;
    } else {
      html += `<div class="ssot-item ssot-nolink">${icon} ${label}</div>`;
    }
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
    const el = document.getElementById('decisions-toc');
    if (el) renderEmpty(el,
      'Dashboard 데이터 미생성.<br>Claude 세션에서 <code>/hams:dashboard --publish</code> 호출 후 재방문.');
    return;
  }
  setGenerated(manifest.generated_at);

  if (manifest.decisions) {
    const md = await fetchText(`${dataPath}/decisions.md`);
    renderDecisions(md);
  } else {
    const el = document.getElementById('decisions-toc');
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
  renderSsotList(manifest.ssot);
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
