# data/items.json 形式の調査結果

調査日: 2026-09-02 / 対象コミット時点の `main`（378件）

## 全体構造

`data/items.json` はオブジェクトの**配列**（トップレベルにメタ情報なし）。
同じ内容が `aikatsu_calendar.html` の `// ITEMS:START` 〜 `// ITEMS:END` にも
JSオブジェクトリテラル（キー無引用符）として重複して埋め込まれている。
CLAUDE.md に明記の通り **両者は自動同期されない**。

## フィールド

| キー | 出現数 | 型 | 内容 |
|---|---|---|---|
| `id` | 378 | string | `YYYYMMDD-NN`（追加日-連番）。誕生日は `bd01`、周年は `anv01` 形式 |
| `cat` | 378 | string | `goods`(187) / `event`(81) / `birthday`(67) / `game`(17) / `stream`(11) / `anime`(8) / `anniversary`(7) |
| `subcat` | 78 | string | 現状 `gashapon` のみ |
| `published` | 378 | string\|null | 情報の公開日 |
| `addedAt` | 378 | string | カレンダーへの追加日 |
| `eventDate` | 378 | string\|null | 予定日。**null が100件** |
| `recur` | 96 | string\|null | `MM-DD`。毎年繰り返す項目（誕生日67・周年7、残りは値 null） |
| `eventLabel` | 378 | string | 「9月1日 公開」などの表示用文字列 |
| `title` | 378 | string | 見出し |
| `detail` | 378 | string | 本文 |
| `src` | 378 | string | 情報源名 |
| `url` | 378 | string | 情報源URL |
| `reservation` | 49 | true | 予約系のみ付与 |
| `foundingYear` | 7 | number | `anniversary` のみ。周年計算の起点 |
| `startWord` | 7 | string | `anniversary` のみ。「放送」等 |

※ CLAUDE.md のデータ形式説明には `recur` / `foundingYear` / `startWord` の記載がない。
実装は `aikatsu_calendar.html` の `resolveForDate()` / `itemsByRecur()` にある。

## 日付の3パターン（.ics 化で分岐が必要なところ）

1. **単発**（`eventDate` あり、278件相当）
   → 終日イベント1件。

2. **毎年繰り返し**（`eventDate: null` かつ `recur: "MM-DD"`、74件）
   - `cat: "birthday"`（67件）: タイトル固定 → `RRULE:FREQ=YEARLY` で表現できる。
   - `cat: "anniversary"`（7件）: `title` / `detail` / `eventLabel` に `{N}` プレースホルダがあり、
     `N = 表示年 - foundingYear`。`N === 0` の年は `{N}周年` を `<startWord>開始日` に置換する
     （本体の `resolveForDate()` と同じ規則）。
     年ごとに文言が変わるため、`{N}` を保ったまま RRULE で表現することはできない
     （iCalendar の `SUMMARY` は静的なため）。

     `build_ics.py` は **タイトルから「N周年」を外し、`RRULE:FREQ=YEARLY` の1件**にしている。
     `SUMMARY` は `<startWord>開始記念日`、`DTSTART` は `foundingYear` の当日（＝放送/配信開始日そのもの）。
     `detail` は「今年で{N}周年になります。」だけを落とすので、
     「2012年10月8日に放送が始まった…」という絶対年が残り、何周年かは読み手が数えられる。
     年ごとに展開する案は、展開窓の維持（データ更新が無くても定期再生成が要る）、
     窓の外の年に予定が無いこと、UIDが年ごとに増えることから採らなかった。
     詳細は `HANDOFF.md` の「周年（anniversary）の表現」を参照。

3. **日付未定**（`eventDate: null` かつ `recur` なし、26件）
   例:「凛堂たいむ お誕生日イベントのグッズ情報を解禁」など、告知のみで日付が確定していないもの。
   本体サイトでは「日付未定」ボックス（`tbdBox`）に出している。
   → カレンダーには置き場所がないため、`build_ics.py` では**既定でスキップ**。
   `--undated=published` で公開日に置くこともできる（要判断）。

## 期間もの（開始／終了）の扱い

CLAUDE.md の規約通り、POP UP SHOP の開催期間や予約期間は
「〜開始」「〜終了」の **2件のエントリ** に分けて登録されている。
したがって .ics 側でも自動的に「開始日の終日イベント」「終了日の終日イベント」の2件になり、
複数日にまたがる1イベントにはならない。
これは仕様として妥当（本体サイトの見え方と一致する）。
将来まとめたい場合は、ペアを対応付けるためのフィールド（例 `pairId`）が
データ側に必要になる。

## 生成結果（2026-09-02 時点のデータ）

| フィード | 元データ件数 | VEVENT数 |
|---|---|---|
| aikatsu-all | 378 | 352 |
| aikatsu-nobirthday | 304 | 278 |
| aikatsu-goods | 187 | 177 |
| aikatsu-event | 81 | 70 |
| aikatsu-birthday | 67 | 67 |
| aikatsu-anniversary | 7 | 7 |
| aikatsu-game | 17 | 16 |
| aikatsu-stream | 11 | 10 |
| aikatsu-anime | 8 | 5 |

件数が減っているのは日付未定のスキップ分。
誕生日・周年は `RRULE:FREQ=YEARLY` の1件ずつなので、元データと同数になる。
