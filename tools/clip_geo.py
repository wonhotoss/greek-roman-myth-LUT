"""sources/geo/ne_50m_land.geojson -> data/geo/mediterranean.json

Natural Earth 50m 육지 폴리곤을 지중해 동부(신화의 무대)로 잘라내고 좌표를 줄인다.
결과는 지도 렌더러가 그대로 SVG path 로 그린다. 한 번 만들면 다시 돌릴 일은 거의 없다.

원본: https://github.com/nvkelso/natural-earth-vector (public domain)

    python tools/clip_geo.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "geo" / "ne_50m_land.geojson"
OUT = ROOT / "data" / "geo" / "mediterranean.json"

# 카르타고(동경 10.3)부터 카우카소스(동경 44.5)까지 담고, 가장 바깥 장소에서 2도쯤 여유를 둔다.
# 여유가 없으면 지도가 그 장소 바로 옆에서 땅이 끝난 것처럼 보인다(카르타고에서 실제로 그랬다).
BOX = {"lon0": 8.0, "lon1": 48.0, "lat0": 28.0, "lat1": 48.0}
TOL = 0.02  # 도. 이보다 가까운 점은 버린다.


def clip_edge(ring, keep, intersect):
    """Sutherland-Hodgman 한 변."""
    out = []
    n = len(ring)
    for i in range(n):
        cur, prev = ring[i], ring[i - 1]
        cur_in, prev_in = keep(cur), keep(prev)
        if cur_in:
            if not prev_in:
                out.append(intersect(prev, cur))
            out.append(cur)
        elif prev_in:
            out.append(intersect(prev, cur))
    return out


def clip(ring):
    def lerp(a, b, t):
        return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]

    edges = [
        (lambda p: p[0] >= BOX["lon0"], lambda a, b: lerp(a, b, (BOX["lon0"] - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= BOX["lon1"], lambda a, b: lerp(a, b, (BOX["lon1"] - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= BOX["lat0"], lambda a, b: lerp(a, b, (BOX["lat0"] - a[1]) / (b[1] - a[1]))),
        (lambda p: p[1] <= BOX["lat1"], lambda a, b: lerp(a, b, (BOX["lat1"] - a[1]) / (b[1] - a[1]))),
    ]
    for keep, intersect in edges:
        ring = clip_edge(ring, keep, intersect)
        if not ring:
            return []
    return ring


def thin(ring):
    out = [ring[0]]
    for p in ring[1:]:
        q = out[-1]
        if abs(p[0] - q[0]) + abs(p[1] - q[1]) >= TOL:
            out.append(p)
    return out


def main():
    geo = json.loads(SRC.read_text(encoding="utf-8"))
    rings = []
    for feat in geo["features"]:
        g = feat["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            for ring in poly:  # 첫 링만이 아니라 구멍도 그대로 넣는다(호수 = 안 그려도 무해)
                clipped = clip([[float(x), float(y)] for x, y in ring])
                if len(clipped) < 4:
                    continue
                small = thin(clipped)
                if len(small) < 4:
                    continue
                rings.append([[round(x, 3), round(y, 3)] for x, y in small])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"box": BOX, "rings": rings}, ensure_ascii=False,
                              separators=(",", ":")), encoding="utf-8")
    pts = sum(len(r) for r in rings)
    print(f"{OUT.relative_to(ROOT).as_posix()} — 링 {len(rings)}개, 점 {pts:,}개, "
          f"{OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
