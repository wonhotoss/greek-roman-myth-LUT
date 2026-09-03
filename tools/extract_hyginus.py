"""topostext.org/work/206 (히기누스 『이야기 모음』, Mary Grant 역) HTML -> sources/hyginus-fabulae-grant.txt

    curl -sSL -A "Mozilla/5.0" -o hyginus.html "https://topostext.org/work/206"
    python tools/extract_hyginus.py hyginus.html sources/hyginus-fabulae-grant.txt

우화 번호가 <p id='urn:cts:latinLit:phi1263.phi001:N'> 에 있다. 그 번호를 [N] 으로 단락 앞에 남긴다.
아폴로도로스의 [2.5.1] 표시와 같은 방식이어서 `sources = ["hyginus.fabulae 57"]` 를 grep 으로 바로 찾는다.
theoi.com 은 2026-09-03 현재 페이지마다 우화 넷씩만 내주어 전문을 받을 수 없었다. ToposText 가 같은
Grant 번역 전문을 싣고 공개 도메인이라 밝히고 있어 거기서 받는다. ToposText 의 지명 링크·날짜 표시는 뺀다.
"""
import html
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
PREFIX = "urn:cts:latinLit:phi1263.phi001:"

raw = SRC.read_text(encoding="utf-8", errors="replace")
marker = re.compile(rf"<[a-zA-Z]+[^>]*\sid='{re.escape(PREFIX)}([^']+)'[^>]*>")
hits = list(marker.finditer(raw))
assert hits, "우화 표시를 찾지 못했다"

# 마지막 우화 뒤의 꼬리(색인·푸터)를 잘라 낸다.
tail = raw[hits[-1].end():]
cut = min([m.start() for m in [re.search(r'<div id="footer"', tail),
                               re.search(r'id="paragraphs_index"', tail),
                               re.search(r'<!--\s*Footer', tail),
                               re.search(r'<div[^>]*class="[^"]*footer', tail)] if m] or [len(tail)])
raw = raw[:hits[-1].end() + cut]
parts = marker.split(raw)  # [머리, id1, 본문1, id2, 본문2, ...]


def clean(seg):
    seg = re.sub(r"<!--.*?-->", " ", seg, flags=re.S)
    seg = re.sub(r"<br\s*/?>", "\n", seg, flags=re.I)
    seg = re.sub(r"</p\s*>", "\n", seg, flags=re.I)
    seg = re.sub(r"<[^>]+>", " ", seg)
    seg = html.unescape(seg)
    seg = re.sub(r"[ \t ]+", " ", seg)
    seg = re.sub(r"\s*\n\s*", "\n", seg)
    # ToposText 가 단락마다 붙이는 메타데이터. 원문이 아니다.
    seg = "\n".join(l for l in seg.split("\n")
                    if not re.match(r"^(Event Date:|END$)", l.strip()))
    return seg.strip()


lines = [
    "Hyginus, Fabulae. Translated by Mary Grant, The Myths of Hyginus (University of Kansas Press, 1960).",
    "Text from https://topostext.org/work/206 (ToposText, ed. Brady Kiesling; text via theoi.com),",
    "which states the translation is now in the public domain. ToposText's own markup is CC BY-NC 4.0.",
    "Fetched 2026-09-03 with tools/extract_hyginus.py. Place-name hyperlinks and ToposText's section marks",
    "stripped; fable numbers kept as [N]. [0.2] and [p.N] are the preface (theogony). Numbering follows the",
    "manuscript tradition and has gaps (e.g. 44-46).",
    "",
]
count = 0
skipped = []
for fid, seg in zip(parts[1::2], parts[2::2]):
    text = clean(seg)
    if not text:
        skipped.append(fid)
        continue
    text = re.sub(r"^§\s*\S+\s*", "", text)               # "§ 57" 표시 제거
    whole = fid.split(".")[0]
    text = re.sub(rf"^{re.escape(whole)}\s+", "", text)  # "57 BELLEROPHON:" 의 앞 번호는 [57] 로 대신한다
    lines.append(f"[{fid}] {text}")
    lines.append("")
    count += 1

OUT.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
fables = sum(1 for fid in parts[1::2] if re.fullmatch(r"\d+", fid))
print(f"{count} 단락(번호 있는 우화 {fables}) → {OUT} ({OUT.stat().st_size:,} bytes); 빈 단락 {len(skipped)}: {skipped[:10]}")
