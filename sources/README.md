# sources/ — 층 1. 원전 수집

이 저장소의 첫 층이다. **그리스 로마 신화의 원전을 모은다.** 다른 세 층(정리·DB·산출물)은 전부 여기서 출발한다.

## 방침 — 수집한 것은 일단 모두 원전이다

원전과 복각(번역·편집), 재창작(재화·개작)을 가르는 기준이 아직 없다. 호메로스는 원전이고
불핀치는 19세기 재화인데, 그 사이에 있는 것(헬레니즘기의 편람, 로마 시인의 재서술, 근대 번역)을
어디서 끊을지 정하지 못했다. 그래서 **지금은 수집된 문서를 모두 원전으로 둔다.** 기준이 서면 그때 가른다.

그 방침과 별개로, DB 층은 항목의 근거(`sources` 필드)로 무엇을 인용할지 따로 정한다 —
불핀치는 수집은 했으나 아직 근거로 인용하지 않았다([db/data/sources.toml](../db/data/sources.toml) 의 note).
수집 방침과 인용 방침은 다른 층의 일이다.

## 있는 것

전부 공개 도메인 번역의 전문이다. 12MB, 전부 커밋한다(매번 다시 받지 않기 위해).

| 파일 | 내용 | 출처 | 본문 안의 위치 표시 |
|---|---|---|---|
| `hesiod-homerichymns-evelyn-white.txt` | 헤시오도스 『신들의 계보』『일과 날』 + 『호메로스 찬가』 (Evelyn-White 1914) | Gutenberg #348 | 행 번호 `(ll. 116-138)` |
| `apollodorus-library-{1,2,3,E}-frazer.{html,txt}` | 아폴로도로스 『신화집』 1~3권 + 요약(Epitome) (Frazer 1921) | theoi.com | 절 번호 `[2.4.2]` |
| `homer-iliad-butler.txt` | 호메로스 『일리아스』 (Butler 1898) | Gutenberg #2199 | `BOOK I` … 권 표제 |
| `homer-odyssey-butler.txt` | 호메로스 『오디세이아』 (Butler 1900) | Gutenberg #1727 | `BOOK I` … 권 표제 |
| `ovid-metamorphoses-1-7-more.txt`, `-8-15-` | 오비디우스 『변신 이야기』 (More 1922) | Gutenberg #21765, #26073 | 권 표제 + 행 번호 |
| `virgil-aeneid-dryden.txt` | 베르길리우스 『아이네이스』 (Dryden 1697) | Gutenberg #228 | 권 표제 |
| `livy-rome-1-8-roberts.txt` | 리비우스 『로마사』 1~8권 (Roberts 1912) | Gutenberg #19725 | 권 표제 + 장 번호 `4. ` |
| `pausanias-greece-v{1,2}-frazer.txt` | 파우사니아스 『그리스 안내기』 (Frazer 1898) | Gutenberg #68946, #68680 | `BOOK I.--ATTICA.` … 권·지역 표제 |
| `hyginus-fabulae-grant.txt` | 히기누스 『이야기 모음』 전문 (Grant 1960) | topostext.org/work/206 | 우화 번호 `[57]` |
| `bulfinch-mythology.txt` | 불핀치 『The Age of Fable』 (1855) | Gutenberg #4928 | `CHAPTER I` … |
| `geo/ne_50m_land.geojson` | Natural Earth 50m 육지 (public domain) | nvkelso/natural-earth-vector | — |

theoi.com 의 HTML 은 일회성 추출로 `.txt` 를 함께 두었다. 히기누스는 theoi.com 이 페이지마다 우화 넷씩만
내주어(2026-09-03 확인) 같은 Grant 번역 전문을 싣는 ToposText 에서 받았다.

**수집하지 않은 것.** 미래엔아이세움 『처음 읽는 그리스 로마 신화』(최설희 글, 전 15권)는 범위와 순서의
참고로만 쓰고 여기 두지 않는다(저작권 있는 현대 어린이책). DB 에는 `aiseum.first-myth` 로 이름만 있다.

## 다시 받는 법

```sh
cd sources
curl -sSL -O "https://www.gutenberg.org/cache/epub/<번호>/pg<번호>.txt"
curl -sSL -A "Mozilla/5.0" -O "https://www.theoi.com/Text/Apollodorus1.html"
curl -sSL -A "Mozilla/5.0" -o hyginus.html "https://topostext.org/work/206"
python tools/extract_hyginus.py hyginus.html hyginus-fabulae-grant.txt      # 지명 링크를 벗기고 우화 번호를 [57] 로 남긴다
curl -sSL -o geo/ne_50m_land.geojson \
  "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
```

`tools/` 에는 **수집에만** 쓰는 스크립트를 둔다. 수집한 것을 DB 로 바꾸는 스크립트(`clip_geo.py` 등)는 `db/tools/` 다.

## 다음에 모을 것

- **그림.** 공개 도메인 도판(그리스 도기, 19세기 판화). 포스터와 카드가 처음 쓴다
  ([outputs/poster/포스터-구상.md](../outputs/poster/포스터-구상.md) "그래픽 파이프라인"). 자리는 `sources/images/`,
  출처·라이선스는 `db/data/images.toml` 에 적는 것으로 구상해 두었다.
- 아직 항목과 대조하지 않은 부분이 있는 원전(히기누스 117~125 등)은 수집의 문제가 아니라 정리의 문제다 —
  [notes/](../notes/README.md).
