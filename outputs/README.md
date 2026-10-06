# outputs/ — 층 4. 산출물

넷째 층이다. DB([db/](../db/README.md))를 읽어 **사람이 쓰는 것**을 만든다. 혼자 읽는 8~10세 아이가
그리스 로마 신화를 시간순·지리·인물·사건으로 찾아보게 하는 것이 첫 목표였고, 산출물은 계속 더해진다.

## 규칙

- **렌더러는 `db/build/myth.json` 만 읽는다.** 산출물에 필요한 값을 렌더러 안에서 만들어 쓰지 않는다 —
  다른 산출물에서 사라진다. 필요하면 DB 에 넣는다.
- 산출물 하나가 폴더 하나다. 렌더러(`render_*.py`)와 그 결과물, 그 산출물만의 구상·메모를 한 폴더에 둔다.
- 결과물은 **커밋한다.** 자료를 받는 사람이 파이썬 없이 `web/myth.html` 하나만 열어도 되게 하려는 것이다.
  DB 를 고치면 렌더러를 모두 다시 돌려 함께 커밋한다.
- 아이가 보는 산출물(web·print)에는 `sensitivity`·`note`·`record` 를 그리지 않는다. 에이전트 팩에는 준다 —
  무엇을 말하지 않을지 알아야 하기 때문이다.

## 있는 것

| 폴더 | 산출물 | 만드는 법 | 상태 |
|---|---|---|---|
| [web/](web/) | `myth.html` — 단일 파일·오프라인 탐색. 언제 어디서(시간축 커서 + 지도) / 시간순 / 땅과 세계 / 계보 / 이야기(타래·묶음) / 검색 | `python outputs/web/render_web.py` | 아홉 시대 전부 |
| [print/](print/) | `print-timeline.html`(A3 가로 5쪽) · `print-family.html`(A3 세로) · `print-map.html`(A3 가로) · `print-cards.html`(A4, 인물 카드 72장) — 브라우저에서 인쇄 | `python outputs/print/render_print.py` | 아홉 시대 전부 |
| [agent/](agent/) | `pack/` — [my-talking-claw](https://github.com/wonhotoss/my-talking-claw) 에 얹는 지침 + 지식(900KB). `cd outputs/agent/pack && claude -p "제우스는 누구야?"` | `python outputs/agent/render_agent.py` | 구조 확인. 실제 음성 세션 미실측 |
| [poster/](poster/) | 인포그래픽 포스터 — 벽에 붙이는 한 장. 첫 장은 「헤라클레스의 열두 가지 일」 | 렌더러 없음. [포스터-구상.md](poster/포스터-구상.md) | 구상 |
| [quiz/](quiz/) | `quiz.html` — 4지선다 퀴즈. 인물(설명·재밌는 것·주인공·맞선 이·부모·짝)·장소(설명·사건의 자리)·사물(상징물·맡은 일) 1032문제를 빌드 때 뽑아 넣고, 한 판 열 문제씩 돌려 쓴다. 맞히면 다음, 틀리면 다시. `quiz-greek.html` 은 로마 건국 신화(시대 8)를 뺀 판, 964문제 | `python outputs/quiz/render_quiz.py` (두 판 모두) | 아홉 시대 전부 / 그리스 판. 둘 다 claude.ai 아티팩트로도 올려 둠 |

산출물을 하나 더 만들 때는 폴더를 하나 더 만들고 이 표에 줄을 더한다(퀴즈가 그렇게 들어온 첫 예다 — 렌더러 하나, 결과물 하나, DB 는 손대지 않았다). 후보로 적어 둔 것 —
카드 놀이(짝 맞추기·순서 맞추기, `db/build/myth.sqlite` 의 `card_*` 뷰가 재료).

## 전부 다시 만들기

```sh
python db/tools/build.py
python outputs/web/render_web.py
python outputs/print/render_print.py
python outputs/agent/render_agent.py
python outputs/quiz/render_quiz.py
```
