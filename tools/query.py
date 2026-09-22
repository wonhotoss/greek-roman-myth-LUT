"""build/myth.sqlite 에 묻는다.

    python tools/query.py 제우스                  # 검색 — 이름·다른 표기·한 줄·본문. 두 글자면 이름만 LIKE 로
    python tools/query.py figure zeus             # 인물 한 장: 부모·자식·짝·맡은 일·표시·나오는 사건(시간순)·원전
    python tools/query.py event medusa-slain      # 사건: 시대·자리·곳·등장·앞뒤·묶음·타래·이설·원전
    python tools/query.py place delphi            # 장소와 거기서 일어난 일
    python tools/query.py arc herakles-labors     # 묶음의 이야기 순서
    python tools/query.py thread zeus-partners    # 타래의 시간 순서와 "모른다" 표시
    python tools/query.py cards [kind]            # 인물 카드 표(card_figure 뷰). 사건이 많은 순
    python tools/query.py sql "SELECT ..."        # 아무 SQL

note 와 sensitivity 도 보여 준다 — 만드는 사람과 에이전트가 쓰는 도구다.
아이에게 보일 것은 public_* 뷰에서 뽑는다(render_sqlite.py).
"""

import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "build" / "myth.sqlite"


def width(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def pad(s, w):
    s = "" if s is None else str(s)
    return s + " " * max(0, w - width(s))


def table(rows, cols):
    if not rows:
        print("  (없음)")
        return
    ws = [max(width(c), *(width(r[i]) for r in rows)) for i, c in enumerate(cols)]
    print("  " + "  ".join(pad(c, w) for c, w in zip(cols, ws)))
    print("  " + "  ".join("-" * w for w in ws))
    for r in rows:
        print("  " + "  ".join(pad(v, w) for v, w in zip(r, ws)))


def connect():
    if not DB.exists():
        raise SystemExit("build/myth.sqlite 가 없다. 먼저: python tools/build.py && python tools/render_sqlite.py")
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def names(con, ids):
    return ", ".join(con.execute("SELECT name_ko FROM entry WHERE id = ?", (i,)).fetchone()[0] for i in ids)


def cites(con, eid):
    rows = con.execute("SELECT c.source_id, c.loc, s.author_ko, s.title_ko FROM citation c "
                       "JOIN source s ON s.id = c.source_id WHERE c.entry_id = ? ORDER BY c.pos", (eid,))
    return " / ".join(f"{r['author_ko']} 『{r['title_ko']}』 {r['loc']}" for r in rows)


def show_common(con, row, kind_label):
    print(f"\n{row['name_ko']}  `{row['id']}`  [{kind_label}]")
    aka = [r[0] for r in con.execute("SELECT name FROM aka WHERE entry_id = ?", (row["id"],))]
    if aka:
        print("  다른 표기:", ", ".join(aka))
    print(f"\n  {row['oneliner']}\n")
    for line in row["body"].splitlines():
        print("  " + line)
    if row["fun"]:
        print(f"\n  재밌는 것: {row['fun']}")
    for v in con.execute("SELECT text FROM variant WHERE entry_id = ? ORDER BY pos", (row["id"],)):
        print(f"  다른 이야기: {v[0]}")
    if row["sensitivity"] != "none":
        print(f"\n  민감도: {row['sensitivity']}")
    if row["note"]:
        print(f"  내부 메모: {row['note']}")


def search(con, q):
    if width(q) >= 3 and len(q) >= 3:
        rows = con.execute(
            "SELECT e.kind, e.id, e.name_ko, e.oneliner FROM search s JOIN entry e ON e.id = s.entry_id "
            "WHERE search MATCH ? ORDER BY bm25(search, 0, 0, 10, 6, 3, 1, 2) LIMIT 30",
            ('"' + q.replace('"', '""') + '"',)).fetchall()
        how = "trigram"
    else:
        like = f"%{q}%"
        rows = con.execute(
            "SELECT DISTINCT e.kind, e.id, e.name_ko, e.oneliner FROM entry e "
            "LEFT JOIN aka a ON a.entry_id = e.id LEFT JOIN figure f ON f.id = e.id "
            "WHERE e.name_ko LIKE ? OR a.name LIKE ? OR f.name_grc LIKE ? OR f.name_la LIKE ? "
            "ORDER BY e.kind, e.name_ko LIMIT 30", (like, like, like, like)).fetchall()
        how = "이름 LIKE (세 글자 미만)"
    print(f'"{q}" — {len(rows)}개 ({how})')
    table([(r["kind"], r["id"], r["name_ko"], r["oneliner"]) for r in rows], ["종류", "id", "이름", "한 줄"])


def figure(con, fid):
    f = con.execute("SELECT f.*, r.name_ko AS era_name FROM figure f JOIN era r ON r.n = f.era WHERE f.id = ?",
                    (fid,)).fetchone()
    if not f:
        raise SystemExit(f"인물 {fid} 없음")
    show_common(con, f, f"{f['kind']} · 시대 {f['era']} {f['era_name']}")
    alt = [x for x in (f["name_grc"] and f"그리스어 {f['name_grc']}", f["name_la"] and f"로마 {f['name_la']}") if x]
    if alt:
        print("  이름:", " / ".join(alt))
    rel = {
        "부모": [r[0] for r in con.execute("SELECT parent_id FROM figure_parent WHERE figure_id = ? ORDER BY pos", (fid,))],
        "자식": [r[0] for r in con.execute("SELECT child_id FROM figure_child WHERE figure_id = ?", (fid,))],
        "짝": [r[0] for r in con.execute("SELECT spouse_id FROM figure_spouse WHERE figure_id = ?", (fid,))],
    }
    for k, ids in rel.items():
        if ids:
            print(f"  {k}: {names(con, ids)}")
    for v in con.execute("SELECT text, parents FROM figure_parent_variant WHERE figure_id = ? ORDER BY pos", (fid,)):
        print(f"  다른 계보: {v['text'] or v['parents']}")
    for k, t in (("맡은 일", "figure_domain"), ("표시", "figure_symbol")):
        vals = [r[0] for r in con.execute(f"SELECT {t.split('_')[1]} FROM {t} WHERE figure_id = ? ORDER BY pos", (fid,))]
        if vals:
            print(f"  {k}: {', '.join(vals)}")
    if f["home"]:
        print(f"  사는 곳: {names(con, [f['home']])}")
    rows = con.execute("SELECT event_id, name_ko, role, era FROM figure_event WHERE figure_id = ? ORDER BY t0", (fid,)).fetchall()
    print(f"\n  나오는 사건 {len(rows)}건 (시간순)")
    table([(r["era"], r["event_id"], r["name_ko"], r["role"]) for r in rows], ["시대", "id", "사건", "역할"])
    print("\n  적힌 곳:", cites(con, fid))


def event(con, eid):
    e = con.execute("SELECT e.*, r.name_ko AS era_name FROM event e JOIN era r ON r.n = e.era WHERE e.id = ?",
                    (eid,)).fetchone()
    if not e:
        raise SystemExit(f"사건 {eid} 없음")
    show_common(con, e, f"시대 {e['era']} {e['era_name']} · seq {e['seq']} · {e['span_label']} · 시간축 {e['t0']}~{e['t1']}"
                + (" · 끝을 모른다" if e["open"] else ""))
    places = [r[0] for r in con.execute("SELECT place_id FROM event_place WHERE event_id = ? ORDER BY pos", (eid,))]
    print("  일어난 곳:", names(con, places) if places else ("원전이 말하지 않는다" if e["place_unknown"] else "아직 없음"))
    for role in ("주인공", "상대", "도움", "피해", "등장"):
        ids = [r[0] for r in con.execute("SELECT figure_id FROM event_cast WHERE event_id = ? AND role = ? ORDER BY pos", (eid, role))]
        if ids:
            print(f"  {role}: {names(con, ids)}")
    for label, sql in (("이 일이 있기 전에(원인)", "SELECT cause_id FROM event_cause WHERE event_id = ?"),
                       ("완전히 끝난 뒤에(after)", "SELECT before_id FROM event_after WHERE event_id = ?"),
                       ("이 일의 결과", "SELECT event_id FROM event_cause WHERE cause_id = ?")):
        ids = [r[0] for r in con.execute(sql, (eid,))]
        if ids:
            print(f"  {label}: {names(con, ids)}")
    if e["within"]:
        print(f"  품는 사건: {names(con, [e['within']])}")
    if e["arc"]:
        print(f"  묶음: {names(con, [e['arc']])}")
    for t in con.execute("SELECT thread_id, pos, unsure FROM event_thread WHERE event_id = ?", (eid,)):
        print(f"  타래: {names(con, [t['thread_id']])} {t['pos'] + 1}번째"
              + (" (앞 단계와의 순서는 옛 책에 없다)" if t["unsure"] else ""))
    print("\n  적힌 곳:", cites(con, eid))


def place(con, pid):
    p = con.execute("SELECT * FROM place WHERE id = ?", (pid,)).fetchone()
    if not p:
        raise SystemExit(f"장소 {pid} 없음")
    where = f"실제로 있는 곳 · {p['modern']} · 북위 {p['lat']} 동경 {p['lon']}" if p["kind"] == "real" \
        else f"이야기 속의 곳 · 층 {p['layer']}"
    show_common(con, p, where)
    rows = con.execute("SELECT event_id, name_ko, era FROM place_event WHERE place_id = ? ORDER BY t0", (pid,)).fetchall()
    print(f"\n  여기서 일어난 일 {len(rows)}건")
    table([(r["era"], r["event_id"], r["name_ko"]) for r in rows], ["시대", "id", "사건"])
    print("\n  적힌 곳:", cites(con, pid))


def arc(con, aid):
    a = con.execute("SELECT a.*, r.name_ko AS era_name FROM arc a JOIN era r ON r.n = a.era WHERE a.id = ?", (aid,)).fetchone()
    if not a:
        raise SystemExit(f"묶음 {aid} 없음")
    show_common(con, a, f"묶음 · 시대 {a['era']} {a['era_name']}")
    rows = con.execute("SELECT ae.pos, e.id, e.name_ko, e.oneliner FROM arc_event ae JOIN event e ON e.id = ae.event_id "
                       "WHERE ae.arc_id = ? ORDER BY ae.pos", (aid,)).fetchall()
    print("\n  이야기 순서")
    table([(r["pos"] + 1, r["id"], r["name_ko"], r["oneliner"]) for r in rows], ["", "id", "사건", "한 줄"])
    print("\n  적힌 곳:", cites(con, aid))


def thread(con, tid):
    t = con.execute("SELECT * FROM thread WHERE id = ?", (tid,)).fetchone()
    if not t:
        raise SystemExit(f"타래 {tid} 없음")
    show_common(con, t, "타래 · 시간 순서")
    rows = con.execute("SELECT s.pos, s.label, s.unsure, e.id, e.name_ko, e.era FROM thread_step s "
                       "JOIN event e ON e.id = s.event_id WHERE s.thread_id = ? ORDER BY s.pos", (tid,)).fetchall()
    print("\n  시간 순서 (? = 앞 단계와 어느 것이 먼저인지 옛 책에 없다)")
    table([("?" if r["unsure"] else "", r["pos"] + 1, r["era"], r["label"] or "", r["id"], r["name_ko"]) for r in rows],
          ["", "", "시대", "이름표", "id", "사건"])
    print("\n  적힌 곳:", cites(con, tid))


def cards(con, kind=None):
    sql = "SELECT * FROM card_figure" + (" WHERE kind = ?" if kind else "") + " ORDER BY n_events DESC, name_ko"
    rows = con.execute(sql, (kind,) if kind else ()).fetchall()
    print(f"인물 카드 {len(rows)}장" + (f" ({kind})" if kind else "") + " — 사건 수 순. soften 은 게임에서 걸러 낼 것")
    table([(r["name_ko"], r["kind"], r["era"], r["n_events"], r["n_lead"], r["n_rival"], r["n_children"], r["n_eras"],
            r["symbols"] or "", r["domains"] or "", "완화" if r["sensitivity"] == "soften" else "") for r in rows],
          ["이름", "종류", "시대", "사건", "주인공", "상대", "자식", "시대수", "표시", "맡은 일", "민감도"])


def sql(con, stmt):
    cur = con.execute(stmt)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    table([tuple(r) for r in rows], cols)
    print(f"  ({len(rows)}행)")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    con = connect()
    cmd, *rest = argv
    fns = {"figure": figure, "event": event, "place": place, "arc": arc, "thread": thread}
    if cmd in fns:
        if not rest:
            raise SystemExit(f"{cmd} 뒤에 id 를 준다")
        fns[cmd](con, rest[0])
    elif cmd == "cards":
        cards(con, rest[0] if rest else None)
    elif cmd == "sql":
        sql(con, " ".join(rest))
    else:
        search(con, " ".join(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
