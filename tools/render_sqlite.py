"""build/myth.json -> build/myth.sqlite

질의용 DB. TOML 이 진실의 원본이고 이것은 다른 셋과 같은 **산출물**이다 — 데이터를 고치면 다시 만든다.
지식팩 900KB 를 통째로 읽는 대신 필요한 항목만 뽑아 읽게 하는 것이 첫 목적이고,
카드·짝 맞추기·순서 맞추기처럼 항목을 다른 모양으로 잘라 쓰는 것이 둘째 목적이다.

  - 표 하나가 항목 종류 하나(figure / event / place / arc / thread / source / era).
    관계는 전부 표다 — figure_parent, event_cast, event_cause, arc_event, thread_step ...
  - entry 는 다섯 종류를 아우르는 색인이다. id 가 종류를 넘어 유일하다는 것은 빌드가 보장한다.
  - 빌드가 계산한 값(t0·t1, event.arc, 타래의 unsure)도 넣는다. 산출물이므로 파생 값을 담아도
    HANDOFF 규칙 6 에 어긋나지 않는다. 검사는 빌드가 이미 했고, 여기서는 외래 키로 한 번 더 걸린다.
  - search 는 FTS5 trigram. 한국어는 조사가 붙어 낱말 단위 색인이 맞지 않으므로 세 글자 조각으로 찾는다.
    두 글자 이름(헤라·레토)은 trigram 으로 못 찾는다 — tools/query.py 가 그때 LIKE 로 돈다.
  - public_* 뷰는 note 와 sensitivity 를 뺀 것이다. 아이가 보는 쪽은 이 뷰만 읽는다.
  - card_figure / card_event 뷰는 카드 한 장에 들어갈 것을 한 줄로 모은 것이다.

    python tools/build.py && python tools/render_sqlite.py
    python tools/query.py 제우스
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "build" / "myth.json"
OUT = ROOT / "build" / "myth.sqlite"

SCHEMA = """
CREATE TABLE era (
  n        INTEGER PRIMARY KEY,
  name_ko  TEXT NOT NULL,
  oneliner TEXT NOT NULL,
  t0       INTEGER NOT NULL,          -- 시간축에서 이 시대가 시작하는 칸
  t1       INTEGER NOT NULL
);

CREATE TABLE source (
  id         TEXT PRIMARY KEY,
  author_ko  TEXT NOT NULL,
  title_ko   TEXT NOT NULL,
  title_orig TEXT NOT NULL,
  written    TEXT NOT NULL,
  file       TEXT,
  translator TEXT,
  note       TEXT
);

-- 색인. 다섯 종류의 항목이 한 id 공간을 쓴다.
CREATE TABLE entry (
  id       TEXT PRIMARY KEY,
  kind     TEXT NOT NULL CHECK (kind IN ('figure', 'event', 'place', 'arc', 'thread')),
  name_ko  TEXT NOT NULL,
  oneliner TEXT NOT NULL
);

CREATE TABLE aka (
  entry_id TEXT NOT NULL REFERENCES entry(id),
  name     TEXT NOT NULL,
  PRIMARY KEY (entry_id, name)
);

-- 항목이 근거로 삼은 원전 위치. "apollodorus.library 2.4.2" 를 source_id 와 loc 으로 가른다.
CREATE TABLE citation (
  entry_id  TEXT NOT NULL REFERENCES entry(id),
  pos       INTEGER NOT NULL,
  source_id TEXT NOT NULL REFERENCES source(id),
  loc       TEXT NOT NULL,
  PRIMARY KEY (entry_id, pos)
);

-- 이설. "다른 이야기도 있어" 박스 하나가 한 줄.
CREATE TABLE variant (
  entry_id  TEXT NOT NULL REFERENCES entry(id),
  pos       INTEGER NOT NULL,
  source_id TEXT NOT NULL REFERENCES source(id),
  loc       TEXT NOT NULL,
  text      TEXT NOT NULL,
  PRIMARY KEY (entry_id, pos)
);

CREATE TABLE place (
  id          TEXT PRIMARY KEY REFERENCES entry(id),
  name_ko     TEXT NOT NULL,
  name_grc    TEXT,
  kind        TEXT NOT NULL CHECK (kind IN ('real', 'mythic')),
  lat         REAL, lon REAL, modern TEXT,          -- real
  layer       TEXT CHECK (layer IN ('sky', 'earth', 'sea', 'underworld', 'edge')),
  cx          REAL, cy REAL,                        -- mythic
  oneliner    TEXT NOT NULL,
  body        TEXT NOT NULL,
  fun         TEXT,
  sensitivity TEXT NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'soften')),
  note        TEXT,
  CHECK ((kind = 'real'   AND lat IS NOT NULL AND lon IS NOT NULL AND modern IS NOT NULL)
      OR (kind = 'mythic' AND layer IS NOT NULL AND cx IS NOT NULL AND cy IS NOT NULL))
);

CREATE TABLE figure (
  id          TEXT PRIMARY KEY REFERENCES entry(id),
  name_ko     TEXT NOT NULL,
  name_grc    TEXT,
  name_la     TEXT,
  kind        TEXT NOT NULL CHECK (kind IN ('primordial', 'titan', 'god', 'hero', 'human', 'monster', 'nymph', 'group')),
  era         INTEGER NOT NULL REFERENCES era(n),
  home        TEXT REFERENCES place(id),
  oneliner    TEXT NOT NULL,
  body        TEXT NOT NULL,
  fun         TEXT,
  sensitivity TEXT NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'soften')),
  note        TEXT
);

CREATE TABLE figure_parent (
  figure_id TEXT NOT NULL REFERENCES figure(id),
  pos       INTEGER NOT NULL,
  parent_id TEXT NOT NULL REFERENCES figure(id),
  PRIMARY KEY (figure_id, parent_id)
);

-- 이설 계보. parents 는 figure id 의 JSON 배열 — 드물게 읽는 것이라 표를 더 쪼개지 않는다.
CREATE TABLE figure_parent_variant (
  figure_id TEXT NOT NULL REFERENCES figure(id),
  pos       INTEGER NOT NULL,
  source_id TEXT NOT NULL REFERENCES source(id),
  loc       TEXT NOT NULL,
  parents   TEXT NOT NULL,
  text      TEXT,
  PRIMARY KEY (figure_id, pos)
);

CREATE TABLE figure_spouse (
  figure_id TEXT NOT NULL REFERENCES figure(id),
  spouse_id TEXT NOT NULL REFERENCES figure(id),
  PRIMARY KEY (figure_id, spouse_id)
);

CREATE TABLE figure_domain (
  figure_id TEXT NOT NULL REFERENCES figure(id),
  pos       INTEGER NOT NULL,
  domain    TEXT NOT NULL,
  PRIMARY KEY (figure_id, pos)
);

CREATE TABLE figure_symbol (
  figure_id TEXT NOT NULL REFERENCES figure(id),
  pos       INTEGER NOT NULL,
  symbol    TEXT NOT NULL,
  PRIMARY KEY (figure_id, pos)
);

CREATE TABLE arc (
  id          TEXT PRIMARY KEY REFERENCES entry(id),
  name_ko     TEXT NOT NULL,
  era         INTEGER NOT NULL REFERENCES era(n),
  oneliner    TEXT NOT NULL,
  body        TEXT NOT NULL,
  fun         TEXT,
  sensitivity TEXT NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'soften')),
  note        TEXT,
  t0          INTEGER NOT NULL,
  t1          INTEGER NOT NULL
);

CREATE TABLE event (
  id            TEXT PRIMARY KEY REFERENCES entry(id),
  name_ko       TEXT NOT NULL,
  era           INTEGER NOT NULL REFERENCES era(n),
  seq           INTEGER NOT NULL,
  span          TEXT NOT NULL CHECK (span IN ('moment', 'days', 'season', 'years', 'age')),
  span_label    TEXT NOT NULL,
  open          INTEGER NOT NULL CHECK (open IN (0, 1)),
  place_unknown INTEGER NOT NULL CHECK (place_unknown IN (0, 1)),
  within        TEXT REFERENCES event(id),
  arc           TEXT REFERENCES arc(id),           -- 빌드가 arc_event 에서 만든 역인덱스
  t0            INTEGER NOT NULL,                  -- 빌드가 푼 시간축 구간
  t1            INTEGER NOT NULL,
  oneliner      TEXT NOT NULL,
  body          TEXT NOT NULL,
  fun           TEXT,
  sensitivity   TEXT NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'soften')),
  note          TEXT,
  UNIQUE (era, seq)
);

CREATE TABLE event_place (
  event_id TEXT NOT NULL REFERENCES event(id),
  pos      INTEGER NOT NULL,                       -- 0 이 주 장소, 그 뒤는 이동 순서
  place_id TEXT NOT NULL REFERENCES place(id),
  PRIMARY KEY (event_id, pos)
);

CREATE TABLE event_cast (
  event_id  TEXT NOT NULL REFERENCES event(id),
  pos       INTEGER NOT NULL,
  figure_id TEXT NOT NULL REFERENCES figure(id),
  role      TEXT NOT NULL CHECK (role IN ('주인공', '상대', '도움', '피해', '등장')),
  PRIMARY KEY (event_id, figure_id)
);

CREATE TABLE event_cause (                         -- caused_by: 원인이 먼저 시작한다
  event_id TEXT NOT NULL REFERENCES event(id),
  cause_id TEXT NOT NULL REFERENCES event(id),
  PRIMARY KEY (event_id, cause_id)
);

CREATE TABLE event_after (                         -- after: 앞 사건이 완전히 끝난 뒤 시작한다
  event_id  TEXT NOT NULL REFERENCES event(id),
  before_id TEXT NOT NULL REFERENCES event(id),
  PRIMARY KEY (event_id, before_id)
);

CREATE TABLE arc_event (
  arc_id   TEXT NOT NULL REFERENCES arc(id),
  pos      INTEGER NOT NULL,                       -- 이야기 순서
  event_id TEXT NOT NULL UNIQUE REFERENCES event(id),   -- 한 사건은 한 묶음에만
  PRIMARY KEY (arc_id, pos)
);

CREATE TABLE thread (
  id          TEXT PRIMARY KEY REFERENCES entry(id),
  name_ko     TEXT NOT NULL,
  oneliner    TEXT NOT NULL,
  body        TEXT NOT NULL,
  fun         TEXT,
  sensitivity TEXT NOT NULL DEFAULT 'none' CHECK (sensitivity IN ('none', 'soften')),
  note        TEXT,
  t0          INTEGER NOT NULL,
  t1          INTEGER NOT NULL
);

CREATE TABLE thread_step (
  thread_id TEXT NOT NULL REFERENCES thread(id),
  pos       INTEGER NOT NULL,                      -- 시간축 순서. 빌드가 검사했다
  event_id  TEXT NOT NULL REFERENCES event(id),
  label     TEXT,
  unsure    INTEGER NOT NULL CHECK (unsure IN (0, 1)),   -- 앞 단계와의 순서를 원전이 말하지 않는다
  PRIMARY KEY (thread_id, pos),
  UNIQUE (thread_id, event_id)
);

-- 검색. 세 글자 조각(trigram)으로 한국어 본문 어디든 찾는다.
CREATE VIRTUAL TABLE search USING fts5(
  entry_id UNINDEXED, kind UNINDEXED, names, aka, oneliner, body, fun,
  tokenize = 'trigram'
);

-- ---------- 파생 뷰 ----------

CREATE VIEW figure_child AS
  SELECT parent_id AS figure_id, figure_id AS child_id FROM figure_parent;

CREATE VIEW figure_event AS
  SELECT c.figure_id, e.id AS event_id, e.name_ko, c.role, e.era, e.seq, e.t0, e.t1
  FROM event_cast c JOIN event e ON e.id = c.event_id;

CREATE VIEW place_event AS
  SELECT p.place_id, e.id AS event_id, e.name_ko, e.era, e.t0
  FROM event_place p JOIN event e ON e.id = p.event_id;

CREATE VIEW event_thread AS
  SELECT s.event_id, s.thread_id, t.name_ko, s.pos, s.unsure
  FROM thread_step s JOIN thread t ON t.id = s.thread_id;

-- ---------- 아이가 보는 쪽 — note 와 sensitivity 가 없다 ----------

CREATE VIEW public_figure AS
  SELECT id, name_ko, name_grc, name_la, kind, era, home, oneliner, body, fun FROM figure;
CREATE VIEW public_event AS
  SELECT id, name_ko, era, seq, span, span_label, open, place_unknown, within, arc, t0, t1, oneliner, body, fun FROM event;
CREATE VIEW public_place AS
  SELECT id, name_ko, name_grc, kind, lat, lon, modern, layer, cx, cy, oneliner, body, fun FROM place;
CREATE VIEW public_arc AS
  SELECT id, name_ko, era, oneliner, body, fun, t0, t1 FROM arc;
CREATE VIEW public_thread AS
  SELECT id, name_ko, oneliner, body, fun, t0, t1 FROM thread;

-- ---------- 카드 — 한 장에 들어갈 것을 한 줄로 ----------
-- sensitivity 를 남겨 둔 것은 게임을 만드는 쪽이 soften 항목을 걸러 내야 하기 때문이다. 카드에 찍지는 않는다.

CREATE VIEW card_figure AS
  SELECT f.id, f.name_ko, f.name_la, f.kind, f.era, r.name_ko AS era_name, f.oneliner, f.fun, f.sensitivity,
         (SELECT group_concat(p.name_ko, ', ') FROM figure_parent fp JOIN figure p ON p.id = fp.parent_id
            WHERE fp.figure_id = f.id ORDER BY fp.pos)                                          AS parents,
         (SELECT group_concat(domain, ', ') FROM figure_domain d WHERE d.figure_id = f.id)       AS domains,
         (SELECT group_concat(symbol, ', ') FROM figure_symbol s WHERE s.figure_id = f.id)       AS symbols,
         (SELECT count(*) FROM event_cast c WHERE c.figure_id = f.id)                            AS n_events,
         (SELECT count(*) FROM event_cast c WHERE c.figure_id = f.id AND c.role = '주인공')      AS n_lead,
         (SELECT count(*) FROM event_cast c WHERE c.figure_id = f.id AND c.role = '상대')        AS n_rival,
         (SELECT count(*) FROM figure_parent fp WHERE fp.parent_id = f.id)                       AS n_children,
         (SELECT count(DISTINCT e.era) FROM event_cast c JOIN event e ON e.id = c.event_id
            WHERE c.figure_id = f.id)                                                            AS n_eras
  FROM figure f JOIN era r ON r.n = f.era;

CREATE VIEW card_event AS
  SELECT e.id, e.name_ko, e.era, r.name_ko AS era_name, e.span_label, e.oneliner, e.fun, e.sensitivity,
         (SELECT name_ko FROM arc a WHERE a.id = e.arc)                                          AS arc_name,
         (SELECT group_concat(f.name_ko, ', ') FROM event_cast c JOIN figure f ON f.id = c.figure_id
            WHERE c.event_id = e.id AND c.role = '주인공')                                       AS leads,
         (SELECT group_concat(f.name_ko, ', ') FROM event_cast c JOIN figure f ON f.id = c.figure_id
            WHERE c.event_id = e.id AND c.role = '상대')                                         AS rivals,
         (SELECT group_concat(p.name_ko, ' → ') FROM event_place ep JOIN place p ON p.id = ep.place_id
            WHERE ep.event_id = e.id ORDER BY ep.pos)                                            AS places,
         (SELECT count(*) FROM event_cast c WHERE c.event_id = e.id)                             AS n_cast
  FROM event e JOIN era r ON r.n = e.era;
"""


def split_cite(s):
    sid, _, loc = s.partition(" ")
    return sid, loc


def main():
    if sqlite3.sqlite_version_info < (3, 34):
        raise SystemExit(f"SQLite {sqlite3.sqlite_version} — trigram 토크나이저는 3.34 부터다. 파이썬을 올린다.")
    D = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if OUT.exists():
        OUT.unlink()
    con = sqlite3.connect(OUT)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    con.execute("BEGIN")
    con.execute("PRAGMA defer_foreign_keys = ON")   # 참조 순서에 얽매이지 않고 넣고, 끝에 한 번 검사한다
    ex = con.execute
    many = con.executemany

    for e in D["eras"]:
        t0, t1 = D["axis"]["eras"][str(e["n"])]
        ex("INSERT INTO era VALUES (?,?,?,?,?)", (e["n"], e["name_ko"], e["oneliner"], t0, t1))
    for s in D["sources"]:
        ex("INSERT INTO source VALUES (?,?,?,?,?,?,?,?)",
           (s["id"], s["author_ko"], s["title_ko"], s["title_orig"], s["written"],
            s.get("file"), s.get("translator"), s.get("note")))

    def common(kind, it, names):
        """색인·다른 표기·원전·이설·검색 — 다섯 종류가 같이 갖는 것."""
        ex("INSERT INTO entry VALUES (?,?,?,?)", (it["id"], kind, it["name_ko"], it["oneliner"]))
        many("INSERT INTO aka VALUES (?,?)", [(it["id"], a) for a in dict.fromkeys(it.get("aka", []))])
        many("INSERT INTO citation VALUES (?,?,?,?)",
             [(it["id"], i, *split_cite(s)) for i, s in enumerate(it["sources"])])
        many("INSERT INTO variant VALUES (?,?,?,?,?)",
             [(it["id"], i, *split_cite(v["source"]), v["text"]) for i, v in enumerate(it.get("variants", []))])
        ex("INSERT INTO search VALUES (?,?,?,?,?,?,?)",
           (it["id"], kind, " ".join(x for x in names if x), " ".join(it.get("aka", [])),
            it["oneliner"], it["body"].strip(), it.get("fun") or ""))

    for p in D["places"]:
        common("place", p, [p["name_ko"], p.get("name_grc")])
        ex("INSERT INTO place VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
           (p["id"], p["name_ko"], p.get("name_grc"), p["kind"], p.get("lat"), p.get("lon"), p.get("modern"),
            p.get("layer"), p.get("cx"), p.get("cy"), p["oneliner"], p["body"].strip(), p.get("fun"),
            p.get("sensitivity", "none"), p.get("note")))

    for f in D["figures"]:
        common("figure", f, [f["name_ko"], f.get("name_grc"), f.get("name_la")])
        ex("INSERT INTO figure VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
           (f["id"], f["name_ko"], f.get("name_grc"), f.get("name_la"), f["kind"], f["era"], f.get("home"),
            f["oneliner"], f["body"].strip(), f.get("fun"), f.get("sensitivity", "none"), f.get("note")))
        many("INSERT INTO figure_parent VALUES (?,?,?)", [(f["id"], i, p) for i, p in enumerate(f.get("parents", []))])
        many("INSERT INTO figure_parent_variant VALUES (?,?,?,?,?,?)",
             [(f["id"], i, *split_cite(v["source"]), json.dumps(v["parents"]), v.get("text"))
              for i, v in enumerate(f.get("parents_variant", []))])
        many("INSERT INTO figure_spouse VALUES (?,?)", [(f["id"], s) for s in f.get("spouses", [])])
        many("INSERT INTO figure_domain VALUES (?,?,?)", [(f["id"], i, d) for i, d in enumerate(f.get("domains", []))])
        many("INSERT INTO figure_symbol VALUES (?,?,?)", [(f["id"], i, s) for i, s in enumerate(f.get("symbols", []))])

    for a in D["arcs"]:
        common("arc", a, [a["name_ko"]])
        ex("INSERT INTO arc VALUES (?,?,?,?,?,?,?,?,?,?)",
           (a["id"], a["name_ko"], a["era"], a["oneliner"], a["body"].strip(), a.get("fun"),
            a.get("sensitivity", "none"), a.get("note"), a["t0"], a["t1"]))
        many("INSERT INTO arc_event VALUES (?,?,?)", [(a["id"], i, e) for i, e in enumerate(a["events"])])

    for e in D["events"]:
        common("event", e, [e["name_ko"]])
        ex("INSERT INTO event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
           (e["id"], e["name_ko"], e["era"], e["seq"], e.get("span", "moment"), e["span_label"],
            int(bool(e.get("open"))), int(bool(e.get("place_unknown"))), e.get("within"), e.get("arc"),
            e["t0"], e["t1"], e["oneliner"], e["body"].strip(), e.get("fun"),
            e.get("sensitivity", "none"), e.get("note")))
        places = ([e["place"]] if "place" in e else []) + e.get("places", [])
        many("INSERT INTO event_place VALUES (?,?,?)", [(e["id"], i, p) for i, p in enumerate(places)])
        many("INSERT INTO event_cast VALUES (?,?,?,?)",
             [(e["id"], i, c["figure"], c["role"]) for i, c in enumerate(e["cast"])])
        many("INSERT INTO event_cause VALUES (?,?)", [(e["id"], c) for c in e.get("caused_by", [])])
        many("INSERT INTO event_after VALUES (?,?)", [(e["id"], a) for a in e.get("after", [])])

    for t in D["threads"]:
        common("thread", t, [t["name_ko"]])
        ex("INSERT INTO thread VALUES (?,?,?,?,?,?,?,?,?)",
           (t["id"], t["name_ko"], t["oneliner"], t["body"].strip(), t.get("fun"),
            t.get("sensitivity", "none"), t.get("note"), t["t0"], t["t1"]))
        many("INSERT INTO thread_step VALUES (?,?,?,?,?)",
             [(t["id"], i, s["event"], s.get("label"), int(s["unsure"])) for i, s in enumerate(t["steps"])])

    con.execute("COMMIT")
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    if bad:
        raise SystemExit("외래 키가 깨졌다 — 빌드가 통과한 JSON 이면 있을 수 없는 일이다:\n  "
                         + "\n  ".join(map(str, bad[:20])))
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    if ok != "ok":
        raise SystemExit(f"integrity_check: {ok}")
    con.execute("VACUUM")

    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE 'search_%' ORDER BY name")]
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    print(f"build/myth.sqlite — {OUT.stat().st_size:,} bytes, SQLite {sqlite3.sqlite_version}")
    print("  " + "  ".join(f"{t} {n}" for t, n in counts.items()))


if __name__ == "__main__":
    main()
