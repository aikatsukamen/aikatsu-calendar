#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aikatsu_calendar.html に購読UI（CSS / ボタン / モーダル / JS）を差し込む。

    python3 tools/apply_subscribe_ui.py --html aikatsu_calendar.html

- web/subscribe-demo.html のマーカー間を切り出して使うので、デモとズレない。
- 既に適用済み（id="subscribeBtn" がある）なら何もしない（冪等）。
- 既存コードの整形・並べ替えは一切しない。追加のみ。

aikatsu_calendar.html は <html>/<head>/<body> を持たない素のフラグメント形式なので、
挿入位置は「</style> の直後」「.tabs-row の閉じタグ直前」「.page の閉じタグ直後」「ファイル末尾」。
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(HERE, "web", "subscribe-demo.html")

# 挿入位置のアンカー（本体HTML内で一意であること）
ANCHOR_CSS = '</style>\n\n<div class="today-bar">'
ANCHOR_TABS = '''      <button class="tab-btn" id="tab-topics-btn" role="tab" aria-selected="false" aria-controls="panel-topics">トピックス</button>
    </div>
  </div>
'''
ANCHOR_PAGE_END = '''  <div class="site-copyright">© 2026 AIKATSU! CALENDAR</div>
</div>
'''


def block(src, name):
    m = re.search(
        r"<!--\s*SUBSCRIBE:%s:START\s*-->\n(.*?)\n\s*<!--\s*SUBSCRIBE:%s:END\s*-->" % (name, name),
        src, re.S)
    if not m:
        raise SystemExit("マーカーが見つかりません: SUBSCRIBE:%s" % name)
    return m.group(1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="aikatsu_calendar.html")
    ap.add_argument("--demo", default=DEMO)
    opts = ap.parse_args(argv)

    demo = open(opts.demo, encoding="utf-8").read()
    html = open(opts.html, encoding="utf-8").read()

    if 'id="subscribeBtn"' in html:
        print("既に適用済みのため何もしません: " + opts.html)
        return 0

    css = block(demo, "CSS")
    btn = block(demo, "HTML")
    modal = block(demo, "MODAL")
    js = block(demo, "JS")

    for name, anchor in (("CSS", ANCHOR_CSS), ("TABS", ANCHOR_TABS), ("PAGE", ANCHOR_PAGE_END)):
        if html.count(anchor) != 1:
            raise SystemExit("アンカーが一意ではありません(%s): %d件" % (name, html.count(anchor)))

    # 1) CSS: 既存 <style> の直後
    html = html.replace(ANCHOR_CSS, '</style>\n\n' + css + '\n\n<div class="today-bar">')

    # 2) 購読ボタン: .tabs-row の中、.tabs の直後
    # デモ側の [HTML] ブロックは既に4スペース字下げ済みなのでそのまま入れる
    tabs_new = ANCHOR_TABS.replace("    </div>\n  </div>\n",
                                   "    </div>\n\n" + btn + "\n  </div>\n")
    html = html.replace(ANCHOR_TABS, tabs_new)

    # 3) モーダル: .page を閉じた直後
    html = html.replace(ANCHOR_PAGE_END, ANCHOR_PAGE_END + "\n" + modal + "\n")

    # 4) JS: ファイル末尾
    if not html.endswith("\n"):
        html += "\n"
    html += "\n" + js + "\n"

    open(opts.html, "w", encoding="utf-8", newline="").write(html)
    print("適用しました: " + opts.html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
