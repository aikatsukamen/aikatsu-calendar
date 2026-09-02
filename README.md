# aikatsu-calendar — iCalendar(.ics) 配信 + 購読UI

`aikatsu-info/aikatsu-calendar` に提案するための一式です。
本家に .ics 配信と購読UIを追加し、実際に適用して動作確認まで済ませた状態が `docs/` に入っています。

## 構成

```
HANDOFF.md                  ← 先方の Claude に渡す実装指示書
data-format.md              ← data/items.json の形式調査結果
aikatsu-calendar-ics.patch  ← 差分パッチ（生成物の calendar/*.ics は除外）
docs/                       ← 適用済みの本体一式。本家のリポジトリ直下に相当する
```

`docs/` を GitHub Pages の配信ルートにしているため、
このリポジトリでの公開URLは `https://aikatsukamen.github.io/aikatsu-calendar/…` になります。
本家はリポジトリ直下から配信しているので、`docs/` の中身をそのままリポジトリ直下に置けば同じ構成です。

## 変更点（`docs/` の中身）

| ファイル | 変更 |
|---|---|
| `aikatsu_calendar.html` | +292行（**追加のみ**。既存コードの整形・並べ替えなし）。CSS／購読ボタン／モーダル／JS |
| `tools/build_ics.py` | 追加。`data/items.json` → `.ics` 変換（Python標準ライブラリのみ） |
| `tools/check_sync.py` | 追加。HTML内 `ITEMS` と `data/items.json` の整合チェック |
| `tools/apply_subscribe_ui.py` | 追加。購読UIを本体HTMLに差し込む（冪等） |
| `tools/extract_snippet.py` | 追加。デモから貼り付け用スニペットを生成 |
| `web/subscribe-demo.html` | 追加。購読UIの編集元・単体デモ |
| `web/subscribe-snippet.html` | 追加。貼り付け用に切り出したもの |
| `calendar/*.ics` + `feeds.json` | 追加。生成物9本 |
| `.github/workflows/build-ics.yml` | 追加。データ更新時に自動生成＋コミット（定期実行なし） |
| `README.md` / `CLAUDE.md` | 購読URL、運用上の注意、周年の表現、ドメインを埋め込まない方針を追記 |
| `robots.txt` | `Disallow: /web/` を追加 |

`data/items.json` と `aikatsu_calendar.html` の `ITEMS` には手を入れていません。

## 各カレンダーへの追加リンクの形式

| 追加先 | 渡すURL |
|---|---|
| Google カレンダー | `https://calendar.google.com/calendar/render?cid=` + URLエンコードした **`webcal://`** のURL |
| iPhone・iPad・Mac | `webcal://` のURL |
| Outlook.com | `https://outlook.live.com/calendar/0/addfromweb?url=` + URLエンコードした `https://` のURL |
| 手動（コピー欄） | `https://` のURL |

Google の `cid` に `https://` のURLを渡すと、カレンダーIDとして解釈されて
「カレンダーを追加できません。URL を確認してください。」で弾かれることがあるため `webcal://` を渡しています。

## 配信先ドメインを埋め込まない

購読URLはページ自身のURLから解決するので、コードにドメインは書かれていません。

- 購読UI: `#subModal` の `data-feed-base`（既定 `calendar/`）を `new URL(..., location.href)` で解決。
  本家・このリポジトリ・独自ドメイン・ローカルサーバのいずれでもそのまま正しい先を指します。
- `build_ics.py`: `--base-url` / `--site-url` に既定値なし。省略すれば `SOURCE` を出力せず
  `feeds.json` のURLも相対になります。ワークフローがリポジトリ情報から組み立てて渡します。
- 例外は `--uid-domain` の既定値のみ。これは配信先ではなく**識別子の名前空間**で、
  実在する必要がなく、配信先が変わっても変更しません（変えると購読者の予定が壊れます）。

## 周年（anniversary）の扱い

`{N}周年` は iCalendar の `SUMMARY` が静的なため繰り返しでは出し分けられないので、
タイトルから「N周年」を外し、`DTSTART` を放送/配信開始日とする `RRULE:FREQ=YEARLY` の1件にしています。

- `🎉 アイカツ！ 放送開始記念日` / `DTSTART: 2012-10-08` / `RRULE:FREQ=YEARLY`
- 説明文に「2012年10月8日に放送が始まった…」という絶対年が残るので、何周年かは読み手が数えられる
- 誕生日と同じ形になり、定期再生成も不要
- サイト本体の `resolveForDate()` は従来どおり `{N}` を解決するので、表示は変わらない

## 生成結果（378件のデータから）

| フィード | 元データ | VEVENT |
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

差は日付未定26件をスキップしているぶん。誕生日・周年は繰り返し1件ずつなので元データと同数です。
