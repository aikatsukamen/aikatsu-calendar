# aikatsu-calendar — iCalendar(.ics) 配信 + 購読UI

`aikatsu-info/aikatsu-calendar` に提案するための一式です。
リポジトリ（`main` 相当・378件）に**実際に適用して動作確認済み**の状態が入っています。

## 中身

```
HANDOFF.md                  ← 先方の Claude にそのまま渡す実装指示書
data-format.md              ← data/items.json の形式調査結果
aikatsu-calendar-ics.patch  ← 差分パッチ（生成物の calendar/*.ics は除外）
integrated/                 ← 適用済みリポジトリ一式（そのまま差し替え可能）
```

## integrated/ での変更点

| ファイル                          | 変更                                                                       |
| --------------------------------- | -------------------------------------------------------------------------- |
| `aikatsu_calendar.html`           | +288行（追加のみ。既存コードの整形なし）。CSS／購読ボタン／モーダル／JS    |
| `tools/build_ics.py`              | 追加。json → ics 変換（標準ライブラリのみ）                                |
| `tools/check_sync.py`             | 追加。HTML内 `ITEMS` と `items.json` の整合チェック                        |
| `tools/apply_subscribe_ui.py`     | 追加。購読UIを本体HTMLに差し込む（冪等）                                   |
| `tools/extract_snippet.py`        | 追加。デモから貼り付け用スニペットを生成                                   |
| `web/subscribe-demo.html`         | 追加。購読UIの編集元・単体デモ                                             |
| `web/subscribe-snippet.html`      | 追加。貼り付け用に切り出したもの                                           |
| `calendar/*.ics` + `feeds.json`   | 追加。生成物9本                                                            |
| `.github/workflows/build-ics.yml` | 追加。データ更新時に自動生成＋コミット（定期実行なし）                     |
| `README.md` / `CLAUDE.md`         | 購読URL一覧、運用上の注意（UID不変・生成物は手編集禁止）、周年の表現を追記 |
| `robots.txt`                      | `Disallow: /web/` を追加                                                   |

## 周年（anniversary）の扱い

`{N}周年` は iCalendar の `SUMMARY` が静的なため繰り返しでは出し分けられないので、
**タイトルから「N周年」を外し、`DTSTART` を放送/配信開始日とする `RRULE:FREQ=YEARLY` の1件**にしている。

- `🎉 アイカツ！ 放送開始記念日` / `DTSTART: 2012-10-08` / `RRULE:FREQ=YEARLY`
- 説明文には「2012年10月8日に放送が始まった…」という絶対年が残るので、何周年かは読み手が数えられる
- 誕生日と同じ形になり、定期再生成も不要（ワークフローに `schedule` は入れていない）
- サイト本体の `resolveForDate()` は従来どおり `{N}` を解決するので、表示は変わらない

## 適用の仕方（先方の選択肢）

1. `integrated/` をそのまま使う
2. `aikatsu-calendar-ics.patch` を当てて `python3 tools/build_ics.py --input data/items.json --outdir calendar`
3. `HANDOFF.md` を読んで自分で入れ直す（`tools/apply_subscribe_ui.py` が使える）

## 確認済みの項目

- Chromium(headless) でライト／ダーク、PC(1000px)／モバイル(390px) 表示
- モーダルの開閉・Esc・背景クリック・フィード切り替え・生成URL・コピー
- JSエラーなし／要素IDの重複なし／HTMLのタグ対応／3つの `<script>` の構文
- 既存機能（カレンダー・トピックスのタブ切り替え）に影響なし
- `.ics` 9本のパース、UID重複なし、全行75オクテット以下、繰り返しの展開

## 生成結果（378件のデータから）

| フィード            | 元データ | VEVENT |
| ------------------- | -------- | ------ |
| aikatsu-all         | 378      | 352    |
| aikatsu-nobirthday  | 304      | 278    |
| aikatsu-goods       | 187      | 177    |
| aikatsu-event       | 81       | 70     |
| aikatsu-birthday    | 67       | 67     |
| aikatsu-anniversary | 7        | 7      |
| aikatsu-game        | 17       | 16     |
| aikatsu-stream      | 11       | 10     |
| aikatsu-anime       | 8        | 5      |

差は日付未定26件をスキップしているぶん。誕生日・周年は繰り返し1件ずつなので元データと同数。
