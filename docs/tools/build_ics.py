#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/items.json -> iCalendar (.ics) 変換スクリプト

使い方:
    python3 tools/build_ics.py --input data/items.json --outdir calendar

出力（既定）:
    calendar/aikatsu-all.ics          全カテゴリ
    calendar/aikatsu-nobirthday.ics   誕生日・周年を除く全カテゴリ
    calendar/aikatsu-goods.ics        グッズ
    calendar/aikatsu-event.ics        イベント
    calendar/aikatsu-anime.ics        アニメ・映像
    calendar/aikatsu-game.ics         アイカツ！アンコール
    calendar/aikatsu-stream.ics       配信
    calendar/aikatsu-birthday.ics     誕生日
    calendar/aikatsu-anniversary.ics  周年
    calendar/feeds.json               購読UI用のフィード一覧（任意）

標準ライブラリのみで動作する（外部依存なし）。
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

# ---------------------------------------------------------------- 設定

PRODID = "-//aikatsu-info//aikatsu-calendar//JA"

# UID の右側に使う識別子。**URLではなく名前空間**なので、
# 配信先ドメインが変わっても（フォーク・独自ドメイン）絶対に変えない。
# 変えると購読者のカレンダー上で予定が重複または消失する。
UID_DOMAIN_DEFAULT = "aikatsu-calendar.aikatsu-info.github.io"

# aikatsu_calendar.html の var CATS と揃えること
CATS = {
    "event":       {"label": "イベント",             "emoji": ""},
    "goods":       {"label": "グッズ",               "emoji": ""},
    "anime":       {"label": "アニメ・映像",         "emoji": ""},
    "game":        {"label": "アイカツ！アンコール", "emoji": ""},
    "stream":      {"label": "配信",                 "emoji": ""},
    "birthday":    {"label": "誕生日",               "emoji": "🎂"},
    "anniversary": {"label": "周年",                 "emoji": "🎉"},
}
SUBCAT_LABELS = {"gashapon": "ガシャポン"}

# 出力するフィードの定義: (ファイル名, 表示名, 説明, フィルタ関数)
FEEDS = [
    ("aikatsu-all",         "アイカツ！情報カレンダー",
     "アイカツ！シリーズのイベント・グッズ・配信・誕生日・周年をまとめた非公式カレンダー",
     lambda it: True),
    ("aikatsu-nobirthday",  "アイカツ！情報カレンダー（誕生日・周年なし）",
     "誕生日・周年を除いた、イベント／グッズ／配信などの予定のみ",
     lambda it: it.get("cat") not in ("birthday", "anniversary")),
    ("aikatsu-goods",       "アイカツ！グッズ",        "グッズの発売日・予約開始／締切",
     lambda it: it.get("cat") == "goods"),
    ("aikatsu-event",       "アイカツ！イベント",      "ライブ・上映会・POP UP SHOP などのイベント",
     lambda it: it.get("cat") == "event"),
    ("aikatsu-anime",       "アイカツ！アニメ・映像",  "アニメ・映像関連の予定",
     lambda it: it.get("cat") == "anime"),
    ("aikatsu-game",        "アイカツ！アンコール",    "『アイカツ！アンコール』関連の予定",
     lambda it: it.get("cat") == "game"),
    ("aikatsu-stream",      "アイカツ！配信",          "配信番組・一挙配信などの予定",
     lambda it: it.get("cat") == "stream"),
    ("aikatsu-birthday",    "アイカツ！誕生日",        "キャラクターの誕生日（毎年繰り返し）",
     lambda it: it.get("cat") == "birthday"),
    ("aikatsu-anniversary", "アイカツ！周年",          "シリーズの周年記念日",
     lambda it: it.get("cat") == "anniversary"),
]

# 誕生日の RRULE 用の基準年。
# 毎回の生成で値が変わらないよう固定値にしている（差分ノイズを避けるため）。
BIRTHDAY_BASE_YEAR = 2013

# 周年は foundingYear を初回インスタンスの年に使う。
# 万一 foundingYear が無いデータが来たときのフォールバック。
ANNIVERSARY_FALLBACK_YEAR = 2013

# ---------------------------------------------------------------- ICS プリミティブ

ESCAPE_RE = re.compile(r"([\\;,])")


def esc(text):
    """TEXT 値のエスケープ（RFC 5545 3.3.11）"""
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    s = s.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return s


def fold(line):
    """
    75オクテットで行折り返し（RFC 5545 3.1）。
    UTF-8 のマルチバイト文字の途中で切らないようバイト単位で処理する。
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out = []
    start = 0
    limit = 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        # UTF-8 の継続バイト (10xxxxxx) の途中で切らない
        while end > start and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        out.append(raw[start:end].decode("utf-8"))
        start = end
        limit = 74  # 2行目以降は先頭の空白1文字ぶん減らす
    return "\r\n ".join(out[:1] + out[1:])


def prop(name, value, params=None):
    p = ""
    if params:
        p = "".join(";%s=%s" % (k, v) for k, v in params)
    return fold("%s%s:%s" % (name, p, value))


def date_compact(d):
    return d.strftime("%Y%m%d")


def parse_iso_date(s):
    if not s:
        return None
    try:
        return dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, TypeError, IndexError):
        return None


# ---------------------------------------------------------------- データ整形

def resolve_anniversary(item):
    """
    周年を「毎年繰り返す1件のイベント」として表現するために {N} を落とす。

    iCalendar の SUMMARY は静的なので、RRULE のまま「14周年」と年ごとに
    出し分けることは仕様上できない。そこでタイトルからは「N周年」を外し、
    「<startWord>開始記念日」にする。何周年かは detail に残る絶対年
    （「2012年10月8日に放送が始まった…」）から読み手が数えられる。
    サイト本体では従来どおり resolveForDate() が {N} を解決して表示する。
    """
    start_word = item.get("startWord") or "放送"
    out = dict(item)
    out["title"] = re.sub(r"\{N\}周年", start_word + "開始記念日", item.get("title", "") or "")
    out["eventLabel"] = re.sub(r"（\{N\}周年）", "（毎年）", item.get("eventLabel", "") or "")
    out["detail"] = re.sub(r"今年で\{N\}周年になります。", "", item.get("detail", "") or "").strip()
    # 取りこぼした {N} が残らないようにする
    for k in ("title", "detail", "eventLabel"):
        if out.get(k):
            out[k] = out[k].replace("{N}", "")
    return out


def summary_for(item):
    cat = CATS.get(item.get("cat"), {})
    emoji = cat.get("emoji") or ""
    title = item.get("title") or "(無題)"
    return (emoji + " " + title).strip() if emoji else title


def description_for(item, site_url):
    lines = []
    if item.get("detail"):
        lines.append(item["detail"])
    meta = []
    cat = CATS.get(item.get("cat"), {}).get("label")
    sub = SUBCAT_LABELS.get(item.get("subcat"))
    if cat:
        meta.append("区分: " + cat + (("／" + sub) if sub else ""))
    if item.get("eventLabel"):
        meta.append("日程表記: " + item["eventLabel"])
    if item.get("published"):
        meta.append("情報公開日: " + item["published"])
    if item.get("src"):
        meta.append("情報源: " + item["src"])
    if meta:
        lines.append("\n".join(meta))
    if item.get("url"):
        lines.append(item["url"])
    footer = "― アイカツ！情報カレンダー（非公式ファンメイド）"
    if site_url:
        footer += "\n" + site_url
    lines.append(footer)
    return "\n\n".join(lines)


def categories_for(item):
    vals = []
    label = CATS.get(item.get("cat"), {}).get("label")
    if label:
        vals.append(label)
    sub = SUBCAT_LABELS.get(item.get("subcat"))
    if sub:
        vals.append(sub)
    if item.get("reservation"):
        vals.append("予約")
    return vals


def vevent(uid, start_date, item, dtstamp, site_url, rrule=None):
    end_date = start_date + dt.timedelta(days=1)
    out = ["BEGIN:VEVENT"]
    out.append(prop("UID", esc(uid)))
    out.append(prop("DTSTAMP", dtstamp))
    out.append(prop("DTSTART", date_compact(start_date), [("VALUE", "DATE")]))
    out.append(prop("DTEND", date_compact(end_date), [("VALUE", "DATE")]))
    if rrule:
        out.append(prop("RRULE", rrule))
    out.append(prop("SUMMARY", esc(summary_for(item))))
    out.append(prop("DESCRIPTION", esc(description_for(item, site_url))))
    if item.get("url"):
        out.append(prop("URL", item["url"]))
    cats = categories_for(item)
    if cats:
        out.append(prop("CATEGORIES", ",".join(esc(c) for c in cats)))
    added = parse_iso_date(item.get("addedAt"))
    if added:
        out.append(prop("LAST-MODIFIED", date_compact(added) + "T000000Z"))
    out.append(prop("TRANSP", "TRANSPARENT"))   # 予定を「空き時間」扱いにする
    out.append(prop("SEQUENCE", "0"))
    out.append("END:VEVENT")
    return out


def build_events(items, opts, dtstamp):
    """items -> VEVENT 行のリスト"""
    lines = []
    for item in items:
        cat = item.get("cat")
        recur = item.get("recur")
        event_date = parse_iso_date(item.get("eventDate"))

        if event_date:
            # 通常の単発予定
            lines += vevent("%s@%s" % (item["id"], opts.uid_domain),
                            event_date, item, dtstamp, opts.site_url)

        elif recur and cat == "anniversary":
            # 周年: 放送/配信開始日を初回インスタンスとする毎年繰り返し。
            # タイトルから「N周年」を外している（resolve_anniversary() を参照）。
            mm, dd = int(recur[0:2]), int(recur[3:5])
            base_year = int(item.get("foundingYear") or ANNIVERSARY_FALLBACK_YEAR)
            try:
                d = dt.date(base_year, mm, dd)
            except ValueError:
                continue
            lines += vevent("%s@%s" % (item["id"], opts.uid_domain),
                            d, resolve_anniversary(item), dtstamp, opts.site_url,
                            rrule="FREQ=YEARLY")

        elif recur:
            # 誕生日など: 毎年繰り返し
            mm, dd = int(recur[0:2]), int(recur[3:5])
            base_year = BIRTHDAY_BASE_YEAR
            if (mm, dd) == (2, 29):
                while base_year % 4 != 0:
                    base_year += 1
            try:
                d = dt.date(base_year, mm, dd)
            except ValueError:
                continue
            lines += vevent("%s@%s" % (item["id"], opts.uid_domain),
                            d, item, dtstamp, opts.site_url,
                            rrule="FREQ=YEARLY")

        else:
            # eventDate も recur も無い（日付未定の告知）
            if opts.undated == "published":
                d = parse_iso_date(item.get("published")) or parse_iso_date(item.get("addedAt"))
                if d:
                    lines += vevent("%s@%s" % (item["id"], opts.uid_domain),
                                    d, item, dtstamp, opts.site_url)
            # opts.undated == "skip" の場合は何も出さない
    return lines


def build_calendar(items, name, desc, opts, dtstamp, feed_url=None):
    lines = [
        "BEGIN:VCALENDAR",
        prop("VERSION", "2.0"),
        prop("PRODID", PRODID),
        prop("CALSCALE", "GREGORIAN"),
        prop("METHOD", "PUBLISH"),
        prop("X-WR-CALNAME", esc(name)),
        prop("X-WR-CALDESC", esc(desc)),
        prop("X-WR-TIMEZONE", "Asia/Tokyo"),
        prop("REFRESH-INTERVAL", "PT6H", [("VALUE", "DURATION")]),
        prop("X-PUBLISHED-TTL", "PT6H"),
        prop("SOURCE", feed_url, [("VALUE", "URI")]) if feed_url else None,
    ]
    lines = [l for l in lines if l]
    lines += build_events(items, opts, dtstamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- main

def default_dtstamp(items):
    """
    DTSTAMP はデータ内の最新日付から決める。
    実行時刻を使うと毎回全イベントの差分が出てコミットがノイズになるため。
    """
    latest = None
    for it in items:
        for key in ("addedAt", "published"):   # eventDate は未来日なので使わない
            d = parse_iso_date(it.get(key))
            if d and (latest is None or d > latest):
                latest = d
    if latest is None:
        latest = dt.date.today()
    return latest.strftime("%Y%m%dT000000Z")


def main(argv=None):
    ap = argparse.ArgumentParser(description="data/items.json から .ics を生成する")
    ap.add_argument("--input", default="data/items.json")
    ap.add_argument("--outdir", default="calendar")
    ap.add_argument("--base-url", default=None,
                    help="出力先ディレクトリの公開URL（例 https://<owner>.github.io/<repo>/calendar）。"
                         "省略すると feeds.json のURLは相対パスになり、SOURCE は出力しない")
    ap.add_argument("--site-url", default=None,
                    help="DESCRIPTION 末尾に入れるサイトURL。省略すると入れない")
    ap.add_argument("--uid-domain", default=UID_DOMAIN_DEFAULT,
                    help="UID の右側に使う名前空間。配信先が変わっても変更しないこと")
    ap.add_argument("--undated", choices=["skip", "published"], default="skip",
                    help="eventDate も recur も無い項目の扱い（既定: skip）")
    ap.add_argument("--today", default=None, help="基準日 YYYY-MM-DD（テスト用）")
    opts = ap.parse_args(argv)

    opts.today = parse_iso_date(opts.today) or dt.date.today()
    if opts.base_url:
        opts.base_url = opts.base_url.rstrip("/")

    with open(opts.input, encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        print("items.json は配列であるべきです", file=sys.stderr)
        return 1

    dtstamp = default_dtstamp(items)
    os.makedirs(opts.outdir, exist_ok=True)

    feeds_meta = []
    for slug, name, desc, filt in FEEDS:
        subset = [it for it in items if filt(it)]
        feed_url = ("%s/%s.ics" % (opts.base_url, slug)) if opts.base_url else None
        text = build_calendar(subset, name, desc, opts, dtstamp, feed_url)
        path = os.path.join(opts.outdir, slug + ".ics")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        n_events = text.count("BEGIN:VEVENT")
        feeds_meta.append({
            "slug": slug, "name": name, "description": desc,
            "file": slug + ".ics",
            "url": feed_url or (slug + ".ics"),   # base-url 未指定なら feeds.json からの相対
            "items": len(subset), "events": n_events,
        })
        print("%-28s items=%-4d events=%-4d %s" % (slug, len(subset), n_events, path))

    with open(os.path.join(opts.outdir, "feeds.json"), "w", encoding="utf-8") as f:
        json.dump({"generated": dtstamp, "feeds": feeds_meta}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
