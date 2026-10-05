# db/ — 층 3. DB화

셋째 층이다. 원전([sources/](../sources/README.md))을 읽고 정리한 것([notes/](../notes/README.md))을
**명확하고 구조화된 형태로** 적는다. 인물·사건·장소·시대와 그 관계가 id 로 이어진, 기계가 읽는 지식이다.
산출물([outputs/](../outputs/README.md))은 전부 여기서만 읽는다.

## 무엇이 DB 인가

| 자리 | 형태 | 역할 |
|---|---|---|
| `db/data/*.toml` | TOML, 손으로 쓴다 | **진실의 원본.** 항목·관계·주석·집필 메모가 여기 있다 |
| `db/build/myth.json` | JSON, `db/tools/build.py` 가 만든다 | 검증을 통과하고 파생 값(역인덱스·시간축 좌표·타래 순서)이 채워진 DB 한 벌. 산출물이 읽는 것 |
| `db/build/myth.sqlite` | SQLite, `db/tools/render_sqlite.py` 가 만든다 | 같은 DB 의 질의용 형태. 커밋하지 않는다 |
| `db/build/불확실-점검.md` | 빌드가 만든다 | DB 가 모르는 것의 자동 목록 |

TOML 을 원본으로 두는 까닭은 주석과 집필 메모, git 이력이 자료의 절반이기 때문이다.
JSON 과 SQLite 는 같은 지식의 다른 형태이고 언제든 다시 만든다.

## 규칙을 적은 문서

| 문서 | 내용 |
|---|---|
| [데이터-모델.md](데이터-모델.md) | 스키마와 그 근거. 연대 없는 시간축, 실제 땅과 신화 속 세계, 이름 셋, 이설, 수위, 구간, 타래 — 일곱 난제와 해법 |
| [집필-지침.md](집필-지침.md) | `body` 를 쓰는 규칙. 8~10세 문장, 이름 표기, 무엇을 그대로 주고 무엇을 완화하는가, `record` |
| [불확실-목록.md](불확실-목록.md) | DB 가 모르는 것에 대한 판단. 순서를 모르는 짝, 장소 미상, 원전 안의 어긋남, 스키마 후보 |

어기면 자료가 못 쓰게 되는 규칙 여덟은 [HANDOFF.md](../HANDOFF.md) 에 있다. 핵심은 둘 — 원전에 없는 것을
쓰지 않는다, 모르는 것을 아는 것처럼 그리지 않는다.

## 돌리는 법

```sh
python db/tools/build.py          # data/*.toml 검증 → build/myth.json, build/불확실-점검.md
python db/tools/render_sqlite.py  # build/myth.json → build/myth.sqlite
python db/tools/query.py 제우스    # 검색. figure/event/place/arc/thread/cards/sql 도 된다
python db/tools/clip_geo.py       # sources/geo → data/geo/mediterranean.json (해안선을 바꿀 때만)
```

의존성 없음. 표준 라이브러리 `tomllib`·`sqlite3`(파이썬 3.11+).
`build.py` 는 **깨지면 즉시 죽는다** — 없는 id, 스키마에 없는 필드, 순환, `seq` 충돌, 타래 순서 어긋남.
기본값을 채우거나 참조를 건너뛰지 않는다.

## 항목을 하나 더 쓰려면

1. [데이터-모델.md](데이터-모델.md) 의 스키마와 [집필-지침.md](집필-지침.md) 의 문장 규칙을 읽는다.
2. 같은 성격의 기존 파일을 표본으로 삼는다(영웅 서사는 `data/events/era5-herakles.toml`).
3. 원전 구절을 `sources/` 에서 찾아 인용 위치를 확인한다(위치 표기는 [notes/원전별-파악.md](../notes/원전별-파악.md)).
   읽으며 안 것 가운데 항목에 들어가지 않는 것은 `notes/` 에 남긴다.
4. 사건이면 `era` 안에서 `seq` 가 겹치지 않게 잡고(10 간격), 이야기 안의 순서는 `caused_by`/`after` 로 함께 적는다.
5. 묶음서사(`data/arcs.toml`)에 넣는다. 여러 묶음을 가로지르면 타래(`data/threads.toml`)에도 넣는다.
6. 빌드 → 산출물 렌더러를 돌리고(`outputs/`), `build/불확실-점검.md` 가 늘지 않았는지 본다.

## 지금 있는 것

인물 309 · 사건 275 · 장소 87(실제 66, 이야기 속 21) · 묶음서사 33 · 타래 5 · 원전 13 — 아홉 시대 전부.
시대별 분량은 [루트 README](../README.md) 에 있다.
