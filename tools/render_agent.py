"""build/myth.json -> build/agent-pack/

아이의 질문에 에이전트가 답하기 위한 지침 + 지식 팩.
음성 앞단(my-talking-claw, github.com/wonhotoss/my-talking-claw)이 `claude -p` 로 부르는
에이전트가 이 폴더를 작업 디렉터리로 삼으면 그대로 동작한다.

화면용(render_web.py)과 다른 점 둘:
  1. sensitivity 와 내부 메모를 **에이전트에게는 보여준다.** 무엇을 말하지 않을지 알아야 한다.
  2. 본문을 그대로 읽어 주는 것이 아니라, 세 문장으로 줄여 말하게 한다.

    python tools/build.py && python tools/render_agent.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "build" / "myth.json"
GUIDE = ROOT / "집필-지침.md"
OUT = ROOT / "build" / "agent-pack"

KIND = {"primordial": "첫 신", "titan": "티탄", "god": "올림포스 신", "hero": "영웅",
        "human": "사람", "monster": "괴물", "nymph": "님프", "group": "무리"}

CLAUDE_MD = """# 그리스 로마 신화 — 아이의 질문에 답하는 에이전트

## 너는 누구인가

혼자 읽는 8~10세 아이와 그리스 로마 신화에 대해 이야기한다.
말로 주고받는다(음성). 아이가 묻고, 너는 답한다.

## 반드시 지킬 것

`집필-지침.md` 의 규칙을 전부 지킨다. 특히:

1. **`knowledge/` 안에 없는 것은 모른다고 한다.** 지어내지 않는다.
   "그건 내가 가진 이야기에 없어. 대신 ○○ 이야기는 알아."
2. **한 번에 세 문장.** 음성이라 길면 아이가 놓친다.
3. **끝에 되물음 하나.** "다음엔 누구 이야기가 궁금해?"
4. 아이가 무서워하면("무서워", "그만") 즉시 다른 이야기로 옮긴다.
5. `민감도: 완화` 로 표시된 항목은 지침의 완화 규칙대로 한 번만 답하고,
   또 파고들면 "그건 좀 더 커서 읽을 이야기야"로 멈춘다.
6. `내부 메모` 는 **그대로 읽어 주지 않는다.** 무엇을 말하지 않을지 알려주는 편집 지시다.
7. 로마 이름이나 다른 표기로 물어도 알아듣는다. 답할 때는 주 표기로 바꿔 말하고 한 번만 알려준다.
   "주피터는 그리스에서는 제우스라고 해."
8. 본문을 그대로 읽지 않는다. 아이가 물은 것에 맞춰 세 문장으로 줄여 말한다.

## 무엇이 어디 있는가

| 파일 | 내용 |
|---|---|
| `knowledge/00-index.md` | 전체 색인. 이름·다른 표기 → id. **이름을 찾을 때 여기부터 본다** |
| `knowledge/10-eras.md` | 아홉 시대. "언제야?" 라는 질문의 답은 연도가 아니라 시대다 |
| `knowledge/20-figures.md` | 사람·신·괴물 전문 |
| `knowledge/30-events.md` | 사건 전문. 시대·순서대로 |
| `knowledge/40-places.md` | 장소. 실제로 있는 곳과 이야기 속의 곳을 구분해서 답한다 |
| `knowledge/50-arcs.md` | 여러 사건이 이어진 이야기 묶음 |
| `knowledge/60-sources.md` | 원전. "그거 어디 나와?" 에 답할 때 |

## 자주 오는 질문에 답하는 법

- **"언제야?"** — 연도로 답하지 않는다. 신화에는 연도가 없다.
  "몇 번째 세대인지"로 답한다. 예: "제우스는 세 번째 임금이야. 할아버지가 우라노스, 아버지가 크로노스."
- **"어디야?"** — 실제로 있는 곳이면 지금의 지명까지 말해 준다.
  이야기 속의 곳이면 **없다는 것을 분명히 말한다.** "타르타로스는 실제로는 없어. 이야기 속의 곳이야."
- **"누가 더 세?"** — 원전에 답이 있는 경우만 답한다. 없으면 없다고 한다.
- **"진짜야?"** — "옛날 그리스 사람들이 믿었던 이야기야. 지금은 이야기로 남아 있어."
  신화를 사실로도, 거짓으로도 말하지 않는다.
- **"○○ 이야기 해 줘"** — `50-arcs.md` 에 묶음이 있으면 순서대로 하나씩 준다.
  한 번에 한 사건, 세 문장, 끝에 "다음 이야기 들을래?"
"""


def block(title, lines):
    return f"## {title}\n\n" + "\n".join(lines) + "\n\n"


def fig_md(f, by):
    L = [f"### {f['name_ko']}  `{f['id']}`", ""]
    names = [x for x in [
        f.get("name_grc") and f"그리스명 {f['name_grc']}",
        f.get("name_la") and f"로마명 {f['name_la']}",
        f.get("aka") and "다른 표기 " + ", ".join(f["aka"])] if x]
    if names:
        L.append("- 이름: " + " / ".join(names))
    L.append(f"- 종류: {KIND[f['kind']]} · 시대 {f['era']}")
    for label, key in (("부모", "parents"), ("짝", "spouses"), ("자식", "children")):
        if f.get(key):
            L.append(f"- {label}: " + ", ".join(by[i]["name_ko"] for i in f[key]))
    if f.get("domains"):
        L.append("- 맡은 일: " + ", ".join(f["domains"]))
    if f.get("symbols"):
        L.append("- 알아보는 표시: " + ", ".join(f["symbols"]))
    if f.get("home"):
        L.append(f"- 사는 곳: {by[f['home']]['name_ko']}")
    if f["events"]:
        L.append("- 나오는 사건: " + ", ".join(
            f"{by[e['event']]['name_ko']}({e['role']})" for e in f["events"]))
    L += ["", f"**{f['oneliner']}**", "", f["body"].strip()]
    if f.get("fun"):
        L += ["", f"재밌는 것: {f['fun']}"]
    for v in f.get("parents_variant", []):
        # text 는 스키마에 없는 선택 필드다(데이터-모델.md). 없으면 parents 로 문장을 만든다.
        text = v.get("text") or (
            "부모를 " + ", ".join(by[p]["name_ko"] for p in v.get("parents", []))
            + " 라고 하는 이야기도 있다.")
        L += ["", f"다른 이야기: {text}"]
    if f.get("sensitivity") == "soften":
        L += ["", "> 민감도: 완화"]
    if f.get("note"):
        L += ["", f"> 내부 메모(그대로 읽지 않는다): {f['note']}"]
    L += ["", "적힌 곳: " + " / ".join(f["sources"]), ""]
    return "\n".join(L)


def event_md(e, by, eras):
    L = [f"### {e['name_ko']}  `{e['id']}`", ""]
    if e.get("aka"):
        L.append("- 다른 이름: " + ", ".join(e["aka"]))
    L.append(f"- 시대 {e['era']} ({eras[e['era']]['name_ko']}), 그 안에서 {e['seq']}번째 자리")
    places = ([e["place"]] if "place" in e else []) + e.get("places", [])
    if places:
        L.append("- 일어난 곳: " + ", ".join(
            f"{by[p]['name_ko']}({'실제로 있는 곳' if by[p]['kind'] == 'real' else '이야기 속의 곳'})"
            for p in places))
    for role in ("주인공", "상대", "도움", "피해", "등장"):
        who = [by[c["figure"]]["name_ko"] for c in e["cast"] if c["role"] == role]
        if who:
            L.append(f"- {role}: " + ", ".join(who))
    if e.get("caused_by"):
        L.append("- 이 일이 있기 전에: " + ", ".join(by[i]["name_ko"] for i in e["caused_by"]))
    if e.get("arc"):
        L.append(f"- 묶음 서사: {by[e['arc']]['name_ko']}")
    L += ["", f"**{e['oneliner']}**", "", e["body"].strip()]
    if e.get("fun"):
        L += ["", f"재밌는 것: {e['fun']}"]
    for v in e.get("variants", []):
        L += ["", f"다른 이야기: {v['text']}"]
    if e.get("sensitivity") == "soften":
        L += ["", "> 민감도: 완화"]
    if e.get("note"):
        L += ["", f"> 내부 메모(그대로 읽지 않는다): {e['note']}"]
    L += ["", "적힌 곳: " + " / ".join(e["sources"]), ""]
    return "\n".join(L)


def place_md(p, by):
    L = [f"### {p['name_ko']}  `{p['id']}`", ""]
    if p["kind"] == "real":
        L.append(f"- **실제로 있는 곳.** 지금의 {p['modern']} (북위 {p['lat']}, 동경 {p['lon']})")
    else:
        L.append("- **이야기 속의 곳. 실제로는 없다.** "
                 f"세계의 층: {p['layer']}")
    if p.get("aka"):
        L.append("- 다른 이름: " + ", ".join(p["aka"]))
    if p["events"]:
        L.append("- 여기서 일어난 일: " + ", ".join(by[i]["name_ko"] for i in p["events"]))
    L += ["", f"**{p['oneliner']}**", "", p["body"].strip()]
    if p.get("fun"):
        L += ["", f"재밌는 것: {p['fun']}"]
    if p.get("note"):
        L += ["", f"> 내부 메모(그대로 읽지 않는다): {p['note']}"]
    L += ["", "적힌 곳: " + " / ".join(p["sources"]), ""]
    return "\n".join(L)


def main():
    D = json.loads(BUNDLE.read_text(encoding="utf-8"))
    by = {}
    for k in ("figures", "events", "places", "arcs"):
        for it in D[k]:
            by[it["id"]] = it
    eras = {e["n"]: e for e in D["eras"]}

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "knowledge").mkdir(parents=True)

    (OUT / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    shutil.copy(GUIDE, OUT / GUIDE.name)

    K = OUT / "knowledge"

    # 색인 — 이름과 다른 표기로 id 를 찾는 표
    TYPE = {"figures": "사람·신", "events": "사건", "places": "장소", "arcs": "이야기 묶음"}
    rows = []
    for k in ("figures", "events", "places", "arcs"):
        for it in D[k]:
            alts = ", ".join([x for x in ([it.get("name_grc"), it.get("name_la")]
                                          + (it.get("aka") or [])) if x])
            rows.append(f"| {it['name_ko']} | {alts} | `{it['id']}` | {TYPE[k]} | {it['oneliner']} |")
    K.joinpath("00-index.md").write_text(
        "# 색인\n\n이름이나 다른 표기로 항목을 찾는 표. 아이가 어떤 이름으로 물어도 여기서 찾는다.\n\n"
        "| 주 표기 | 다른 표기 | id | 종류 | 한 줄 |\n|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n", encoding="utf-8")

    K.joinpath("10-eras.md").write_text(
        "# 아홉 시대\n\n신화에는 연도가 없다. \"언제야?\" 라는 질문에는 연도가 아니라 "
        "이 시대와 세대로 답한다.\n\n| 시대 | 이름 | 내용 |\n|---|---|---|\n"
        + "\n".join(f"| {e['n']} | {e['name_ko']} | {e['oneliner']} |" for e in D["eras"])
        + "\n", encoding="utf-8")

    K.joinpath("20-figures.md").write_text(
        "# 사람·신·괴물\n\n" + "\n".join(fig_md(f, by) for f in D["figures"]), encoding="utf-8")
    K.joinpath("30-events.md").write_text(
        "# 사건\n\n시대와 순서대로.\n\n"
        + "\n".join(event_md(e, by, eras) for e in D["events"]), encoding="utf-8")
    K.joinpath("40-places.md").write_text(
        "# 장소\n\n실제로 있는 곳과 이야기 속의 곳을 반드시 구분해서 답한다.\n\n"
        + "\n".join(place_md(p, by) for p in D["places"]), encoding="utf-8")
    K.joinpath("50-arcs.md").write_text(
        "# 이야기 묶음\n\n한 번에 한 사건씩, 순서대로 준다.\n\n"
        + "\n".join(
            f"### {a['name_ko']}  `{a['id']}`\n\n**{a['oneliner']}**\n\n{a['body'].strip()}\n\n"
            + "\n".join(f"{i + 1}. {by[e]['name_ko']} — {by[e]['oneliner']}"
                        for i, e in enumerate(a["events"]))
            + f"\n\n적힌 곳: {' / '.join(a['sources'])}\n"
            for a in D["arcs"]), encoding="utf-8")
    K.joinpath("60-sources.md").write_text(
        "# 원전\n\n\"그거 어디 나와?\" 라고 물으면 이 표로 답한다.\n\n"
        "| id | 지은이 | 제목 | 원제 | 쓰인 때 |\n|---|---|---|---|---|\n"
        + "\n".join(f"| `{s['id']}` | {s['author_ko']} | 『{s['title_ko']}』 | "
                    f"{s['title_orig']} | {s['written']} |" for s in D["sources"])
        + "\n", encoding="utf-8")

    (OUT / "README.md").write_text(f"""# agent-pack — 음성 에이전트에 얹는 방법

이 폴더는 `tools/render_agent.py` 가 만든 산출물이다. 직접 고치지 말고 `data/` 를 고쳐 다시 만든다.

## my-talking-claw 에 붙이기

`my-talking-claw` 의 에이전트 게이트웨이는 질문을 `claude -p` 로 넘긴다.
이 폴더를 그 프로세스의 작업 디렉터리로 주면 `CLAUDE.md` 가 자동으로 읽힌다.

```sh
cd build/agent-pack
claude -p "제우스는 누구야?"
```

작업 디렉터리를 바꿀 수 없으면 지침을 직접 얹는다.

```sh
claude -p --append-system-prompt "$(cat build/agent-pack/CLAUDE.md)" "제우스는 누구야?"
```

## 들어 있는 것

- `CLAUDE.md` — 에이전트 지침. 어떻게 답할지
- `집필-지침.md` — 문장·이름·수위·톤 규칙. `data/` 를 쓸 때와 같은 기준
- `knowledge/` — 지식 {len(D['figures'])}인물 / {len(D['events'])}사건 / {len(D['places'])}장소 / {len(D['arcs'])}묶음서사

## 화면용과 다른 점

화면(`build/myth.html`)에는 `민감도`와 `내부 메모`를 그리지 않는다. 아이가 보는 것이다.
에이전트에게는 준다. **무엇을 말하지 않을지 알아야 하기 때문이다.**
""", encoding="utf-8")

    files = sorted(OUT.rglob("*"))
    total = sum(f.stat().st_size for f in files if f.is_file())
    print(f"build/agent-pack/ — 파일 {sum(1 for f in files if f.is_file())}개, {total:,} bytes")
    for f in files:
        if f.is_file():
            print(f"  {f.relative_to(OUT).as_posix()}  {f.stat().st_size:,}")


if __name__ == "__main__":
    main()
