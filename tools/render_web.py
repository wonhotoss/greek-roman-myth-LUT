"""build/myth.json -> build/myth.html

혼자 탐색하는 단일 파일 페이지. 인터넷 없이 열린다. 데이터는 HTML 안에 박아 넣는다.
다섯 가지로 찾는다 — 언제 어디서(시간축 커서 + 반응하는 지도), 시간순(연표),
지리(실제 지도 + 우주 도해), 인물(계보), 이야기 묶음.

내부 필드(note, sensitivity)는 그리지 않는다. 아이가 보는 화면이다.

    python tools/build.py && python tools/render_web.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "build" / "myth.json"
GEO = ROOT / "data" / "geo" / "mediterranean.json"
OUT = ROOT / "build" / "myth.html"

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>그리스 로마 신화 — 시간·땅·사람으로 찾아보기</title>
<style>
  :root {
    --bg: #fbf7ef; --panel: #fffdf8; --ink: #23201b; --dim: #6d6558;
    --line: #e2d9c8; --accent: #9a5b2c; --accent-soft: #f2e5d6;
    --e0:#3b4a6b; --e1:#4f6b8a; --e2:#8a6a2f; --e3:#6b7a3a; --e4:#9a5b2c;
    --e5:#8a3a3a; --e6:#6b3a5b; --e7:#3a6b62; --e8:#7a4a2a;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
    font-size:16px; line-height:1.7; }
  header { position:sticky; top:0; z-index:20; background:var(--bg);
    border-bottom:1px solid var(--line); padding:10px 16px 0; }
  h1 { margin:0 0 8px; font-size:19px; letter-spacing:-.02em; }
  h1 span { color:var(--dim); font-weight:400; font-size:14px; margin-left:8px; }
  .bar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  input[type=search] { flex:1 1 220px; min-width:0; padding:9px 12px; font-size:16px;
    border:1px solid var(--line); border-radius:9px; background:var(--panel); color:var(--ink);
    font-family:inherit; }
  .tabs { display:flex; gap:4px; margin:8px 0 0; overflow-x:auto; }
  .tabs button { border:0; background:none; padding:9px 13px; font-size:15px; cursor:pointer;
    color:var(--dim); border-bottom:3px solid transparent; white-space:nowrap;
    font-family:inherit; }
  .tabs button[aria-selected=true] { color:var(--ink); border-bottom-color:var(--accent);
    font-weight:600; }
  main { display:grid; grid-template-columns:minmax(0,1fr) 380px; gap:20px;
    max-width:1400px; margin:0 auto; padding:18px 16px 60px; align-items:start; }
  @media (max-width:900px) { main { grid-template-columns:minmax(0,1fr); }
    #side { position:static; max-height:none; } }

  .era { margin:0 0 26px; }
  .era-head { display:flex; align-items:baseline; gap:10px; margin-bottom:8px;
    border-bottom:2px solid var(--line); padding-bottom:4px; }
  .era-n { font-size:12px; font-weight:700; color:#fff; background:var(--eracolor);
    border-radius:20px; padding:2px 9px; }
  .era-name { font-size:17px; font-weight:700; }
  .era-one { font-size:13px; color:var(--dim); }
  .chips { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { border:1px solid var(--line); background:var(--panel); border-radius:8px;
    padding:7px 11px; font-size:15px; cursor:pointer; text-align:left; color:var(--ink);
    font-family:inherit; line-height:1.35; }
  .chip:hover { border-color:var(--accent); background:var(--accent-soft); }
  .chip.on { border-color:var(--accent); background:var(--accent-soft); font-weight:600; }
  .chip small { color:var(--dim); font-size:12px; }
  .sub { font-size:12px; color:var(--dim); margin:12px 0 5px; letter-spacing:.02em; }
  .flow { display:flex; flex-direction:column; gap:5px; }
  .flow .chip { display:flex; gap:9px; align-items:baseline; }
  .flow .chip b { font-weight:600; }
  .flow .chip span { color:var(--dim); font-size:13px; }

  #side { position:sticky; top:118px; max-height:calc(100vh - 140px); overflow:auto;
    display:flex; flex-direction:column; gap:12px; }
  #now, #detail { background:var(--panel); border:1px solid var(--line);
    border-radius:12px; padding:16px 17px; }
  /* 좁은 칸이라 이름과 설명을 위아래로 쌓는다. 나란히 두면 이름이 잘린다. */
  #now { flex:0 0 auto; position:sticky; top:0; z-index:2; max-height:52%; overflow:auto; }
  #now .flow .chip { display:block; }
  #now .flow .chip b { display:block; }
  #now .flow .chip span { display:block; margin-top:1px; }
  #detail h2 { margin:0; font-size:22px; }
  #detail .alt { color:var(--dim); font-size:13px; margin:3px 0 10px; }
  .badges { display:flex; gap:5px; flex-wrap:wrap; margin-bottom:10px; }
  .badge { font-size:12px; padding:2px 8px; border-radius:20px; background:var(--accent-soft);
    color:var(--accent); }
  #detail .one { font-weight:600; margin:0 0 8px; }
  #detail .body { white-space:pre-line; margin:0 0 12px; }
  .fun { background:#fff8e6; border-left:3px solid #d9a640; padding:9px 11px; font-size:14px;
    border-radius:0 7px 7px 0; margin:0 0 12px; }
  .variant { background:#f2f5f8; border-left:3px solid #7d94ab; padding:9px 11px; font-size:14px;
    border-radius:0 7px 7px 0; margin:0 0 10px; }
  .variant b { display:block; font-size:12px; color:var(--dim); font-weight:600; }
  .rel { margin:0 0 10px; }
  .rel .sub { margin:10px 0 4px; }
  .src { font-size:12px; color:var(--dim); border-top:1px solid var(--line); margin-top:14px;
    padding-top:9px; }
  .src li { margin-bottom:2px; }
  .src ul { margin:4px 0 0; padding-left:18px; }
  .empty { color:var(--dim); }

  svg { width:100%; height:auto; display:block; background:var(--panel);
    border:1px solid var(--line); border-radius:12px; }
  .land { fill:#efe6d3; stroke:#cfc0a4; stroke-width:.06; }
  .sea { fill:#dfe9ef; }
  .dot { fill:var(--accent); stroke:#fff; stroke-width:.05; cursor:pointer; }
  .dot:hover, .dot.on { fill:#c8791f; }
  .plabel { fill:var(--ink); cursor:pointer; }
  .band { stroke:none; }
  .bandlabel { fill:var(--dim); }
  .tree { font-size:15px; }
  .tree ul { list-style:none; margin:0; padding-left:17px; border-left:1px dotted var(--line); }
  .tree > ul { padding-left:0; border:0; }
  .tree li { margin:2px 0; }
  .tree button { border:0; background:none; cursor:pointer; font-size:15px; padding:2px 5px;
    border-radius:6px; color:var(--ink); font-family:inherit; text-align:left; }
  .tree button:hover { background:var(--accent-soft); }
  .tree button.on { background:var(--accent-soft); font-weight:600; }
  .tree .k { color:var(--dim); font-size:12px; }
  .hint { font-size:13px; color:var(--dim); margin:0 0 12px; }
  .seg { display:inline-flex; gap:0; margin:0 0 12px; border:1px solid var(--line);
    border-radius:9px; overflow:hidden; }
  .seg button { border:0; background:var(--panel); padding:7px 14px; font-size:14px;
    cursor:pointer; color:var(--dim); font-family:inherit; }
  .seg button[aria-selected=true] { background:var(--accent-soft); color:var(--accent);
    font-weight:600; }
  .card { border:1px solid var(--line); background:var(--panel); border-radius:11px;
    padding:14px 15px; margin-bottom:14px; }
  .card h3 { margin:0 0 3px; font-size:17px; }
  .card p { margin:0 0 10px; color:var(--dim); font-size:14px; }

  /* 언제 어디서 — 커서로 훑는 시간축 */
  #tl { touch-action:none; cursor:ew-resize; user-select:none; }
  #tl:focus { outline:2px solid var(--accent); outline-offset:2px; }
  .bar { cursor:pointer; }
  .bar rect { stroke:#fff; stroke-width:1; }
  .bar.off rect { opacity:.22; }
  .bar.off .blabel { opacity:.35; }
  .bar.hot rect { stroke:#23201b; stroke-width:1.6; }
  .blabel { font-size:12px; fill:#fff; pointer-events:none; font-weight:600; }
  .blabel.dark { fill:var(--ink); }
  .opentail { stroke-dasharray:5 4; stroke-width:3; fill:none; }
  .opentail.off { opacity:.22; }
  .erab { opacity:.16; }
  .eralab { font-size:12px; fill:var(--dim); pointer-events:none; }
  .arcname { font-size:11px; fill:var(--dim); pointer-events:none; }
  .rowbg { fill:#000; opacity:.022; }
  .cursor line { stroke:var(--accent); stroke-width:2.5; }
  .cursor polygon { fill:var(--accent); }
  #now .sub { margin:0 0 7px; }
  .maps { display:flex; gap:12px; align-items:flex-start; }
  .maps > div:first-child { flex:1.5 1 0; min-width:0; }
  .maps > div:last-child { flex:1 1 0; min-width:0; }
  .maps h4 { margin:0 0 5px; font-size:13px; color:var(--dim); font-weight:600; }
  .dot.off { opacity:.25; }
  .plabel.off { opacity:.3; }
  @media (max-width:700px) { .maps { flex-direction:column; } }
</style>
</head>
<body>
<header>
  <h1>그리스 로마 신화<span>시간·땅·사람으로 찾아보기</span></h1>
  <div class="bar">
    <input type="search" id="q" placeholder="이름을 넣어 보세요. 주피터, 헤르쿨레스처럼 다른 이름도 찾습니다." autocomplete="off">
  </div>
  <div class="tabs" id="tabs" role="tablist"></div>
</header>
<main>
  <div id="view"></div>
  <aside id="side">
    <div id="now" hidden></div>
    <div id="detail"></div>
  </aside>
</main>
<script id="data" type="application/json">__DATA__</script>
<script id="geo" type="application/json">__GEO__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const GEO = JSON.parse(document.getElementById('geo').textContent);
const byId = {};
for (const k of ['figures','events','places','arcs']) for (const it of D[k]) { it._t = k; byId[it.id] = it; }
const srcById = {}; for (const s of D.sources) srcById[s.id] = s;
const eraById = {}; for (const e of D.eras) eraById[e.n] = e;

const KIND = { primordial:'첫 신', titan:'티탄', god:'올림포스 신', hero:'영웅',
  human:'사람', monster:'괴물', nymph:'님프', group:'무리' };
const el = (t, a = {}, ...kids) => {
  const n = document.createElement(t);
  for (const [k, v] of Object.entries(a)) {
    if (k === 'cls') n.className = v; else if (k === 'on') n.onclick = v;
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of kids.flat(Infinity)) if (c !== null && c !== undefined) n.append(c);
  return n;
};
const eraColor = n => `var(--e${n})`;

let sel = null, tab = 'when', mapMode = 'real';

function chip(id, extra) {
  const it = byId[id];
  if (!it) return null;
  const b = el('button', { cls: 'chip' + (sel === id ? ' on' : ''), on: () => select(id) },
    it.name_ko, extra ? el('small', {}, ' ' + extra) : null);
  return b;
}

/* ---------- 상세 ---------- */
function relRow(label, ids) {
  if (!ids || !ids.length) return null;
  return [el('div', { cls: 'sub' }, label), el('div', { cls: 'chips' }, ids.map(i => chip(i)))];
}
function sourceList(item) {
  if (!item.sources) return null;
  return el('div', { cls: 'src' }, '이 이야기가 적혀 있는 곳',
    el('ul', {}, item.sources.map(s => {
      const [sid, loc] = [s.split(' ')[0], s.split(' ').slice(1).join(' ')];
      const src = srcById[sid];
      return el('li', {}, `${src.author_ko} 『${src.title_ko}』 ${loc}  ·  ${src.written}`);
    })));
}
function detailFigure(f) {
  const alt = [f.name_grc && '그리스어 ' + f.name_grc, f.name_la && '로마 이름 ' + f.name_la,
    f.aka && f.aka.length && '다른 표기 ' + f.aka.join(', ')].filter(Boolean).join(' · ');
  const sibs = [...new Set((f.parents || []).flatMap(p =>
    (byId[p].children || []).filter(c => c !== f.id)))];
  return [
    el('h2', {}, f.name_ko),
    alt ? el('div', { cls: 'alt' }, alt) : null,
    el('div', { cls: 'badges' },
      el('span', { cls: 'badge' }, KIND[f.kind]),
      el('span', { cls: 'badge' }, eraById[f.era].name_ko),
      (f.domains || []).map(d => el('span', { cls: 'badge' }, d))),
    el('p', { cls: 'one' }, f.oneliner),
    el('div', { cls: 'body' }, f.body.trim()),
    f.fun ? el('div', { cls: 'fun' }, f.fun) : null,
    (f.parents_variant || []).map(v => el('div', { cls: 'variant' },
      el('b', {}, '다른 이야기도 있어'),
      v.text || ('부모를 ' + (v.parents || []).map(p => byId[p].name_ko).join(', ')
        + ' 라고 하는 이야기도 있어.'))),
    (f.symbols || []).length ? el('div', { cls: 'rel' },
      el('div', { cls: 'sub' }, '이 신을 알아보는 표시'),
      el('div', {}, f.symbols.join(', '))) : null,
    el('div', { cls: 'rel' },
      relRow('부모', f.parents), relRow('짝', f.spouses),
      relRow('형제', sibs), relRow('자식', f.children),
      f.home ? relRow('사는 곳', [f.home]) : null,
      f.events.length ? [el('div', { cls: 'sub' }, '나오는 이야기'),
        el('div', { cls: 'chips' }, f.events.map(e => chip(e.event, '· ' + e.role)))] : null),
    sourceList(f),
  ];
}
function detailEvent(e) {
  const pl = ('place' in e ? [e.place] : []).concat(e.places || []);
  return [
    el('h2', {}, e.name_ko),
    e.aka && e.aka.length ? el('div', { cls: 'alt' }, '다른 이름 ' + e.aka.join(', ')) : null,
    el('div', { cls: 'badges' },
      el('span', { cls: 'badge' }, eraById[e.era].name_ko),
      e.arc ? el('span', { cls: 'badge' }, byId[e.arc].name_ko) : null),
    el('p', { cls: 'one' }, e.oneliner),
    el('div', { cls: 'body' }, e.body.trim()),
    e.fun ? el('div', { cls: 'fun' }, e.fun) : null,
    (e.variants || []).map(v => el('div', { cls: 'variant' },
      el('b', {}, '다른 이야기도 있어'), v.text)),
    el('div', { cls: 'rel' },
      relRow('일어난 곳', pl),
      relRow('이 일이 있기 전에', e.caused_by),
      ...['주인공', '상대', '도움', '피해', '등장'].map(r => {
        const ids = e.cast.filter(c => c.role === r).map(c => c.figure);
        return ids.length ? relRow(r, ids) : null;
      })),
    sourceList(e),
  ];
}
function detailPlace(p) {
  return [
    el('h2', {}, p.name_ko),
    p.name_grc ? el('div', { cls: 'alt' }, '그리스어 ' + p.name_grc) : null,
    el('div', { cls: 'badges' },
      el('span', { cls: 'badge' }, p.kind === 'real' ? '실제로 있는 곳' : '이야기 속의 곳'),
      p.kind === 'real' ? el('span', { cls: 'badge' }, p.modern) : null),
    el('p', { cls: 'one' }, p.oneliner),
    el('div', { cls: 'body' }, p.body.trim()),
    p.fun ? el('div', { cls: 'fun' }, p.fun) : null,
    p.kind === 'real' ? el('div', { cls: 'rel' }, el('div', { cls: 'sub' }, '실제 위치'),
      el('div', {}, `북위 ${p.lat}, 동경 ${p.lon}`),
      el('a', { href: `https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=10/${p.lat}/${p.lon}`,
        target: '_blank', rel: 'noopener' }, '실제 지도에서 보기')) : null,
    el('div', { cls: 'rel' }, relRow('여기서 일어난 일', p.events)),
    sourceList(p),
  ];
}
function detailArc(a) {
  return [
    el('h2', {}, a.name_ko),
    el('div', { cls: 'badges' }, el('span', { cls: 'badge' }, eraById[a.era].name_ko),
      el('span', { cls: 'badge' }, '이야기 묶음')),
    el('p', { cls: 'one' }, a.oneliner),
    el('div', { cls: 'body' }, a.body.trim()),
    el('div', { cls: 'rel' }, el('div', { cls: 'sub' }, '이야기 순서'),
      el('div', { cls: 'flow' }, a.events.map((id, i) =>
        el('button', { cls: 'chip' + (sel === id ? ' on' : ''), on: () => select(id) },
          el('b', {}, (i + 1) + '. ' + byId[id].name_ko),
          el('span', {}, byId[id].oneliner))))),
    sourceList(a),
  ];
}
function drawDetail() {
  const d = document.getElementById('detail');
  d.replaceChildren();
  if (!sel) {
    d.append(el('p', { cls: 'empty' }, tab === 'when'
      ? '위에서 이야기를 눌러 보세요. 여기에 내용이 나옵니다.'
      : '왼쪽에서 무엇이든 눌러 보세요. 사람, 사건, 장소가 서로 이어져 있습니다.'));
    return;
  }
  const it = byId[sel];
  const fn = { figures: detailFigure, events: detailEvent, places: detailPlace, arcs: detailArc }[it._t];
  d.append(...fn(it).flat(Infinity).filter(Boolean));
  d.scrollTop = 0;
}
function select(id) {
  sel = id;
  const it = byId[id];
  /* 사건을 고르면 커서를 그 구간 안으로 옮긴다. 지도와 시간축이 어긋나지 않게. */
  if (it._t === 'events' && !(cursor >= it.t0 && cursor <= it.t1)) cursor = it.t0;
  followPlace();
  writeHash();
  drawDetail();
  drawView();
}
/* 이야기 속의 곳을 고르면 지도도 그쪽으로 바뀐다. 실제 지도에 없는 곳을 찾게 두지 않는다. */
function followPlace() {
  const it = sel && byId[sel];
  if (it && it._t === 'places') mapMode = it.kind === 'real' ? 'real' : 'cosmos';
}
/* 주소에 지금 보고 있는 것을 남긴다 — 다시 열거나 보내 줄 수 있게. 형태: #지도 또는 #연표:zeus */
const TABNAME = { when:'언제어디서', time:'연표', map:'지도', tree:'계보', arcs:'이야기', all:'모두' };
const TABKEY = Object.fromEntries(Object.entries(TABNAME).map(([k,v]) => [v,k]));
function writeHash() {
  const h = TABNAME[tab] + (tab === 'when' && cursor !== null ? '@' + Math.round(cursor) : '')
    + (sel ? ':' + sel : '');
  if (location.hash.slice(1) !== h) history.replaceState(null, '', '#' + h);
}
function readHash() {
  const [head, id] = decodeURIComponent(location.hash.slice(1)).split(':');
  const [tname, cur] = head.split('@');
  if (cur !== undefined && cur !== '' && !isNaN(+cur)) cursor = +cur;
  if (TABKEY[tname]) tab = TABKEY[tname];
  else if (byId[tname]) { sel = tname; followPlace(); return; }  /* 옛 형태(#zeus)도 받아 준다 */
  if (id && byId[id]) sel = id;
  followPlace();
}

/* ---------- 연표 ---------- */
function viewTime() {
  const v = [el('p', { cls: 'hint' },
    '신화에는 연도가 없습니다. 대신 누가 누구의 부모인지로 순서를 알 수 있습니다. 그 순서를 아홉 시대로 나눈 것입니다.')];
  for (const era of D.eras) {
    const evs = D.events.filter(e => e.era === era.n);
    const figs = D.figures.filter(f => f.era === era.n);
    if (!evs.length && !figs.length) continue;
    v.push(el('section', { cls: 'era', style: `--eracolor:${eraColor(era.n)}` },
      el('div', { cls: 'era-head' },
        el('span', { cls: 'era-n' }, era.n),
        el('span', { cls: 'era-name' }, era.name_ko),
        el('span', { cls: 'era-one' }, era.oneliner)),
      evs.length ? [el('div', { cls: 'sub' }, '일어난 일'),
        el('div', { cls: 'flow' }, evs.map(e =>
          el('button', { cls: 'chip' + (sel === e.id ? ' on' : ''), on: () => select(e.id) },
            el('b', {}, e.name_ko), el('span', {}, e.oneliner))))] : null,
      figs.length ? [el('div', { cls: 'sub' }, '이때 나오는 사람과 신'),
        el('div', { cls: 'chips' }, figs.map(f => chip(f.id, KIND[f.kind])))] : null));
  }
  return v;
}

/* ---------- 지도 ---------- */
const SVGNS = 'http://www.w3.org/2000/svg';
const sv = (t, a = {}, ...kids) => {
  const n = document.createElementNS(SVGNS, t);
  for (const [k, val] of Object.entries(a)) {
    if (k === 'cls') n.setAttribute('class', val);
    else if (k === 'on') n.onclick = val;
    else if (val !== null && val !== undefined) n.setAttribute(k, val);
  }
  for (const c of kids.flat(Infinity)) if (c) n.append(c);
  return n;
};
function mapReal(hi, reg) {
  const real = D.places.filter(p => p.kind === 'real');
  const b = GEO.box, K = Math.cos((b.lat0 + b.lat1) / 2 * Math.PI / 180);
  const X = lon => (lon - b.lon0) * K, Y = lat => (b.lat1 - lat);

  /* 지금 데이터에 있는 곳들에 맞춰 지도를 자른다. 로마·콜키스가 들어오면 저절로 넓어진다. */
  const xs = real.map(p => X(p.lon)), ys = real.map(p => Y(p.lat));
  const pad = 2.2;
  let x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad;
  let y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  const minAspect = 1.35;  /* 너무 세로로 길면 가로를 늘린다 */
  if ((x1 - x0) / (y1 - y0) < minAspect) {
    const want = (y1 - y0) * minAspect, cx = (x0 + x1) / 2;
    x0 = cx - want / 2; x1 = cx + want / 2;
  }
  const W = x1 - x0, H = y1 - y0;
  const fs = H * 0.019, r = H * 0.009;

  const paths = GEO.rings.map(ring =>
    sv('path', { cls: 'land', d: 'M' + ring.map(([x, y]) => `${X(x).toFixed(2)},${Y(y).toFixed(2)}`).join('L') + 'Z' }));

  /* 이름표가 서로 겹치지 않게 아래로 밀어 둔다 */
  const labels = real.map(p => ({ p, x: X(p.lon), y: Y(p.lat) }))
    .sort((a, c) => a.y - c.y || a.x - c.x);
  const boxes = [];
  for (const L of labels) {
    L.lx = L.x + r * 1.8; L.ly = L.y + fs * 0.35;
    const w = L.p.name_ko.length * fs * 1.02;
    let guard = 0;
    while (boxes.some(o => Math.abs(o.ly - L.ly) < fs * 1.25
        && L.lx < o.lx + o.w && o.lx < L.lx + w) && guard++ < 12) {
      L.ly += fs * 1.1;
    }
    boxes.push({ lx: L.lx, ly: L.ly, w });
  }
  const marks = labels.flatMap(L => {
    const off = hi && !hi.has(L.p.id) ? ' off' : '';
    const dot = sv('circle', { cls: 'dot' + off + (sel === L.p.id ? ' on' : ''),
      cx: L.x, cy: L.y, r, on: () => select(L.p.id) });
    const lab = sv('text', { cls: 'plabel' + off, x: L.lx, y: L.ly, 'font-size': fs,
      on: () => select(L.p.id) }, L.p.name_ko);
    if (reg) reg[L.p.id] = [dot, lab];
    return [
      L.ly - L.y > fs * 0.8 ? sv('line', { x1: L.x, y1: L.y, x2: L.lx - r * .4, y2: L.ly - fs * .3,
        stroke: '#b9a888', 'stroke-width': r * .3 }) : null,
      dot, lab,
    ].filter(Boolean);
  });

  return sv('svg', { viewBox: `${x0.toFixed(2)} ${y0.toFixed(2)} ${W.toFixed(2)} ${H.toFixed(2)}` },
    sv('rect', { cls: 'sea', x: x0, y: y0, width: W, height: H }), paths, marks);
}
function mapCosmos(hi, reg) {
  const W = 30, H = 22;
  const fs = H * 0.026, r = H * 0.014;
  const bands = [['하늘', 0, .20, '#e8eef5'], ['땅', .20, .62, '#efe6d3'],
    ['땅속', .62, 1, '#ddd6cc']];
  const layers = bands.map(([name, a, z, fill]) => [
    sv('rect', { cls: 'band', x: 0, y: a * H, width: W, height: (z - a) * H, fill }),
    sv('text', { cls: 'bandlabel', x: .5, y: a * H + fs * 1.6, 'font-size': fs }, name)]);
  const pts = [];
  for (const p of D.places.filter(p => p.kind === 'mythic')) {
    const x = p.cx * W, y = p.cy * H;
    const off = hi && !hi.has(p.id) ? ' off' : '';
    const anchor = p.cx > .7 ? 'end' : 'start';
    const dot = sv('circle', { cls: 'dot' + off + (sel === p.id ? ' on' : ''), cx: x, cy: y, r,
      on: () => select(p.id) });
    const lab = sv('text', { cls: 'plabel' + off, x: x + (anchor === 'end' ? -r * 1.6 : r * 1.6),
      y: y + fs * .35, 'font-size': fs, 'text-anchor': anchor, on: () => select(p.id) }, p.name_ko);
    if (reg) reg[p.id] = [dot, lab];
    pts.push(dot, lab);
  }
  return sv('svg', { viewBox: `0 0 ${W} ${H}` }, layers, pts,
    sv('rect', { x: .15, y: .15, width: W - .3, height: H - .3, fill: 'none',
      stroke: '#7d94ab', 'stroke-width': .12, 'stroke-dasharray': '.5 .35' }));
}
function viewMap() {
  const seg = el('div', { cls: 'seg' },
    el('button', { 'aria-selected': mapMode === 'real', on: () => { mapMode = 'real'; drawView(); } }, '실제로 있는 곳'),
    el('button', { 'aria-selected': mapMode === 'cosmos', on: () => { mapMode = 'cosmos'; drawView(); } }, '이야기 속의 곳'));
  const hint = mapMode === 'real'
    ? '지금 가면 있는 곳입니다. 점을 누르면 무슨 일이 있었는지 나옵니다.'
    : '실제로는 없는 곳입니다. 그리스 사람들이 생각한 세계의 모양대로 놓았습니다. 둘레의 점선이 세계를 감는 강 오케아노스입니다.';
  const list = D.places.filter(p => p.kind === (mapMode === 'real' ? 'real' : 'mythic'));
  return [seg, el('p', { cls: 'hint' }, hint),
    mapMode === 'real' ? mapReal() : mapCosmos(),
    el('div', { cls: 'sub' }, '장소 목록'),
    el('div', { cls: 'chips' }, list.map(p => chip(p.id, p.kind === 'real' ? p.modern : null)))];
}

/* ---------- 언제 어디서 — 눈금 없는 시간축을 커서로 훑는다 ---------- */
let cursor = null, tlUpdate = null;

/* 줄 나누기: 이야기 묶음 하나가 한 덩이. 덩이 안에서 시간이 겹치는 사건은 하위 줄로 내린다.
   겹치는 것을 같은 줄에 두면 막대가 서로를 덮어 버린다. */
function laneOf() {
  const owned = new Set(D.arcs.flatMap(a => a.events));
  const groups = [...D.arcs].sort((x, y) => x.t0 - y.t0)
    .map(a => ({ arc: a, events: D.events.filter(e => a.events.includes(e.id)) }));
  const loose = D.events.filter(e => !owned.has(e.id));
  if (loose.length) groups.push({ arc: null, events: loose });

  const rows = [];
  for (const g of groups) {
    const lanes = [];
    for (const e of [...g.events].sort((a, b) => a.t0 - b.t0 || a.t1 - b.t1)) {
      let lane = lanes.find(L => L.every(o => o.t1 <= e.t0 || e.t1 <= o.t0));
      if (!lane) { lane = []; lanes.push(lane); }
      lane.push(e);
    }
    lanes.forEach((lane, i) => rows.push({ arc: i ? null : g.arc, events: lane }));
  }
  return rows;
}

function viewWhenWhere() {
  const T = D.axis.total, W = 1000, ROW = 37, TOP = 27;
  const rows = laneOf();
  const H = TOP + rows.length * ROW + 6;
  const x = t => t / T * W;
  if (cursor === null) cursor = D.events[0].t0;

  const kids = [];
  /* 시대 띠 */
  for (const era of D.eras) {
    const [a, b] = D.axis.eras[era.n];
    const w = x(b) - x(a);
    kids.push(sv('rect', { cls: 'erab', x: x(a), y: 0, width: Math.max(w, .5), height: H,
      fill: `var(--e${era.n})` }));
    const full = `${era.n}. ${era.name_ko}`;
    if (w > full.length * 12 + 8) kids.push(sv('text', { cls: 'eralab', x: x(a) + 4, y: 17 }, full));
    else if (w > 20) kids.push(sv('text', { cls: 'eralab', x: x(a) + 4, y: 17 }, String(era.n)));
  }
  /* 줄 배경과 막대 */
  const bars = {};
  rows.forEach((row, i) => {
    const y = TOP + i * ROW;
    if (i % 2) kids.push(sv('rect', { cls: 'rowbg', x: 0, y, width: W, height: ROW }));
    if (row.arc) kids.push(sv('text', { cls: 'arcname', x: x(row.arc.t0) + 2, y: y + 12 },
      row.arc.name_ko));
    for (const e of row.events) {
      const bx = x(e.t0), bw = Math.max(x(e.t1) - x(e.t0), 5);
      const g = sv('g', { cls: 'bar', on: () => { cursor = e.t0; select(e.id); } },
        sv('title', {}, `${e.name_ko} — ${e.span_label}`),
        sv('rect', { x: bx, y: y + 17, width: bw, height: 16, rx: 3.5,
          fill: `var(--e${e.era})` }),
        e.open ? sv('path', { cls: 'opentail', d: `M${bx + bw} ${y + 25}L${W} ${y + 25}`,
          stroke: `var(--e${e.era})` }) : null,
        bw > e.name_ko.length * 12 + 12
          ? sv('text', { cls: 'blabel', x: bx + 5, y: y + 29 }, e.name_ko) : null);
      bars[e.id] = g;
      kids.push(g);
    }
  });
  /* 커서 */
  const cur = sv('g', { cls: 'cursor' },
    sv('line', { x1: 0, y1: 0, x2: 0, y2: H }),
    sv('polygon', { points: '-7,0 7,0 0,11' }));
  kids.push(cur);

  const svg = sv('svg', { id: 'tl', viewBox: `-8 0 ${W + 16} ${H}`, tabindex: 0,
    role: 'slider', 'aria-label': '시간축 커서' }, kids);

  const now = document.getElementById('now');
  const reg = {};
  const maps = el('div', { cls: 'maps' },
    el('div', {}, el('h4', {}, '실제로 있는 곳'), mapReal(new Set(), reg)),
    el('div', {}, el('h4', {}, '이야기 속의 곳'), mapCosmos(new Set(), reg)));

  tlUpdate = () => {
    cursor = Math.max(0, Math.min(T, cursor));
    cur.setAttribute('transform', `translate(${x(cursor)},0)`);
    const live = D.events.filter(e => e.t0 <= cursor && cursor <= e.t1);
    const ids = new Set(live.map(e => e.id));
    const hot = new Set();
    for (const e of live)
      for (const pid of ('place' in e ? [e.place] : []).concat(e.places || [])) hot.add(pid);
    for (const [id, g] of Object.entries(bars)) {
      g.classList.toggle('off', !ids.has(id));
      g.classList.toggle('hot', id === sel);
      const tail = g.querySelector('.opentail');
      if (tail) tail.classList.toggle('off', !ids.has(id));
    }
    for (const [pid, pair] of Object.entries(reg)) {
      pair[0].classList.toggle('off', !hot.has(pid));
      pair[1].classList.toggle('off', !hot.has(pid));
    }
    now.replaceChildren(
      el('div', { cls: 'sub' }, live.length
        ? `여기서 벌어지고 있는 이야기 ${live.length}개`
        : '이 자리에는 아직 넣은 이야기가 없습니다'),
      el('div', { cls: 'flow' }, live.map(e =>
        el('button', { cls: 'chip' + (sel === e.id ? ' on' : ''), on: () => select(e.id) },
          el('b', {}, e.name_ko),
          el('span', {}, `${e.span_label} · ${eraById[e.era].name_ko}${e.open ? ' · 끝나지 않는다' : ''}`)))));
    writeHash();
  };

  const fromEvent = ev => {
    const box = svg.getBoundingClientRect();
    const ux = (ev.clientX - box.left) / box.width * (W + 16) - 8;
    cursor = ux / W * T;
    tlUpdate();
  };
  let dragging = false;
  svg.addEventListener('pointerdown', ev => {
    dragging = true; svg.setPointerCapture(ev.pointerId); fromEvent(ev); svg.focus();
  });
  svg.addEventListener('pointermove', ev => { if (dragging) fromEvent(ev); });
  svg.addEventListener('pointerup', ev => {
    dragging = false; svg.releasePointerCapture(ev.pointerId);
  });
  svg.addEventListener('wheel', ev => {
    ev.preventDefault();
    cursor += (ev.deltaY > 0 ? 1 : -1) * Math.max(1, Math.round(T / 60));
    tlUpdate();
  }, { passive: false });
  svg.addEventListener('keydown', ev => {
    const step = ev.shiftKey ? 5 : 1;
    if (ev.key === 'ArrowRight') { cursor += step; tlUpdate(); ev.preventDefault(); }
    if (ev.key === 'ArrowLeft') { cursor -= step; tlUpdate(); ev.preventDefault(); }
  });

  setTimeout(tlUpdate, 0);
  return [
    el('p', { cls: 'hint' },
      '가로줄은 시간입니다. 다만 눈금이 없습니다 — 신화에는 연도가 없어서, 왼쪽에서 오른쪽으로 순서만 뜻합니다. '
      + '막대 길이도 실제 길이가 아니라 "한 순간"과 "여러 해"를 구별하는 정도입니다. '
      + '막대를 끌거나 굴려 커서를 옮기면, 그때 벌어지고 있는 이야기가 오른쪽에 나오고 아래 지도에 켜집니다. '
      + '점선으로 이어지는 막대는 끝나지 않거나 끝을 아직 모르는 이야기입니다.'),
    svg, maps,
  ];
}

/* ---------- 계보 ---------- */
function viewTree() {
  const placed = new Set();
  function node(f) {
    placed.add(f.id);
    const kids = (f.children || []).filter(c => !placed.has(c));
    kids.forEach(c => placed.add(c));
    return el('li', {},
      el('button', { cls: sel === f.id ? 'on' : '', on: () => select(f.id) },
        f.name_ko, el('span', { cls: 'k' }, ' ' + KIND[f.kind])),
      kids.length ? el('ul', {}, kids.map(c => node(byId[c]))) : null);
  }
  const size = {};
  const count = f => size[f.id] ?? (size[f.id] = 1 +
    (byId[f.id].children || []).reduce((n, c) => n + count(byId[c]), 0));
  const roots = D.figures.filter(f => !(f.parents || []).length)
    .sort((a, b) => a.era - b.era || count(a) - count(b) || a.name_ko.localeCompare(b.name_ko));
  const tops = roots.filter(f => !placed.has(f.id));
  const tree = el('div', { cls: 'tree' }, el('ul', {}, tops.map(f => node(f))));
  return [el('p', { cls: 'hint' },
    '위에서 아래로 부모 → 자식입니다. 맨 처음에는 부모가 없는 신이 여럿입니다. 카오스와 가이아는 서로의 부모가 아니라 각각 생겨났습니다. 부모가 둘인 경우 한쪽 아래에만 놓았습니다.'), tree];
}

/* ---------- 이야기 묶음 ---------- */
function viewArcs() {
  return [el('p', { cls: 'hint' }, '여러 사건이 하나의 이야기로 이어지는 것들입니다.'),
    ...D.arcs.map(a => el('div', { cls: 'card' },
      el('h3', {}, a.name_ko), el('p', {}, a.oneliner),
      el('div', { cls: 'flow' }, a.events.map((id, i) =>
        el('button', { cls: 'chip' + (sel === id ? ' on' : ''), on: () => select(id) },
          el('b', {}, (i + 1) + '. ' + byId[id].name_ko),
          el('span', {}, byId[id].oneliner))))))];
}

/* ---------- 모두 ---------- */
function viewAll() {
  const groups = [['god', '올림포스 신'], ['primordial', '첫 신'], ['titan', '티탄'],
    ['hero', '영웅'], ['human', '사람'], ['monster', '괴물'], ['nymph', '님프'], ['group', '무리']];
  return [el('p', { cls: 'hint' }, '종류별로 모아 놓은 것입니다.'),
    ...groups.map(([k, label]) => {
      const fs = D.figures.filter(f => f.kind === k);
      return fs.length ? el('section', { cls: 'era', style: '--eracolor:var(--e2)' },
        el('div', { cls: 'era-head' }, el('span', { cls: 'era-name' }, label),
          el('span', { cls: 'era-one' }, fs.length + '명')),
        el('div', { cls: 'chips' }, fs.map(f => chip(f.id)))) : null;
    }).filter(Boolean),
    el('section', { cls: 'era', style: '--eracolor:var(--e7)' },
      el('div', { cls: 'era-head' }, el('span', { cls: 'era-name' }, '원전'),
        el('span', { cls: 'era-one' }, '이 이야기들이 적혀 있는 옛 책')),
      el('div', { cls: 'flow' }, D.sources.map(s => el('div', { cls: 'chip' },
        el('b', {}, `${s.author_ko} 『${s.title_ko}』`),
        el('span', {}, ` ${s.title_orig} · ${s.written}`)))))];
}

/* ---------- 검색 ---------- */
function viewSearch(q) {
  const t = q.trim().toLowerCase();
  const hit = [];
  for (const k of ['figures', 'events', 'places', 'arcs']) for (const it of D[k]) {
    const hay = [it.name_ko, it.name_grc, it.name_la, ...(it.aka || []), it.oneliner]
      .filter(Boolean).join(' ').toLowerCase();
    if (hay.includes(t)) hit.push(it);
  }
  const TYPE = { figures: '사람·신', events: '사건', places: '장소', arcs: '이야기 묶음' };
  return [el('p', { cls: 'hint' }, `"${q.trim()}" — ${hit.length}개 찾았습니다.`),
    el('div', { cls: 'flow' }, hit.map(it =>
      el('button', { cls: 'chip' + (sel === it.id ? ' on' : ''), on: () => select(it.id) },
        el('b', {}, it.name_ko), el('span', {}, `${TYPE[it._t]} · ${it.oneliner}`))))];
}

/* ---------- 껍데기 ---------- */
const TABS = [['when', '언제 어디서'], ['time', '시간순'], ['map', '땅과 세계'], ['tree', '계보'],
  ['arcs', '이야기 묶음'], ['all', '모두']];
function drawTabs() {
  const t = document.getElementById('tabs');
  t.replaceChildren(...TABS.map(([k, label]) =>
    el('button', { role: 'tab', 'aria-selected': tab === k,
      on: () => { document.getElementById('q').value = ''; tab = k; writeHash(); drawView(); } }, label)));
}
function drawView() {
  drawTabs();
  const nowBox = document.getElementById('now');
  const q = document.getElementById('q').value;
  /* 지금 벌어지는 일 칸은 "언제 어디서" 탭에서만 쓴다 */
  if (tab !== 'when' || q.trim()) { nowBox.hidden = true; nowBox.replaceChildren(); tlUpdate = null; }
  else nowBox.hidden = false;
  const v = document.getElementById('view');
  const body = q.trim() ? viewSearch(q)
    : { when: viewWhenWhere, time: viewTime, map: viewMap, tree: viewTree,
        arcs: viewArcs, all: viewAll }[tab]();
  v.replaceChildren(...body.flat(Infinity).filter(Boolean));
}
document.getElementById('q').addEventListener('input', drawView);
window.addEventListener('hashchange', () => { readHash(); drawView(); drawDetail(); });
readHash();
drawView();
drawDetail();
</script>
</body>
</html>
"""


def main():
    data = BUNDLE.read_text(encoding="utf-8")
    geo = GEO.read_text(encoding="utf-8")
    # </script> 가 문자열 안에 들어가면 스크립트 태그가 끊긴다. JSON 에는 나올 일이 없지만 확인은 한다.
    for name, blob in (("myth.json", data), ("mediterranean.json", geo)):
        if "</script" in blob.lower():
            raise SystemExit(f"{name} 안에 </script 가 있다. 인라인할 수 없다.")
    html = HTML.replace("__DATA__", data).replace("__GEO__", geo)
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT).as_posix()} — {OUT.stat().st_size:,} bytes (단일 파일, 오프라인)")


if __name__ == "__main__":
    main()
