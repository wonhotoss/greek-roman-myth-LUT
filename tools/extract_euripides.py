"""Perseus Digital Library 의 TEI XML (에우리피데스, Coleridge 역) -> sources/euripides-<play>-coleridge.txt

    git clone --depth 1 --filter=blob:none --sparse https://github.com/PerseusDL/canonical-greekLit perseus
    git -C perseus sparse-checkout set data/tlg0006/tlg003          # tlg003 = 메데이아
    python tools/extract_euripides.py perseus/data/tlg0006/tlg003/tlg0006.tlg003.perseus-eng2.xml sources/euripides-medea-coleridge.txt

행 번호가 <l n="670"> 에 있다. 그 번호를 [670] 으로 행 앞에 남기고, 화자는 <speaker> 를 대문자 줄로 둔다.
아폴로도로스의 [2.5.1]·히기누스의 [57] 과 같은 방식이어서 `sources = ["euripides.medea 663-758"]` 를 grep 으로 찾는다.
번역(Coleridge 1891/1906)은 공개 도메인이고, Perseus 의 TEI 판은 CC BY-SA 4.0 이다 — 머리말에 적는다.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
NS = {"t": "http://www.tei-c.org/ns/1.0"}


def text_of(el):
    s = "".join(el.itertext())
    return re.sub(r"\s+", " ", s).strip()


root = ET.parse(SRC).getroot()
# 역자 주(<note>)는 본문이 아니다 — 빼지 않으면 "i.e., ..." 가 대사 사이에 섞인다.
for parent in root.iter():
    for note in [c for c in list(parent) if c.tag.split("}")[-1] == "note"]:
        tail = note.tail or ""
        prev = list(parent).index(note)
        if prev > 0:
            sib = list(parent)[prev - 1]
            sib.tail = (sib.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail
        parent.remove(note)
title = root.find(".//t:titleStmt/t:title", NS)
author = root.find(".//t:titleStmt/t:author", NS)
translator = root.find(".//t:titleStmt/t:editor[@role='translator']", NS)
desc = root.find(".//t:sourceDesc//t:biblStruct", NS)
licence = root.find(".//t:availability//t:licence", NS)

lines = [
    f"{text_of(author)} — {text_of(title)}",
    f"translated by {text_of(translator)}. " + (text_of(desc) if desc is not None else ""),
    "Source: Perseus Digital Library (PerseusDL/canonical-greekLit, tlg0006.tlg003.perseus-eng2). "
    + (f"TEI edition: {text_of(licence)}. " if licence is not None else "")
    + "The translation itself is in the public domain.",
    "Line numbers of the Greek text are kept as [N] at the start of each line.",
    "",
]

body = root.find(".//t:text/t:body", NS)
for el in body.iter():
    tag = el.tag.split("}")[-1]
    if tag == "speaker":
        lines.append("")
        lines.append(text_of(el).upper())
    elif tag == "l":
        n = el.get("n")
        s = text_of(el)
        if s:
            lines.append(f"[{n}] {s}" if n else s)
    elif tag == "stage":
        lines.append(f"({text_of(el)})")
    elif tag == "head":
        lines.append("")
        lines.append("== " + text_of(el))

out = "\n".join(lines).rstrip() + "\n"
OUT.write_text(out, encoding="utf-8")
print(f"{OUT} — {len(out):,} bytes, {sum(1 for l in lines if l.startswith('['))} numbered lines")
