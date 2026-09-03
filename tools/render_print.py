"""build/myth.json -> build/print-*.html

인쇄용. 브라우저에서 열고 인쇄(또는 PDF로 저장)하면 그대로 나온다.
화면용 페이지를 인쇄한 것이 아니라, 종이에 맞게 따로 짠 판이다.

  print-timeline.html  A3 가로 — 시대별 연표. 벽에 붙이는 것
  print-family.html    A3 세로 — 계보도. 부모에서 자식으로
  print-map.html       A3 가로 — 실제 지도 + 우주 도해 + 장소 표
  print-cards.html     A4 세로 — 인물 카드. 잘라서 쓰는 것

지도 좌표 변환은 render_web.py 와 같은 계산을 파이썬으로 다시 한다.
인쇄판은 상호작용이 없으므로 SVG 를 여기서 완성해 박아 넣는다.

    python tools/build.py && python tools/render_print.py
"""

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "build" / "myth.json"
GEO = ROOT / "data" / "geo" / "mediterranean.json"
OUTDIR = ROOT / "build"

ANCHOR_END = ' text-anchor="end"'

KIND = {"primordial": "첫 신", "titan": "티탄", "god": "올림포스 신", "hero": "영웅",
        "human": "사람", "monster": "괴물", "nymph": "님프", "group": "무리"}

CSS = """
  @page { size: %(page)s; margin: 9mm; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
    color:#1d1a16; font-size:%(fs)s; line-height:1.5; }
  h1 { font-size:20pt; margin:0 0 1mm; letter-spacing:-.02em; }
  .lead { color:#6d6558; font-size:9pt; margin:0 0 4mm; }
  .foot { color:#8d8578; font-size:7.5pt; margin-top:5mm; border-top:.4pt solid #cfc6b4;
    padding-top:2mm; }
  h2 { font-size:11pt; margin:0 0 1mm; }
  @media screen { body { max-width:1100px; margin:20px auto; padding:0 16px; } }
"""


def h(s):
    return escape(str(s))


def page(title, css_extra, body, *, size="A3 landscape", fs="9.5pt"):
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>{h(title)}</title>
<style>{CSS % {"page": size, "fs": fs}}{css_extra}</style></head>
<body>{body}</body></html>
"""


FOOT = ('원전 — 헤시오도스 『신들의 계보』, 아폴로도로스 『신화집』, 호메로스, 오비디우스, '
        '파우사니아스. 자료와 집필 기준은 greek-roman-myth/README.md 에 있다.')


# ---------- 연표 ----------
def timeline(D):
    """시대별 연표. 시대마다 한 구획이고, 사건은 구획 안에서 여러 단으로 흐른다.

    처음에는 아홉 시대를 나란한 아홉 칸으로 그렸다. era 5~8 이 채워지자 한 칸에
    예순 건이 들어가면서 A3 한 장에서 내용이 잘렸다. 그래서 칸을 나란히 두는 대신
    시대를 위에서 아래로 쌓고, 사건은 단으로 흘리게 바꿨다. 종이 수는 자료가
    늘면 늘어난다 — 잘리는 것보다 낫다.
    """
    css = """
  .era { break-inside:auto; margin:0 0 5mm; border:.5pt solid #d8cfbd; border-radius:2mm;
    overflow:hidden; }
  .era > .cap { color:#fff; padding:1.8mm 2.5mm; break-after:avoid; }
  .cap b { font-size:12pt; }
  .cap span { font-size:8.5pt; opacity:.9; margin-left:2mm; }
  .cap i { float:right; font-style:normal; font-size:8pt; opacity:.85; }
  .in { padding:2.5mm; columns:4; column-gap:5mm; }
  .ev { margin:0 0 2mm; break-inside:avoid; }
  .ev b { display:block; font-size:8.6pt; }
  .ev span { display:block; color:#5d564a; font-size:7.4pt; }
  .ev em { font-style:normal; color:#8d8578; font-size:7pt; }
  .who { padding:0 2.5mm 2.5mm; font-size:7.4pt; color:#5d564a; }
  .who b { color:#1d1a16; font-weight:600; }
  .empty { color:#a29a8b; font-size:7.5pt; padding:2.5mm; }
"""
    colors = ["#3b4a6b", "#4f6b8a", "#8a6a2f", "#6b7a3a", "#9a5b2c",
              "#8a3a3a", "#6b3a5b", "#3a6b62", "#7a4a2a"]
    arc_by = {a["id"]: a["name_ko"] for a in D["arcs"]}
    blocks = []
    for era in D["eras"]:
        evs = [e for e in D["events"] if e["era"] == era["n"]]
        figs = [f for f in D["figures"] if f["era"] == era["n"]]
        items = []
        for e in evs:
            arc = arc_by.get(e.get("arc"))
            items.append(
                f'<div class="ev"><b>{h(e["name_ko"])}</b>'
                f'<span>{h(e["oneliner"])}</span>'
                + (f'<em>{h(arc)}</em>' if arc else "")
                + "</div>")
        inner = f'<div class="in">{"".join(items)}</div>' if items else             '<div class="empty">아직 자료를 넣지 않은 시대</div>'
        who = ('<div class="who"><b>이때 처음 나오는 이</b> '
               + ", ".join(h(f["name_ko"]) for f in figs) + "</div>") if figs else ""
        blocks.append(
            f'<div class="era"><div class="cap" style="background:{colors[era["n"]]}">'
            f'<b>{era["n"]}. {h(era["name_ko"])}</b>'
            f'<span>{h(era["oneliner"])}</span>'
            f'<i>사건 {len(evs)} · 인물 {len(figs)}</i></div>'
            f'{inner}{who}</div>')
    body = (f'<h1>그리스 로마 신화 연표</h1>'
            f'<p class="lead">신화에는 연도가 없다. 대신 누가 누구의 부모인지로 순서를 알 수 있다. '
            f'그 순서를 아홉 시대로 나눈 것이다. 사건 {len(D["events"])}건.</p>'
            f'{"".join(blocks)}'
            f'<p class="foot">{FOOT}</p>')
    return page("그리스 로마 신화 연표", css, body)


# ---------- 계보도 ----------
def family(D):
    css = """
  .tree { columns:3; column-gap:7mm; font-size:8.6pt; }
  ul { list-style:none; margin:0; padding-left:3.5mm; border-left:.4pt dotted #cfc6b4; }
  .tree > ul { padding-left:0; border:0; }
  li { margin:.3mm 0; break-inside:avoid; }
  .k { color:#8d8578; font-size:7pt; }
  .root { break-before:column-avoid; }
  .root > span { font-weight:700; }
"""
    by = {f["id"]: f for f in D["figures"]}
    placed = set()

    def node(f, root=False):
        placed.add(f["id"])
        kids = [c for c in f.get("children", []) if c not in placed]
        placed.update(kids)
        inner = "".join(node(by[c]) for c in kids)
        cls = ' class="root"' if root else ""
        return (f'<li{cls}><span>{h(f["name_ko"])}</span> '
                f'<span class="k">{KIND[f["kind"]]}</span>'
                + (f"<ul>{inner}</ul>" if inner else "") + "</li>")

    size = {}

    def count(fid):
        if fid not in size:
            size[fid] = 1 + sum(count(c) for c in by[fid].get("children", []))
        return size[fid]

    roots = sorted((f for f in D["figures"] if not f.get("parents")),
                   key=lambda f: (f["era"], count(f["id"]), f["name_ko"]))
    items = "".join(node(f, root=True) for f in roots if f["id"] not in placed)
    body = ('<h1>그리스 로마 신화 계보도</h1>'
            '<p class="lead">위에서 아래로 부모 → 자식. 맨 처음에는 부모가 없는 신이 여럿이다. '
            '카오스와 가이아는 서로의 부모가 아니라 각각 생겨났다. '
            '부모가 둘인 경우 한쪽 아래에만 놓았다.</p>'
            f'<div class="tree"><ul>{items}</ul></div>'
            f'<p class="foot">{FOOT}</p>')
    return page("그리스 로마 신화 계보도", css, body, size="A3 portrait", fs="9pt")


# ---------- 지도 ----------
def map_svg(D, geo):
    real = [p for p in D["places"] if p["kind"] == "real"]
    b = geo["box"]
    k = math.cos(math.radians((b["lat0"] + b["lat1"]) / 2))

    def X(lon):
        return (lon - b["lon0"]) * k

    def Y(lat):
        return b["lat1"] - lat

    xs = [X(p["lon"]) for p in real]
    ys = [Y(p["lat"]) for p in real]
    pad = 2.2
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    if (x1 - x0) / (y1 - y0) < 1.35:
        want = (y1 - y0) * 1.35
        cx = (x0 + x1) / 2
        x0, x1 = cx - want / 2, cx + want / 2
    w, hh = x1 - x0, y1 - y0
    fs, r = hh * 0.019, hh * 0.009

    paths = "".join(
        '<path d="M' + "L".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in ring) + 'Z"/>'
        for ring in geo["rings"])

    labels = sorted(({"p": p, "x": X(p["lon"]), "y": Y(p["lat"])} for p in real),
                    key=lambda L: (L["y"], L["x"]))
    boxes = []
    marks = []
    for L in labels:
        L["lx"] = L["x"] + r * 1.8
        L["ly"] = L["y"] + fs * 0.35
        width = len(L["p"]["name_ko"]) * fs * 1.02
        guard = 0
        while guard < 12 and any(abs(o["ly"] - L["ly"]) < fs * 1.25
                                 and L["lx"] < o["lx"] + o["w"] and o["lx"] < L["lx"] + width
                                 for o in boxes):
            L["ly"] += fs * 1.1
            guard += 1
        boxes.append({"lx": L["lx"], "ly": L["ly"], "w": width})
        if L["ly"] - L["y"] > fs * 0.8:
            marks.append(f'<line x1="{L["x"]:.2f}" y1="{L["y"]:.2f}" x2="{L["lx"] - r * .4:.2f}"'
                         f' y2="{L["ly"] - fs * .3:.2f}" stroke="#b9a888"'
                         f' stroke-width="{r * .3:.3f}"/>')
        marks.append(f'<circle class="dot" cx="{L["x"]:.2f}" cy="{L["y"]:.2f}" r="{r:.3f}"/>')
        marks.append(f'<text x="{L["lx"]:.2f}" y="{L["ly"]:.2f}" font-size="{fs:.3f}">'
                     f'{h(L["p"]["name_ko"])}</text>')

    return (f'<svg viewBox="{x0:.2f} {y0:.2f} {w:.2f} {hh:.2f}">'
            f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{w:.2f}" height="{hh:.2f}" fill="#e7eef3"/>'
            f'<g class="land">{paths}</g>{"".join(marks)}</svg>')


def cosmos_svg(D):
    w, hh = 30, 22
    fs, r = hh * 0.026, hh * 0.014
    bands = [("하늘", 0, .20, "#eaf0f6"), ("땅", .20, .62, "#f1e9d8"), ("땅속", .62, 1, "#e0d9cf")]
    out = []
    for name, a, z, fill in bands:
        out.append(f'<rect x="0" y="{a * hh:.2f}" width="{w}" height="{(z - a) * hh:.2f}"'
                   f' fill="{fill}"/>')
        out.append(f'<text x="0.5" y="{a * hh + fs * 1.6:.2f}" font-size="{fs:.2f}"'
                   f' fill="#8d8578">{name}</text>')
    for p in [p for p in D["places"] if p["kind"] == "mythic"]:
        x, y = p["cx"] * w, p["cy"] * hh
        end = p["cx"] > .7
        out.append(f'<circle class="dot" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"/>')
        out.append(f'<text x="{x + (-r * 1.6 if end else r * 1.6):.2f}" y="{y + fs * .35:.2f}"'
                   f' font-size="{fs:.2f}"{ANCHOR_END if end else ""}>'
                   f'{h(p["name_ko"])}</text>')
    out.append(f'<rect x=".15" y=".15" width="{w - .3}" height="{hh - .3}" fill="none"'
               f' stroke="#7d94ab" stroke-width=".12" stroke-dasharray=".5 .35"/>')
    return f'<svg viewBox="0 0 {w} {hh}">{"".join(out)}</svg>'


def maps(D, geo):
    css = """
  .two { display:flex; gap:5mm; align-items:flex-start; }
  .two > div { flex:1 1 0; min-width:0; }
  svg { width:100%; height:auto; border:.5pt solid #d8cfbd; border-radius:2mm; }
  .land path { fill:#f1e9d8; stroke:#cfc0a4; stroke-width:.06; }
  .dot { fill:#9a5b2c; stroke:#fff; stroke-width:.05; }
  text { fill:#1d1a16; }
  table { width:100%; border-collapse:collapse; font-size:8pt; margin-top:3mm; }
  th, td { text-align:left; padding:.9mm 1.5mm; border-bottom:.4pt solid #e2d9c8;
    vertical-align:top; }
  th { color:#6d6558; font-weight:600; font-size:7.5pt; }
  .note { font-size:7.5pt; color:#6d6558; margin:1.5mm 0 0; }
"""
    rows = "".join(
        f'<tr><td><b>{h(p["name_ko"])}</b></td><td>{h(p["modern"])}</td>'
        f'<td>{h(p["oneliner"])}</td></tr>'
        for p in D["places"] if p["kind"] == "real")
    myth_rows = "".join(
        f'<tr><td><b>{h(p["name_ko"])}</b></td><td>{h(p["oneliner"])}</td></tr>'
        for p in D["places"] if p["kind"] == "mythic")
    body = (
        '<h1>신화의 땅과 세계</h1>'
        '<p class="lead">왼쪽은 지금 가면 있는 곳이다. 오른쪽은 실제로는 없고, '
        '그리스 사람들이 생각한 세계의 모양이다. 둘을 한 지도에 섞지 않는다.</p>'
        f'<div class="two">'
        f'<div><h2>실제로 있는 곳</h2>{map_svg(D, geo)}'
        f'<table><tr><th>이름</th><th>지금의 이름</th><th>무슨 곳인가</th></tr>{rows}</table></div>'
        f'<div><h2>이야기 속의 곳</h2>{cosmos_svg(D)}'
        f'<p class="note">둘레의 점선이 세계를 감고 흐르는 강 오케아노스다. '
        f'위아래는 하늘·땅·땅속의 층이다.</p>'
        f'<table><tr><th>이름</th><th>무슨 곳인가</th></tr>{myth_rows}</table></div>'
        f'</div><p class="foot">{FOOT}</p>')
    return page("신화의 땅과 세계", css, body)


# ---------- 인물 카드 ----------
def cards(D):
    css = """
  .grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:4mm; }
  .card { border:.6pt solid #c9bfa9; border-radius:2.5mm; padding:3mm 3.5mm; break-inside:avoid;
    min-height:46mm; display:flex; flex-direction:column; }
  .card h3 { margin:0; font-size:13pt; }
  .card .alt { color:#8d8578; font-size:7.5pt; margin:.5mm 0 1.5mm; }
  .card .one { font-weight:600; font-size:9pt; margin:0 0 1.5mm; }
  .card .body { font-size:8.2pt; white-space:pre-line; margin:0 0 auto; }
  .card .meta { font-size:7.5pt; color:#5d564a; border-top:.4pt dotted #cfc6b4;
    margin-top:2mm; padding-top:1.5mm; }
  .card .meta b { color:#1d1a16; font-weight:600; }
"""
    by = {f["id"]: f for f in D["figures"]}
    picked = [f for f in D["figures"] if f["kind"] in ("god", "titan", "hero", "primordial")
              and (f.get("domains") or f.get("symbols") or f["events"])]
    out = []
    for f in picked:
        alt = " · ".join(x for x in [
            f.get("name_grc"), f.get("name_la") and "로마 " + f["name_la"]] if x)
        meta = []
        if f.get("parents"):
            meta.append("<b>부모</b> " + ", ".join(h(by[p]["name_ko"]) for p in f["parents"]))
        if f.get("symbols"):
            meta.append("<b>표시</b> " + h(", ".join(f["symbols"])))
        if f.get("domains"):
            meta.append("<b>맡은 일</b> " + h(", ".join(f["domains"])))
        out.append(
            f'<div class="card"><h3>{h(f["name_ko"])}'
            f' <span class="alt">{KIND[f["kind"]]}</span></h3>'
            + (f'<div class="alt">{h(alt)}</div>' if alt else "")
            + f'<p class="one">{h(f["oneliner"])}</p>'
            f'<div class="body">{h(f["body"].strip())}</div>'
            + (f'<div class="meta">{" · ".join(meta)}</div>' if meta else "")
            + "</div>")
    body = (f'<h1>인물 카드</h1>'
            f'<p class="lead">잘라서 쓰는 카드 {len(out)}장. 한 줄에 둘.</p>'
            f'<div class="grid">{"".join(out)}</div>'
            f'<p class="foot">{FOOT}</p>')
    return page("인물 카드", css, body, size="A4 portrait", fs="9pt")


def main():
    D = json.loads(BUNDLE.read_text(encoding="utf-8"))
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    made = [
        ("print-timeline.html", timeline(D)),
        ("print-family.html", family(D)),
        ("print-map.html", maps(D, geo)),
        ("print-cards.html", cards(D)),
    ]
    for name, html in made:
        (OUTDIR / name).write_text(html, encoding="utf-8")
        print(f"build/{name} — {(OUTDIR / name).stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
