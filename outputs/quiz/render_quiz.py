"""db/build/myth.json -> outputs/quiz/quiz.html

그리스 로마 신화 퀴즈. 인물(신·괴물·영웅·사람)·장소·사물(상징물·맡은 일)을 맞추는 4지선다.
문제는 빌드 때 DB 에서 미리 뽑아 HTML 안에 넣는다 — 화면은 그 목록을 섞어 돌려 쓴다.
읽는 필드는 아이가 보는 것(name_ko·aka·kind·oneliner·fun·symbols·domains·parents·cast·place·modern)뿐이다.
note·record·sensitivity 는 읽지 않는다.

    python db/tools/build.py && python outputs/quiz/render_quiz.py
    python outputs/quiz/render_quiz.py --fragment <경로>   # 문서 뼈대 없이 본문만 (claude.ai 아티팩트용)

의존성 없음.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # 저장소 루트
BUNDLE = ROOT / "db" / "build" / "myth.json"
OUT = ROOT / "outputs" / "quiz" / "quiz.html"

SEED = 20261005          # 같은 DB 면 같은 문제 셋
N_CHOICES = 4

KIND_KO = {"god": "신", "titan": "티탄", "primordial": "태초의 신", "hero": "영웅", "human": "사람",
           "monster": "괴물", "nymph": "님프", "group": "무리"}
KIND_Q = {"god": "이 신은 누구?", "titan": "이 티탄은 누구?", "primordial": "이 태초의 신은 누구?",
          "hero": "이 영웅은 누구?", "human": "이 사람은 누구?", "monster": "이 괴물은 무엇?",
          "nymph": "이 님프는 누구?", "group": "이들은 누구?"}


def names_of(x):
    return [x["name_ko"]] + list(x.get("aka", []))


def mentions(text, x):
    """설명에 답의 이름이 들어 있으면 문제로 못 쓴다."""
    return any(n and n in text for n in names_of(x))


def pick(rng, pool, n, exclude):
    cand = [p for p in pool if p["id"] not in exclude]
    rng.shuffle(cand)
    return cand[:n]


def make(rng, cat, prompt, answer, distractors, explain, label=None):
    if len(distractors) < 2:
        return None
    opts = [answer] + distractors[:N_CHOICES - 1]
    rng.shuffle(opts)
    return {"cat": cat, "q": prompt, "choices": opts, "a": opts.index(answer), "x": explain or "",
            "label": label or ""}


def generate(D):
    rng = random.Random(SEED)
    F = {f["id"]: f for f in D["figures"]}
    P = {p["id"]: p for p in D["places"]}
    known = [f for f in D["figures"] if f["events"]]           # 사건에 나오는 인물만 — 이름만 있는 이는 뺀다
    by_kind = {}
    for f in known:
        by_kind.setdefault(f["kind"], []).append(f)
    qs = []

    # A. 인물 설명 → 이름
    for f in known:
        if mentions(f["oneliner"], f):
            continue
        pool = by_kind.get(f["kind"], [])
        if len(pool) < 3:
            pool = known
        ds = pick(rng, pool, N_CHOICES - 1, {f["id"]})
        q = make(rng, "figure", f["oneliner"], f["name_ko"], [d["name_ko"] for d in ds],
                 f.get("fun", ""), KIND_Q[f["kind"]])
        if q:
            qs.append(q)

    # B. 사건 → 주인공
    for e in D["events"]:
        heroes = [c["figure"] for c in e["cast"] if c["role"] == "주인공"]
        if len(heroes) != 1:
            continue
        f = F[heroes[0]]
        text = e["oneliner"]
        cast_ids = {c["figure"] for c in e["cast"]}
        if mentions(text, f) or mentions(e["name_ko"], f):
            continue
        pool = by_kind.get(f["kind"], known)
        ds = pick(rng, pool, N_CHOICES - 1, cast_ids)
        q = make(rng, "figure", text, f["name_ko"], [d["name_ko"] for d in ds],
                 f"{f['name_ko']} — {f['oneliner']}", "이 이야기의 주인공은 누구?")
        if q:
            qs.append(q)

    # C. 상징물 → 신, 신 → 상징물
    with_sym = [f for f in D["figures"] if f.get("symbols")]
    for f in with_sym:
        syms = f["symbols"]
        ds = pick(rng, with_sym, N_CHOICES - 1, {f["id"]})
        q = make(rng, "thing", "·".join(syms) + " — 이것이 상징인 신은?", f["name_ko"],
                 [d["name_ko"] for d in ds], f["oneliner"], "상징물")
        if q:
            qs.append(q)
        others = [s for d in with_sym if d["id"] != f["id"] for s in d["symbols"] if s not in syms]
        others = list(dict.fromkeys(others))
        rng.shuffle(others)
        q = make(rng, "thing", f"{f['name_ko']}의 상징은?", rng.choice(syms), others[:N_CHOICES - 1],
                 "·".join(syms) + " 모두 " + f["name_ko"] + "의 것이다.", "상징물")
        if q:
            qs.append(q)

    # D. 맡은 일 → 신
    with_dom = [f for f in D["figures"] if f.get("domains")]
    for f in with_dom:
        dom = f["domains"]
        pool = [d for d in with_dom if not set(d["domains"]) & set(dom)]
        ds = pick(rng, pool, N_CHOICES - 1, {f["id"]})
        q = make(rng, "thing", "·".join(dom) + " — 이것을 맡은 신은?", f["name_ko"],
                 [d["name_ko"] for d in ds], f["oneliner"], "맡은 일")
        if q:
            qs.append(q)

    # E. 부모
    for f in known:
        parents = [F[p] for p in f.get("parents", []) if p in F]
        if not parents:
            continue
        par = rng.choice(parents)
        pool = by_kind.get(par["kind"], known)
        ds = pick(rng, pool, N_CHOICES - 1, {f["id"], *f["parents"]})
        q = make(rng, "figure", f"{f['name_ko']}의 부모는 누구?", par["name_ko"],
                 [d["name_ko"] for d in ds], f"{par['name_ko']} — {par['oneliner']}", "계보")
        if q:
            qs.append(q)

    # F. 장소 설명 → 장소
    real = [p for p in D["places"] if p["kind"] == "real"]
    mythic = [p for p in D["places"] if p["kind"] == "mythic"]
    for p in D["places"]:
        if mentions(p["oneliner"], p):
            continue
        pool = real if p["kind"] == "real" else mythic
        ds = pick(rng, pool, N_CHOICES - 1, {p["id"]})
        x = p.get("fun") or (f"지금의 {p['modern']}." if p.get("modern") else "")
        q = make(rng, "place", p["oneliner"], p["name_ko"], [d["name_ko"] for d in ds], x,
                 "이곳은 어디?" if p["kind"] == "real" else "이야기 속의 이곳은 어디?")
        if q:
            qs.append(q)

    # G. 사건 → 장소
    for e in D["events"]:
        if e.get("place_unknown") or not e.get("place"):
            continue
        p = P[e["place"]]
        if mentions(e["name_ko"], p) or mentions(e["oneliner"], p):
            continue
        pool = real if p["kind"] == "real" else mythic
        ds = pick(rng, pool, N_CHOICES - 1, {p["id"], *e.get("places", [])})
        q = make(rng, "place", e["name_ko"] + " — " + e["oneliner"], p["name_ko"],
                 [d["name_ko"] for d in ds], f"{p['name_ko']} — {p['oneliner']}", "어디서 일어난 일?")
        if q:
            qs.append(q)

    rng.shuffle(qs)
    return qs


FRAGMENT = r"""<title>신화 퀴즈</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jua&family=Gowun+Dodum&display=swap">
<style>
/* 한 화면에 카드 하나. 질문은 크게, 보기는 엄지로 누르는 넓은 단추, 결과는 카드 아래 한 줄. */
:root {
  --bg: #f3f4f1;          /* 대리석 — 살짝 푸른 흰색 */
  --card: #ffffff;
  --fg: #1b2433;
  --muted: #5d6676;
  --line: #d6dad3;
  --accent: #1f5fa8;      /* 에게해 */
  --accent-fg: #ffffff;
  --gold: #b8892b;        /* 올리브 기름빛 */
  --ok: #2d8a4e;
  --ok-bg: #e3f3e8;
  --bad: #c2403a;
  --bad-bg: #fbe6e4;
  --display: "Jua", "Gowun Dodum", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  --body: "Gowun Dodum", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121a26; --card: #1b2533; --fg: #eef1f5; --muted: #a3adbb; --line: #2f3b4c;
    --accent: #6ea4e6; --accent-fg: #0f1826; --gold: #d8ab52;
    --ok: #6fcf8f; --ok-bg: #1d3a2a; --bad: #f08a84; --bad-bg: #44252a; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #121a26; --card: #1b2533; --fg: #eef1f5; --muted: #a3adbb; --line: #2f3b4c;
  --accent: #6ea4e6; --accent-fg: #0f1826; --gold: #d8ab52;
  --ok: #6fcf8f; --ok-bg: #1d3a2a; --bad: #f08a84; --bad-bg: #44252a; color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 18px; line-height: 1.5; }
.wrap { max-width: 640px; margin: 0 auto; padding-block: 16px 32px; padding-inline: 16px; display: flex; flex-direction: column; gap: 16px; min-height: 100%; }
header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
h1 { font-family: var(--display); font-weight: 400; font-size: 1.6rem; margin: 0; letter-spacing: .01em; }
h1 small { font-family: var(--body); font-size: .8rem; color: var(--muted); margin-left: .5em; }
.score { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .95rem; }
.score b { color: var(--fg); }
.bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; width: 0; background: var(--accent); transition: width .3s; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.label { font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: var(--gold); font-weight: 700; }
.q { font-family: var(--display); font-size: 1.45rem; line-height: 1.35; margin: 0; text-wrap: balance; }
.choices { display: grid; gap: 10px; }
@media (min-width: 560px) { .choices.short { grid-template-columns: 1fr 1fr; } }
.choice { font: inherit; font-size: 1.1rem; text-align: left; padding: 14px 16px; border-radius: 10px; border: 2px solid var(--line); background: var(--card); color: var(--fg); cursor: pointer; display: flex; gap: 12px; align-items: center; min-height: 56px; }
.choice span.n { font-family: var(--display); color: var(--muted); width: 1.2em; flex: none; }
.choice:hover:not(:disabled) { border-color: var(--accent); }
.choice:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.choice.ok { border-color: var(--ok); background: var(--ok-bg); }
.choice.bad { border-color: var(--bad); background: var(--bad-bg); }
.choice:disabled { cursor: default; opacity: .9; }
.fb { border-radius: 10px; padding: 12px 14px; font-size: 1rem; display: flex; flex-direction: column; gap: 6px; }
.fb.ok { background: var(--ok-bg); color: var(--ok); }
.fb.bad { background: var(--bad-bg); color: var(--bad); }
.fb b { font-family: var(--display); font-weight: 400; font-size: 1.15rem; }
.fb .x { color: var(--fg); }
.actions { display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.btn { font: inherit; font-family: var(--display); font-size: 1.1rem; padding: 12px 22px; border-radius: 10px; border: 2px solid var(--accent); background: var(--accent); color: var(--accent-fg); cursor: pointer; }
.btn:disabled { opacity: .35; cursor: default; }
.btn.ghost { background: transparent; color: var(--accent); }
.btn:focus-visible { outline: 3px solid var(--gold); outline-offset: 2px; }
.cats { display: flex; gap: 8px; flex-wrap: wrap; }
.cat { font: inherit; padding: 8px 14px; border-radius: 999px; border: 2px solid var(--line); background: var(--card); color: var(--fg); cursor: pointer; }
.cat[aria-pressed="true"] { border-color: var(--accent); background: var(--accent); color: var(--accent-fg); }
.intro p { margin: 0; color: var(--muted); }
.big { font-family: var(--display); font-size: 3rem; line-height: 1; color: var(--accent); font-variant-numeric: tabular-nums; }
footer { color: var(--muted); font-size: .8rem; }
footer a { color: inherit; }
@media (prefers-reduced-motion: reduce) { .bar i { transition: none; } }
</style>

<div class="wrap">
  <header>
    <h1>신화 퀴즈 <small>그리스 로마 신화</small></h1>
    <div class="score" id="score" hidden><b id="s-ok">0</b> 맞힘 · <span id="s-pos">1</span>/<span id="s-len">10</span></div>
  </header>
  <div class="bar" id="bar" hidden><i id="bar-i"></i></div>

  <section class="card intro" id="intro">
    <div class="label">시작하기</div>
    <p class="q">무엇을 맞춰 볼까?</p>
    <div class="cats" id="cats">
      <button class="cat" type="button" data-cat="figure" aria-pressed="true">인물 <span id="n-figure"></span></button>
      <button class="cat" type="button" data-cat="place" aria-pressed="true">장소 <span id="n-place"></span></button>
      <button class="cat" type="button" data-cat="thing" aria-pressed="true">상징과 맡은 일 <span id="n-thing"></span></button>
    </div>
    <p>한 판에 열 문제. 네 보기 가운데 하나를 고른다. 맞히면 다음으로, 틀리면 다시 고른다. 자판 1·2·3·4 로도 고를 수 있다.</p>
    <div class="actions"><button class="btn" type="button" id="start">시작</button></div>
  </section>

  <section class="card" id="play" hidden>
    <div class="label" id="label"></div>
    <p class="q" id="q"></p>
    <div class="choices" id="choices"></div>
    <div class="fb" id="fb" hidden></div>
    <div class="actions"><button class="btn" type="button" id="next" disabled>다음</button></div>
  </section>

  <section class="card" id="done" hidden>
    <div class="label">한 판 끝</div>
    <div class="big" id="final"></div>
    <p class="q" id="final-msg"></p>
    <p class="intro" id="final-sub"></p>
    <div class="actions"><button class="btn ghost" type="button" id="again-cats">종류 바꾸기</button><button class="btn" type="button" id="again">한 판 더</button></div>
  </section>

  <footer>문제 <span id="n-all"></span>개. 모두 공개 도메인 원전(아폴로도로스·호메로스·헤시오도스·오비디우스·베르길리우스 등)에서 쓴 자료다. 한 번 나온 문제는 다 돌 때까지 다시 나오지 않는다.</footer>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var ALL = JSON.parse(document.getElementById('data').textContent);
  var ROUND = 10;
  var $ = function (id) { return document.getElementById(id); };
  var cats = { figure: true, place: true, thing: true };
  var queue = [], pos = 0, ok = 0, cur = null, answered = false;

  function count(c) { return ALL.filter(function (q) { return q.cat === c; }).length; }
  $('n-figure').textContent = count('figure'); $('n-place').textContent = count('place'); $('n-thing').textContent = count('thing');
  $('n-all').textContent = ALL.length;

  // 한 번 나온 문제는 다 돌 때까지 다시 내지 않는다 — 이 브라우저에만 남는 기록
  function seenGet() { try { return JSON.parse(localStorage.getItem('seen') || '[]'); } catch (e) { return []; } }
  function seenPut(s) { try { localStorage.setItem('seen', JSON.stringify(s)); } catch (e) {} }

  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  function buildQueue() {
    var pool = ALL.map(function (q, i) { return i; }).filter(function (i) { return cats[ALL[i].cat]; });
    var seen = seenGet();
    var fresh = pool.filter(function (i) { return seen.indexOf(i) < 0; });
    if (fresh.length < ROUND) { seen = seen.filter(function (i) { return pool.indexOf(i) < 0; }); seenPut(seen); fresh = pool; }
    queue = shuffle(fresh).slice(0, ROUND);
    seenPut(seen.concat(queue));
  }

  function show(sec) { ['intro', 'play', 'done'].forEach(function (s) { $(s).hidden = s !== sec; }); $('score').hidden = $('bar').hidden = sec !== 'play'; }

  function render() {
    cur = ALL[queue[pos]]; answered = false;
    $('label').textContent = cur.label || '';
    $('q').textContent = cur.q;
    var box = $('choices'); box.innerHTML = '';
    var short = cur.choices.every(function (c) { return c.length <= 12; });
    box.className = 'choices' + (short ? ' short' : '');
    cur.choices.forEach(function (c, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'choice'; b.dataset.i = i;
      var n = document.createElement('span'); n.className = 'n'; n.textContent = i + 1;
      b.appendChild(n); b.appendChild(document.createTextNode(c));
      b.addEventListener('click', function () { pickChoice(i, b); });
      box.appendChild(b);
    });
    $('fb').hidden = true; $('fb').className = 'fb'; $('fb').innerHTML = '';
    $('next').disabled = true;
    $('s-pos').textContent = pos + 1; $('s-len').textContent = queue.length; $('s-ok').textContent = ok;
    $('bar-i').style.width = (pos / queue.length * 100) + '%';
    box.firstChild && box.firstChild.focus();
  }

  function pickChoice(i, btn) {
    if (answered) return;
    var fb = $('fb'); fb.hidden = false;
    if (i === cur.a) {
      answered = true; ok++;
      btn.classList.add('ok');
      Array.prototype.forEach.call($('choices').children, function (b) { b.disabled = true; });
      fb.className = 'fb ok';
      fb.innerHTML = '<b>맞았다! ' + esc(cur.choices[cur.a]) + '</b>' + (cur.x ? '<span class="x">' + esc(cur.x) + '</span>' : '');
      $('next').disabled = false; $('next').focus();
      $('s-ok').textContent = ok;
    } else {
      btn.classList.add('bad'); btn.disabled = true;
      fb.className = 'fb bad';
      fb.innerHTML = '<b>아니야.</b><span>' + esc(cur.choices[i]) + '은(는) 아니다. 다시 골라 보자.</span>';
    }
  }

  function next() {
    if (!answered) return;
    pos++;
    if (pos >= queue.length) { finish(); return; }
    render();
  }

  function finish() {
    show('done');
    $('final').textContent = ok + ' / ' + queue.length;
    $('final-msg').textContent = ok === queue.length ? '다 맞혔다.' : ok >= queue.length * 0.7 ? '잘했다.' : '다음 판엔 더 맞힐 수 있다.';
    var left = ALL.filter(function (q, i) { return cats[q.cat] && seenGet().indexOf(i) < 0; }).length;
    $('final-sub').textContent = '아직 안 나온 문제 ' + left + '개.';
  }

  function start() { pos = 0; ok = 0; buildQueue(); show('play'); render(); }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  $('cats').addEventListener('click', function (e) {
    var b = e.target.closest('.cat'); if (!b) return;
    var on = b.getAttribute('aria-pressed') !== 'true';
    if (!on && Object.keys(cats).filter(function (k) { return cats[k]; }).length === 1) return;  // 하나는 남긴다
    cats[b.dataset.cat] = on; b.setAttribute('aria-pressed', on);
  });
  $('start').addEventListener('click', start);
  $('again').addEventListener('click', start);
  $('again-cats').addEventListener('click', function () { show('intro'); });
  $('next').addEventListener('click', next);
  document.addEventListener('keydown', function (e) {
    if ($('play').hidden) return;
    if (e.key >= '1' && e.key <= '4') { var b = $('choices').children[+e.key - 1]; if (b && !b.disabled) b.click(); }
    else if (e.key === 'Enter' && answered) { next(); }
  });
})();
</script>
"""

DOC = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{fragment}
</body>
</html>
"""


def main(argv):
    D = json.loads(BUNDLE.read_text(encoding="utf-8"))
    qs = generate(D)
    data = json.dumps(qs, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fragment = FRAGMENT.replace("__DATA__", data)
    if len(argv) >= 2 and argv[0] == "--fragment":
        Path(argv[1]).write_text(fragment, encoding="utf-8")
        print(f"{argv[1]} — 본문만, {len(fragment):,} bytes")
        return
    # <title>·<style>·<link> 은 head 로, 나머지는 body 로
    head_end = fragment.index("</style>") + len("</style>")
    html = DOC.format(fragment=fragment[:head_end] + "\n</head>\n<body>" + fragment[head_end:])
    OUT.write_text(html, encoding="utf-8")
    from collections import Counter
    c = Counter(q["cat"] for q in qs)
    print(f"outputs/quiz/quiz.html — 문제 {len(qs)}개 (인물 {c['figure']}, 장소 {c['place']}, 사물 {c['thing']}), {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main(sys.argv[1:])
