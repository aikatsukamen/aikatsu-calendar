#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web/subscribe-demo.html のマーカー間を抜き出して、
aikatsu_calendar.html に貼り付ける用の web/subscribe-snippet.html を作る。

    python3 tools/extract_snippet.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "web", "subscribe-demo.html")
DST = os.path.join(HERE, "web", "subscribe-snippet.html")

BLOCKS = [
    ("CSS",   "<head> の末尾（既存の <style> の後ろ）に貼る"),
    ("HTML",  "<div class=\"tabs-row\"> の中、<div class=\"tabs\">…</div> の直後に貼る"),
    ("MODAL", "<div class=\"page\"> を閉じた直後（</body> の手前）に貼る"),
    ("JS",    "本体のメイン <script> の後ろ、</body> の直前に貼る"),
]


def extract(src, name):
    m = re.search(
        r"<!--\s*SUBSCRIBE:%s:START\s*-->\n(.*?)\n\s*<!--\s*SUBSCRIBE:%s:END\s*-->" % (name, name),
        src, re.S)
    if not m:
        raise SystemExit("マーカーが見つかりません: SUBSCRIBE:%s" % name)
    return m.group(1)


def main():
    src = open(SRC, encoding="utf-8").read()
    out = ["<!--",
           "  aikatsu_calendar.html への貼り付け用スニペット",
           "  （web/subscribe-demo.html から tools/extract_snippet.py で自動生成）",
           "  FEED_BASE の値と、build_ics.py の FEEDS の内容が一致していることを確認すること。",
           "-->", ""]
    for name, where in BLOCKS:
        out.append("<!-- ===== [%s] %s ===== -->" % (name, where))
        out.append(extract(src, name))
        out.append("")
    open(DST, "w", encoding="utf-8").write("\n".join(out))
    print("wrote " + DST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
