#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aikatsu_calendar.html に埋め込まれた ITEMS と data/items.json の整合チェック。

CLAUDE.md にある通り、この2つは自動同期されない複製なので、
.ics を items.json から生成する場合、items.json 側の更新漏れが
そのままカレンダー購読者への情報漏れになる。CI で先に落とすためのスクリプト。

    python3 tools/check_sync.py --html aikatsu_calendar.html --json data/items.json

差分があれば終了コード 1。
"""

import argparse
import json
import re
import sys

ID_RE = re.compile(r'(?:^|[{,\s])id\s*:\s*"([^"]+)"')


def ids_from_html(path):
    src = open(path, encoding="utf-8").read()
    i = src.find("// ITEMS:START")
    j = src.find("// ITEMS:END")
    if i < 0 or j < 0:
        raise SystemExit("ITEMS:START / ITEMS:END が見つかりません: " + path)
    return ID_RE.findall(src[i:j])


def ids_from_json(path):
    return [it["id"] for it in json.load(open(path, encoding="utf-8"))]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="aikatsu_calendar.html")
    ap.add_argument("--json", default="data/items.json")
    opts = ap.parse_args(argv)

    html_ids = ids_from_html(opts.html)
    json_ids = ids_from_json(opts.json)

    ok = True
    if len(html_ids) != len(json_ids):
        print("件数不一致: html=%d json=%d" % (len(html_ids), len(json_ids)))
        ok = False

    only_html = [i for i in html_ids if i not in set(json_ids)]
    only_json = [i for i in json_ids if i not in set(html_ids)]
    if only_html:
        print("html にのみ存在するID: " + ", ".join(only_html))
        ok = False
    if only_json:
        print("json にのみ存在するID: " + ", ".join(only_json))
        ok = False

    dup_html = [i for i in set(html_ids) if html_ids.count(i) > 1]
    dup_json = [i for i in set(json_ids) if json_ids.count(i) > 1]
    if dup_html:
        print("html 内で重複しているID: " + ", ".join(sorted(dup_html)))
        ok = False
    if dup_json:
        print("json 内で重複しているID: " + ", ".join(sorted(dup_json)))
        ok = False

    if ok:
        print("OK: %d件が一致" % len(json_ids))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
