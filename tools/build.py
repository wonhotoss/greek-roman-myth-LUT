"""data/*.toml -> build/myth.json

검증하고, 파생 필드(children, 등장 사건, 장소별 사건)를 만들고, 정렬해서 하나로 합친다.
스키마는 데이터-모델.md 가 원본이다.

깨지면 즉시 죽는다. 기본값을 채워 넣거나 없는 참조를 건너뛰지 않는다.
데이터가 틀린 채로 산출물이 나오는 것이 최악이다.

    python tools/build.py
"""

import json
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "build" / "myth.json"

COMMON = {"id", "name_ko", "aka", "oneliner", "body", "fun", "sources", "sensitivity", "note"}
REQUIRED_COMMON = {"id", "name_ko", "oneliner", "body", "sources"}

SPEC = {
    "figure": {
        "keys": COMMON | {"name_grc", "name_la", "kind", "era", "parents",
                          "parents_variant", "spouses", "domains", "symbols", "home"},
        "required": REQUIRED_COMMON | {"kind", "era"},
    },
    "event": {
        "keys": COMMON | {"era", "seq", "place", "places", "cast", "caused_by", "variants",
                          "span", "after", "within", "open", "place_unknown"},
        "required": REQUIRED_COMMON | {"era", "seq", "cast"},
    },
    "place": {
        "keys": COMMON | {"name_grc", "kind", "lat", "lon", "modern", "layer", "cx", "cy"},
        "required": REQUIRED_COMMON | {"kind"},
    },
    "arc": {
        "keys": COMMON | {"era", "events"},
        "required": REQUIRED_COMMON | {"era", "events"},
    },
    "source": {
        "keys": {"id", "author_ko", "title_ko", "title_orig", "written", "file", "translator", "note"},
        "required": {"id", "author_ko", "title_ko", "title_orig", "written"},
    },
    "era": {
        "keys": {"n", "name_ko", "oneliner"},
        "required": {"n", "name_ko", "oneliner"},
    },
}

FIGURE_KINDS = {"primordial", "titan", "god", "hero", "human", "monster", "nymph", "group"}
PLACE_KINDS = {"real", "mythic"}
LAYERS = {"sky", "earth", "sea", "underworld", "edge"}
ROLES = {"주인공", "상대", "도움", "피해", "등장"}
SENSITIVITY = {"none", "soften"}

# 사건이 얼마나 걸렸는가. 신화에 정확한 길이는 없으므로 등급만 둔다.
# 값은 눈금 없는 축에서의 최소 길이다. 실제 길이가 아니라 순서와 겹침을 보이기 위한 것.
SPANS = {"moment": 1, "days": 2, "season": 4, "years": 9, "age": 24}
SPAN_LABEL = {"moment": "한 순간", "days": "며칠", "season": "한 철",
              "years": "여러 해", "age": "한 세대 넘게"}

errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def load(kind, paths):
    items = []
    for path in sorted(paths):
        with path.open("rb") as f:
            doc = tomllib.load(f)
        rows = doc.get(kind)
        if rows is None:
            err(path.name, f"[[{kind}]] 이 없다")
            continue
        for row in rows:
            row["_file"] = path.relative_to(ROOT).as_posix()
            items.append(row)
    return items


def check_keys(kind, item):
    spec = SPEC[kind]
    where = f"{item.get('_file', '?')} {kind} {item.get('id', item.get('n', '?'))}"
    unknown = set(item) - spec["keys"] - {"_file"}
    if unknown:
        err(where, f"스키마에 없는 필드: {sorted(unknown)}")
    missing = spec["required"] - set(item)
    if missing:
        err(where, f"필수 필드 없음: {sorted(missing)}")
    if item.get("sensitivity", "none") not in SENSITIVITY:
        err(where, f"sensitivity 값이 이상하다: {item['sensitivity']}")
    return where


def solve_axis(events, eras):
    """눈금 없는 단일 시간축에서 각 사건의 구간 [t0, t1] 을 정한다.

    좌표를 데이터에 적지 않는다. 적어 두면 인과를 하나 고칠 때마다 어긋난다.
    아래 제약만 데이터에 있고, 좌표는 여기서 **가장 긴 경로**로 푼다
    (PERT 와 같은 방식). 제약에 순환이 있으면 = 인과가 모순이면 그 자리에서 죽는다.

    제약:
      시대 경계 E_n < E_(n+1)
      사건은 자기 시대 안에서 시작한다      E_n <= t0 < E_(n+1)
      길이는 span 등급의 최소값 이상          t1 >= t0 + SPANS[span]
      같은 시대 안에서 seq 는 시작 순서        t0(seq 작은 것) < t0(큰 것)
      caused_by: 원인이 먼저 시작한다          t0(원인) < t0(결과)
      after:     완전히 끝난 뒤에 시작한다     t1(앞) <= t0(뒤)
      within:    바깥이 안을 감싼다            t0(밖) <= t0(안), t1(안) <= t1(밖)
      끝이 인과로 고정되지 않았고 open 도 아니면 자기 시대를 넘지 못한다  t1 <= E_(n+1)

    끝(t1)이 시대를 넘을 수 있는 것은 두 경우뿐이다.
      1. 뒤의 사건이 after 로 그 끝을 붙잡고 있다 (우라노스의 감금 → 티타노마키아가 끝낸다)
      2. open = true — 끝나지 않거나 끝을 아직 모른다 (계절의 되풀이, 프로메테우스의 벌)
    그 밖의 사건은 자기 시대 안에서 끝난다. 그러지 않으면 길이 등급 하나 때문에
    "이 일이 다음 시대까지 이어졌다"는, 데이터에 없는 말을 그림이 하게 된다.
    """
    cons = []
    nodes = set()

    def add(a, b, w):
        cons.append((a, b, w))
        nodes.add(a)
        nodes.add(b)

    ns = sorted(e["n"] for e in eras)
    bounds = ns + [ns[-1] + 1]
    for a, b in zip(bounds, bounds[1:]):
        add(("era", a), ("era", b), 1)

    per_era = defaultdict(list)
    for e in events:
        per_era[e["era"]].append(e)
    for n, evs in per_era.items():
        evs.sort(key=lambda e: e["seq"])
        for i, e in enumerate(evs):
            eid = e["id"]
            add(("era", n), ("t0", eid), 0)
            add(("t0", eid), ("era", n + 1), 1)
            add(("t0", eid), ("t1", eid), SPANS[e.get("span", "moment")])
            if i:
                add(("t0", evs[i - 1]["id"]), ("t0", eid), 1)

    pinned = {aid for e in events for aid in e.get("after", [])}
    for e in events:
        eid = e["id"]
        if not e.get("open") and eid not in pinned:
            add(("t1", eid), ("era", e["era"] + 1), 0)
        for cid in e.get("caused_by", []):
            add(("t0", cid), ("t0", eid), 1)
        for aid in e.get("after", []):
            add(("t1", aid), ("t0", eid), 0)
        if "within" in e:
            add(("t0", e["within"]), ("t0", eid), 0)
            add(("t1", eid), ("t1", e["within"]), 0)

    # 위상 정렬. 남는 것이 있으면 순환 = 인과 모순.
    out = defaultdict(list)
    indeg = {v: 0 for v in nodes}
    for a, b, w in cons:
        out[a].append((b, w))
        indeg[b] += 1
    queue = [v for v, d in indeg.items() if d == 0]
    pos = {v: 0 for v in nodes}
    order = []
    while queue:
        v = queue.pop()
        order.append(v)
        for b, w in out[v]:
            if pos[v] + w > pos[b]:
                pos[b] = pos[v] + w
            indeg[b] -= 1
            if indeg[b] == 0:
                queue.append(b)
    if len(order) != len(nodes):
        stuck = sorted(f"{k}:{v}" for v in nodes - set(order) for k in [""])
        left = sorted(v for v in nodes if v not in set(order))
        err("시간축", "인과에 순환이 있다. 다음 항목들의 순서가 서로를 요구한다: "
            + ", ".join(f"{a}({b})" for a, b in left))
        return None

    for e in events:
        e["t0"] = pos[("t0", e["id"])]
        e["t1"] = pos[("t1", e["id"])]
        e["span_label"] = SPAN_LABEL[e.get("span", "moment")]
        e["open"] = bool(e.get("open"))
    return {
        "total": max(pos.values()),
        "eras": {str(n): [pos[("era", n)], pos[("era", n + 1)]] for n in ns},
    }


def audit_uncertain(events, eras, places, arcs, out_path):
    """무엇을 모르는지 기계로 뽑는다. 손으로 적은 목록은 데이터가 바뀌면 낡는다.

    두 가지를 본다.
      1. 순서를 원전이 아니라 seq 가 정한 짝. 같은 시대에서 seq 로 이웃한 두 사건 사이에
         caused_by / after 로 이어지는 길이 없으면, 그 순서는 우리가 아는 것이 아니다.
      2. 장소가 붙지 않은 사건. place_unknown 으로 표시한 것(원전이 말하지 않는다)과
         아직 넣지 않은 것을 가른다. 할 일은 뒤쪽이다.
    시대가 다른 사건끼리는 시작 순서를 안다(시대 경계가 정한다). 그래서 보지 않는다.
    """
    strict = defaultdict(set)          # A -> B : A 가 B 보다 먼저 시작한다고 원전이 말한다
    for e in events:
        for cid in e.get("caused_by", []):
            strict[cid].add(e["id"])
        for aid in e.get("after", []):
            strict[aid].add(e["id"])

    def reaches(a, b):
        seen, stack = {a}, [a]
        while stack:
            v = stack.pop()
            if v == b:
                return True
            for w in strict[v] - seen:
                seen.add(w)
                stack.append(w)
        return False

    by_id = {e["id"]: e for e in events}
    era_name = {x["n"]: x["name_ko"] for x in eras}
    per_era = defaultdict(list)
    for e in events:
        per_era[e["era"]].append(e)

    # 두 종류를 가른다.
    #   같은 묶음 안 — 한 이야기 안에서 순서를 모른다. 이어야 할 관계가 빠졌을 수 있다.
    #   다른 묶음 사이 — 한 시대에 든 두 이야기의 이음매. 원전이 순서를 말하지 않는 것이 정상이다.
    inner_gaps, seam_gaps = [], []
    for n in sorted(per_era):
        evs = sorted(per_era[n], key=lambda e: e["seq"])
        for a, b in zip(evs, evs[1:]):
            if reaches(a["id"], b["id"]) or reaches(b["id"], a["id"]):
                continue
            same = a.get("arc") and a.get("arc") == b.get("arc")
            (inner_gaps if same else seam_gaps).append((n, a, b))
    order_gaps = inner_gaps

    # 장소가 없는 사건을 둘로 가른다.
    #   place_unknown — 원전이 장소를 말하지 않거나 특정할 수 없다고 판단해 표시한 것. note 에 이유가 있다.
    #   그 밖        — 아직 넣지 않은 것. 이쪽이 할 일 목록이다.
    placeless = [e for e in events if "place" not in e and not e.get("places")]
    no_place = [e for e in placeless if not e.get("place_unknown")]
    unknown_place = [e for e in placeless if e.get("place_unknown")]

    lines = [
        "# 불확실 점검 — 자동 생성",
        "",
        "`tools/build.py` 가 만든다. 직접 고치지 말고 `data/` 를 고쳐 다시 만든다.",
        "판단과 처리 방침은 [../불확실-목록.md](../불확실-목록.md) 에 있다.",
        "",
        f"## 1. 같은 묶음 안에서 순서를 모르는 짝 — {len(order_gaps)}건",
        "",
        "같은 이야기 묶음에 든 두 사건이 seq 로 이웃한데, `caused_by`/`after` 로 이어지는 길이 없다.",
        "시간축에서는 순서가 생기지만 **우리가 아는 순서가 아니다.** 이어야 할 관계가 빠진 것일 수 있다.",
        "",
        "| 시대 | 앞(seq) | 뒤(seq) | 이어 줄 관계가 있는가 |",
        "|---|---|---|---|",
    ]
    for n, a, b in order_gaps:
        lines.append(f"| {n} {era_name[n]} | {a['name_ko']} ({a['seq']}) | "
                     f"{b['name_ko']} ({b['seq']}) | 없음 |")
    if not order_gaps:
        lines.append("| — | — | — | 없음 |")

    lines += [
        "",
        f"### 1-2. 다른 묶음 사이의 이음매 — {len(seam_gaps)}건",
        "",
        "한 시대에 여러 이야기가 들어 있어 생기는 것이다. 두 이야기가 서로를 부르지 않으므로",
        "**원전이 순서를 말하지 않는 것이 정상이다.** 위의 1번과 성질이 다르다 — 고칠 것이 아니라",
        "'이 둘은 나란한 이야기'라고 읽어야 한다.",
        "",
        "| 시대 | 앞 묶음 | 뒤 묶음 |",
        "|---|---|---|",
    ]
    seen = set()
    for n, a, b in seam_gaps:
        key = (n, a.get("arc"), b.get("arc"))
        if key in seen:
            continue
        seen.add(key)
        arc_name = {x["id"]: x["name_ko"] for x in arcs}
        left = arc_name.get(a.get("arc"), f"낱 사건 {a['name_ko']}")
        right = arc_name.get(b.get("arc"), f"낱 사건 {b['name_ko']}")
        lines.append(f"| {n} {era_name[n]} | {left} | {right} |")
    if not seam_gaps:
        lines.append("| — | — | — |")

    lines += [
        "",
        f"## 2. 장소를 아직 넣지 않은 사건 — {len(no_place)}건",
        "",
        "지도에 켤 수 없다. 원전이 장소를 말하지 않는 것은 `place_unknown` 으로 표시해 아래 2-2 로 뺐으므로,",
        "여기 남는 것은 **넣을 수 있는데 아직 넣지 않은 것**이다. 할 일 목록이다.",
        "",
        "| 사건 | 시대 | 한 줄 |",
        "|---|---|---|",
    ]
    for e in no_place:
        lines.append(f"| {e['name_ko']} `{e['id']}` | {e['era']} {era_name[e['era']]} | "
                     f"{e['oneliner']} |")
    if not no_place:
        lines.append("| — | — | — |")

    lines += [
        "",
        f"### 2-2. 원전이 장소를 말하지 않는 사건 — {len(unknown_place)}건",
        "",
        "`place_unknown = true` 로 표시한 것. 고칠 것이 아니다 — 모르는 것을 아는 것처럼 그리지 않기 위해 남긴다.",
        "화면과 에이전트 팩은 이 사건에 대해 '어디서 일어났는지는 옛 책에 없다' 고 말한다.",
        "",
        "| 사건 | 시대 | 왜 없는가 |",
        "|---|---|---|",
    ]
    for e in unknown_place:
        lines.append(f"| {e['name_ko']} `{e['id']}` | {e['era']} {era_name[e['era']]} | {e['note']} |")
    if not unknown_place:
        lines.append("| — | — | — |")

    myth = [q for q in places if q["kind"] == "mythic"]
    lines += [
        "",
        f"## 3. 실제 지도에 놓지 않은 장소 — {len(myth)}건",
        "",
        "`kind = \"mythic\"` 으로 둔 곳. 실제로 없는 곳과, 뒷시대 전승이 실제 위치를 주장하는 곳이",
        "섞여 있다. 뒤쪽은 판단이 필요하다 — `불확실-목록.md` 참조.",
        "",
        "| 장소 | 세계의 층 | 메모 |",
        "|---|---|---|",
    ]
    for q in myth:
        lines.append(f"| {q['name_ko']} `{q['id']}` | {q['layer']} | {q.get('note', '') or '—'} |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(order_gaps), len(no_place), len(unknown_place)


def main():
    figures = load("figure", DATA.glob("figures/*.toml"))
    events = load("event", DATA.glob("events/*.toml"))
    places = load("place", DATA.glob("places/*.toml"))
    arcs = load("arc", [DATA / "arcs.toml"])
    sources = load("source", [DATA / "sources.toml"])
    eras = load("era", [DATA / "eras.toml"])

    era_ns = {e["n"] for e in eras}
    for e in eras:
        check_keys("era", e)

    ids = {}
    for kind, items in (("figure", figures), ("event", events), ("place", places), ("arc", arcs)):
        for item in items:
            where = check_keys(kind, item)
            iid = item.get("id")
            if iid in ids:
                err(where, f"id 가 겹친다: {iid} (앞선 것은 {ids[iid]})")
            ids[iid] = where
            if item.get("era") is not None and item["era"] not in era_ns:
                err(where, f"없는 era: {item['era']}")

    source_ids = set()
    for s in sources:
        check_keys("source", s)
        if s["id"] in source_ids:
            err(f"sources.toml {s['id']}", "id 가 겹친다")
        source_ids.add(s["id"])
        if "file" in s and not (ROOT / s["file"]).exists():
            err(f"sources.toml {s['id']}", f"file 이 없다: {s['file']}")

    figure_ids = {f["id"] for f in figures}
    place_ids = {p["id"] for p in places}
    event_ids = {e["id"] for e in events}
    arc_ids = {a["id"] for a in arcs}

    def ref(where, field, value, pool, pool_name):
        if value not in pool:
            err(where, f"{field} 가 없는 {pool_name} 를 가리킨다: {value}")

    def check_sources(where, item):
        for s in item.get("sources", []):
            sid = s.split(" ", 1)[0]
            if sid not in source_ids:
                err(where, f"sources 에 없는 원전 id: {sid}")

    for f in figures:
        where = f"{f['_file']} figure {f['id']}"
        if f["kind"] not in FIGURE_KINDS:
            err(where, f"kind 값이 이상하다: {f['kind']}")
        for pid in f.get("parents", []):
            ref(where, "parents", pid, figure_ids, "figure")
        for sid in f.get("spouses", []):
            ref(where, "spouses", sid, figure_ids, "figure")
        if "home" in f:
            ref(where, "home", f["home"], place_ids, "place")
        for v in f.get("parents_variant", []):
            unknown = set(v) - {"source", "parents", "text"}
            if unknown:
                err(where, f"parents_variant 에 스키마에 없는 필드: {sorted(unknown)}")
            if "parents" not in v or "source" not in v:
                err(where, "parents_variant 는 source 와 parents 를 가져야 한다")
            for pid in v.get("parents", []):
                ref(where, "parents_variant", pid, figure_ids, "figure")
            if v["source"].split(" ", 1)[0] not in source_ids:
                err(where, f"parents_variant 의 원전 id 가 없다: {v['source']}")
        check_sources(where, f)

    for p in places:
        where = f"{p['_file']} place {p['id']}"
        if p["kind"] not in PLACE_KINDS:
            err(where, f"kind 값이 이상하다: {p['kind']}")
        if p["kind"] == "real":
            for k in ("lat", "lon", "modern"):
                if k not in p:
                    err(where, f"real 인데 {k} 가 없다")
        else:
            for k in ("layer", "cx", "cy"):
                if k not in p:
                    err(where, f"mythic 인데 {k} 가 없다")
            if p.get("layer") not in LAYERS:
                err(where, f"layer 값이 이상하다: {p.get('layer')}")
        check_sources(where, p)

    seen_seq = set()
    for e in events:
        where = f"{e['_file']} event {e['id']}"
        key = (e["era"], e["seq"])
        if key in seen_seq:
            err(where, f"era/seq 가 겹친다: {key}")
        seen_seq.add(key)
        for c in e["cast"]:
            if set(c) != {"figure", "role"}:
                err(where, f"cast 항목은 figure/role 만 갖는다: {c}")
            ref(where, "cast.figure", c.get("figure"), figure_ids, "figure")
            if c.get("role") not in ROLES:
                err(where, f"role 값이 이상하다: {c.get('role')}")
        if "place" in e:
            ref(where, "place", e["place"], place_ids, "place")
        for pid in e.get("places", []):
            ref(where, "places", pid, place_ids, "place")
        for eid in e.get("caused_by", []):
            ref(where, "caused_by", eid, event_ids, "event")
        for eid in e.get("after", []):
            ref(where, "after", eid, event_ids, "event")
        if "within" in e:
            ref(where, "within", e["within"], event_ids, "event")
        if "open" in e and not isinstance(e["open"], bool):
            err(where, f"open 은 true/false 여야 한다: {e['open']}")
        if "place_unknown" in e:
            # 원전이 장소를 말하지 않거나 특정할 수 없는 사건. 모르는 것을 아는 것처럼 그리지 않기 위한 표시다.
            if not isinstance(e["place_unknown"], bool):
                err(where, f"place_unknown 은 true/false 여야 한다: {e['place_unknown']}")
            elif e["place_unknown"]:
                if "place" in e or e.get("places"):
                    err(where, "place_unknown 인데 place/places 도 있다 — 장소를 모르는지 아는지 하나만 말한다")
                if not e.get("note"):
                    err(where, "place_unknown 이면 note 에 왜 장소가 없는지 적는다")
        if e.get("span", "moment") not in SPANS:
            err(where, f"span 값이 이상하다: {e['span']} (쓸 수 있는 것: {sorted(SPANS)})")
        for v in e.get("variants", []):
            if set(v) != {"source", "text"}:
                err(where, f"variants 항목은 source/text 만 갖는다: {sorted(v)}")
            if v["source"].split(" ", 1)[0] not in source_ids:
                err(where, f"variants 의 원전 id 가 없다: {v['source']}")
        check_sources(where, e)

    owner = {}
    for a in arcs:
        where = f"{a['_file']} arc {a['id']}"
        for eid in a["events"]:
            ref(where, "events", eid, event_ids, "event")
            if eid in owner:
                err(where, f"사건 {eid} 가 묶음 두 곳에 들어 있다 (앞선 곳은 {owner[eid]})")
            owner[eid] = a["id"]
        check_sources(where, a)

    if errors:
        print(f"검증 실패 — {len(errors)}건\n", file=sys.stderr)
        for line in errors:
            print("  " + line, file=sys.stderr)
        sys.exit(1)

    # 파생 — 데이터에 중복으로 적지 않고 여기서 만든다.
    children = defaultdict(list)
    for f in figures:
        for pid in f.get("parents", []):
            children[pid].append(f["id"])

    # 사건의 묶음(arc)은 묶음의 events 목록에서 역인덱스로 만든다. 양쪽에 적으면 어긋난다.
    for e in events:
        if e["id"] in owner:
            e["arc"] = owner[e["id"]]

    fig_events = defaultdict(list)
    place_events = defaultdict(list)
    events.sort(key=lambda e: (e["era"], e["seq"]))
    for e in events:
        for c in e["cast"]:
            fig_events[c["figure"]].append({"event": e["id"], "role": c["role"]})
        for pid in ([e["place"]] if "place" in e else []) + e.get("places", []):
            place_events[pid].append(e["id"])

    for f in figures:
        f["children"] = children.get(f["id"], [])
        f["events"] = fig_events.get(f["id"], [])
    for p in places:
        p["events"] = place_events.get(p["id"], [])

    axis = solve_axis(events, eras)
    if errors:
        print(f"검증 실패 — {len(errors)}건\n", file=sys.stderr)
        for line in errors:
            print("  " + line, file=sys.stderr)
        sys.exit(1)
    for a in arcs:
        mine = [e for e in events if e["id"] in a["events"]]
        a["t0"] = min(e["t0"] for e in mine)
        a["t1"] = max(e["t1"] for e in mine)

    figures.sort(key=lambda f: (f["era"], f["name_ko"]))
    places.sort(key=lambda p: (p["kind"], p["name_ko"]))
    arcs.sort(key=lambda a: a["era"])
    eras.sort(key=lambda e: e["n"])

    bundle = {
        "axis": axis,
        "eras": eras,
        "figures": figures,
        "events": events,
        "places": places,
        "arcs": arcs,
        "sources": sources,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")

    gaps, noplace, unknown = audit_uncertain(events, eras, places, arcs, OUT.parent / "불확실-점검.md")

    orphans = [f["id"] for f in figures if not f["events"] and not f["children"]]
    print(f"검증 통과 — {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size:,} bytes)")
    print(f"  시간축 길이 {axis['total']}칸, 여러 시대에 걸친 사건 "
          f"{sum(1 for e in events if e['t1'] > axis['eras'][str(e['era'])][1])}건")
    print(f"  불확실 점검 → build/불확실-점검.md — 순서를 seq 가 정한 짝 {gaps}건, "
          f"장소를 아직 넣지 않은 사건 {noplace}건 (원전이 말하지 않는 것 {unknown}건은 따로)")
    print(f"  인물 {len(figures)}  사건 {len(events)}  장소 {len(places)}"
          f"  묶음서사 {len(arcs)}  원전 {len(sources)}")
    if orphans:
        print(f"  사건도 자식도 없는 인물 {len(orphans)}: {', '.join(orphans)}")


if __name__ == "__main__":
    main()
