# HANDOFF: iCalendar(.ics) 配信と購読UIの追加

このファイルは、`aikatsu-info/aikatsu-calendar` を開発している Claude に向けた実装指示書です。
`aikatsu-info/aikatsu-calendar` に .ics 配信と購読UIを追加し、**動作確認まで済ませた状態**を
`docs/` に置いています（GitHub Pages の配信ルートにしているため。本家ではリポジトリ直下にあたる）。
以下に出てくるパスはすべて `docs/` 配下のものです。
ファイルをそのまま取り込むこともできますし、下の説明を読んで自分で入れ直しても構いません。

---

## 0. 依頼の要旨

現在 `data/items.json` として持っているカレンダーデータを **iCalendar (.ics) 形式でも出力**し、
GitHub Pages で配信してください。あわせてサイト上に**購読ボタン**を設置してください。

これにより、閲覧者が Google カレンダーや iPhone の標準カレンダーに購読登録でき、
サイトを見に来なくても予定が手元のカレンダーに流れるようになります。

---

## 変更点（`docs/` の中身）

| ファイル | 変更 |
|---|---|
| `aikatsu_calendar.html` | +292行（**追加のみ**。既存コードの整形・並べ替えはしていない）。CSS／購読ボタン／モーダル／JS |
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
| `HANDOFF.md` / `data-format.md` | このファイルと、データ形式の調査メモ |

`data/items.json` と `aikatsu_calendar.html` の `ITEMS` には**手を入れていません**。

---

## 1. 前提として把握しておいてほしいこと

- このリポジトリはビルドプロセスを持たない素の静的サイトで、Pages はリポジトリ直下から配信されている。
  `calendar/aikatsu-all.ics` をコミットすれば
  `https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-all.ics` で公開される。
- `aikatsu_calendar.html` の `ITEMS` と `data/items.json` は**自動同期されない複製**（CLAUDE.md 記載の通り）。
  .ics は `data/items.json` から生成するので、**json 側の更新漏れがそのまま購読者への情報漏れになる**。
  同梱の `tools/check_sync.py` を CI で先に走らせて落とすこと。
- データの日付には3パターンある（詳細は同梱の `data-format.md`）:
  1. `eventDate` あり = 単発
  2. `eventDate: null` + `recur: "MM-DD"` = 毎年繰り返し（誕生日67・周年7）
  3. `eventDate: null` + `recur` なし = **日付未定**（26件）
- `cat: "anniversary"` は `title`/`detail`/`eventLabel` に `{N}` を含み、年ごとに文言が変わる。
  .ics 側では `{N}` を出せないため、タイトルから外して毎年繰り返しにしている
  （後述の「周年（anniversary）の表現」）。サイト本体の `resolveForDate()` の挙動は変えない。

---

## 2. やること

### 2-1. `tools/build_ics.py` を追加する

`tools/build_ics.py` をそのまま配置してください。
Python 3 標準ライブラリのみで動きます。動作確認済み（378件 → 352 VEVENT）。

```
python3 tools/build_ics.py --input data/items.json --outdir calendar
```

`--base-url` / `--site-url` に既定値はありません。**省略すると .ics にドメインは一切入りません**
（`SOURCE` を出力せず、`feeds.json` のURLは相対パス、`DESCRIPTION` 末尾のサイトURLも省略）。
渡した場合だけ絶対URLが入ります。ワークフローはリポジトリ情報から自動で組み立てるので、
フォークでも正しい値になります。

```
python3 tools/build_ics.py --input data/items.json --outdir calendar \
  --base-url https://<owner>.github.io/<repo>/calendar \
  --site-url https://<owner>.github.io/<repo>/
```

`--uid-domain` の既定値だけは固定のドメイン文字列ですが、これは**配信先ではなく識別子の名前空間**です。
実在する必要はなく、配信先が変わっても変更しません（変えると購読者の予定が壊れます）。

このスクリプトの設計上の決定事項（変更する場合はここを意識してください）:

| 項目 | 決定 | 理由 |
|---|---|---|
| イベント種別 | すべて終日（`DTSTART;VALUE=DATE`、`DTEND` は翌日） | データに時刻の情報がない |
| `UID` | `<id>@aikatsu-calendar.aikatsu-info.github.io` | **一度公開したら絶対に変えない**。変えると購読者側で重複または消失が起きる。URLではなく識別子の名前空間なので、フォークでも独自ドメインでも変えない |
| `DTSTAMP` | データ中の最新 `addedAt`/`published` から生成（実行時刻を使わない） | 実行のたびに全行差分が出るのを防ぐ。生成結果が決定的になる |
| 誕生日 | `RRULE:FREQ=YEARLY`（基準年 2013 固定） | ファイルが小さく、将来の年も自動で出る |
| 周年 | `RRULE:FREQ=YEARLY`（`DTSTART` = `foundingYear` の当日）。タイトルは `<startWord>開始記念日` | 下の「周年の表現」を参照 |
| 日付未定26件 | **既定でスキップ** | カレンダー上に置くべき日付が存在しない。`--undated=published` で公開日に置くことも可能 |
| `TRANSP` | `TRANSPARENT` | 購読者の「予定あり」判定を汚さない |
| 更新間隔 | `REFRESH-INTERVAL:PT6H` / `X-PUBLISHED-TTL:PT6H` | クライアントへの再取得ヒント（あくまでヒント） |

出力するフィードは9本（`FEEDS` 定数）:
`aikatsu-all` / `aikatsu-nobirthday` / `aikatsu-goods` / `aikatsu-event` /
`aikatsu-anime` / `aikatsu-game` / `aikatsu-stream` / `aikatsu-birthday` / `aikatsu-anniversary`。
あわせて `calendar/feeds.json`（フィード一覧・件数）も出力します。

#### 周年（anniversary）の表現

`{N}周年` は年ごとに文言が変わりますが、iCalendar の `SUMMARY` は静的なので、
RRULE のまま「14周年」と出し分けることは**仕様上できません**。
そこで **タイトルから「N周年」を外し、誕生日と同じ毎年繰り返しの1イベントにしています。**

- `SUMMARY`: `{N}周年` → `<startWord>開始記念日`（例: `🎉 アイカツ！ 放送開始記念日`）。
  `startWord` は既存フィールドをそのまま使用（`anv07` だけ「配信」なので「配信開始記念日」になる）。
- `DTSTART`: `foundingYear` の当日（例 `2012-10-08`）。放送/配信開始日そのものが初回インスタンス。
- `RRULE:FREQ=YEARLY`。
- `DESCRIPTION`: 元の `detail` から「今年で{N}周年になります。」だけを落とす。
  「2012年10月8日に放送が始まった…」という**絶対年**が残るので、何周年かは読み手が数えられます。
- `eventLabel` は `（{N}周年）` → `（毎年）`（誕生日と同じ表記）。

年ごとに展開する案も検討しましたが、次の理由で採りませんでした:

- 展開窓を維持するために、データ更新が無くても定期的な再生成が必要になる。
- 窓の外の年には予定が存在せず、購読者が先の年を見ると消えている。
- 同じ記念日が年ごとに別UIDの別イベントになり、「この予定だけ非表示にする」といった
  カレンダーアプリ側の操作が効かない。

RRULE 化により `anniversary` は 7件 → 7 VEVENT（展開案なら42）になり、
ワークフローの定期実行も不要です。
サイト本体の表示は従来どおり `resolveForDate()` が `{N}` を解決するので変わりません。

### 2-2. `tools/check_sync.py` を追加する

`aikatsu_calendar.html` の `ITEMS` と `data/items.json` の ID を突き合わせ、
件数・欠落・重複を検出します。差分があれば終了コード 1。

### 2-3. `.github/workflows/build-ics.yml` を追加する

`.github/workflows/build-ics.yml` をそのまま配置してください。`data/items.json` などが push されたら
`check_sync.py` → `build_ics.py` を走らせ、`calendar/` に差分があればコミットします。
`paths` に `calendar/**` を含めていないので自己ループしません。
誕生日・周年はどちらも `RRULE:FREQ=YEARLY` なので、データが変わらない限り再生成は不要です
（定期実行のトリガは入れていません）。

> Actions を増やしたくない場合の代案: データ更新時の手順に
> `python3 tools/build_ics.py --input data/items.json --outdir calendar` を組み込み、
> 同じPRに `calendar/*.ics` を含める。その場合は **CLAUDE.md の更新手順に明記**すること
> （忘れると .ics だけ古いまま配信され続けるので、CI にする方を推奨）。

### 2-4. 購読UIを `aikatsu_calendar.html` に組み込む

**このリポジトリの `aikatsu_calendar.html` は適用済みです。** そのまま差し替えられます。
手で入れ直す場合は `tools/apply_subscribe_ui.py` を使えます（冪等・既存コードの整形はしません）。

```
python3 tools/apply_subscribe_ui.py --html aikatsu_calendar.html --demo web/subscribe-demo.html
```

`aikatsu_calendar.html` は `<html>` / `<head>` / `<body>` を持たない素のフラグメントなので、
挿入位置は次の4か所です（`web/subscribe-snippet.html` に切り出し済み）。

| ブロック | 貼り付け位置 |
|---|---|
| `[CSS]` | 既存 `<style>` の `</style>` 直後（`<div class="today-bar">` の手前） |
| `[HTML]`（購読ボタン） | `<div class="tabs-row">` の中、`<div class="tabs">…</div>` の直後 |
| `[MODAL]` | `.page` の閉じ `</div>`（`site-copyright` の次の行）の直後 |
| `[JS]` | ファイル末尾（既存の2つの `<script>` の後ろ） |

UIの仕様:

- タブ行の右端に「カレンダー購読」ボタン（狭い画面ではアイコンのみになる）。
- 押すとモーダルが開き、**購読する内容を選択**（すべて／誕生日以外／イベント／グッズ／アンコール／誕生日）。
- 追加ボタンは4つ:
  - **Google カレンダー**: `https://calendar.google.com/calendar/render?cid=<encodeURIComponentしたhttps URL>`
    （`/u/0/` は付けない。アカウント選択をユーザーに委ねるため）
  - **iPhone・iPad・Mac**: `webcal://` スキームのリンク
  - **Outlook.com**: `https://outlook.live.com/calendar/0/addfromweb?url=...&name=...`
  - **.ics ダウンロード**（1回きりの取り込み用）
- その下に **readonly のテキストボックス**で購読URLを表示し、横にコピーボタン。
  Googleアカウントを複数使っている人が、追加先アカウントを自分で選べるようにするための導線。
  この意図を説明する注記も入れてあるので消さないでください。
- モーダルは Esc / 背景クリックで閉じる、Tab のフォーカストラップ、`aria-modal` 対応済み。
- `#subscribe` 付きURLで開くと自動でモーダルが開く（告知ポストからの誘導用）。

組み込み時の注意:

- JS の `FEEDS` は `build_ics.py` の `FEEDS` と対応しています。片方だけ変えないこと。
- **購読UIのコードにドメインは一切書かれていません。**
  モーダルの `data-feed-base`（既定 `calendar/`）をページ自身のURL基準で解決するので、
  本家・フォーク・独自ドメイン・ローカルサーバのいずれでもそのまま正しい先を指します。
  `.ics` の置き場所を変えるときは `data-feed-base` の値だけ直してください。
  ここをドメイン決め打ちに戻すと、フォーク先などで 404 のURLを購読させてしまい、
  Googleカレンダーは「カレンダーを追加できません。URL を確認してください。」で弾きます。
- スニペットは本体の CSS 変数（`--accent` / `--surface` / `--line` など）だけを使っているので、
  `:root[data-theme]` によるライト/ダーク切り替えに自動追従します。
  デモ側の `:root` ブロックはコピーしないでください（`apply_subscribe_ui.py` はコピーしません）。
- 購読ボタンのサイズは `.tab-btn`（12px / padding 7px 15px）に合わせ、
  ブレークポイントも本体と同じ `520px` を使っています。狭い画面ではアイコンのみになります。
- **本体の既存コードの整形・リファクタは一切しないでください。** 追加のみ。

### 2-5. 周辺の更新

- `README.md` に購読URLの一覧を追記。
- `CLAUDE.md` に以下を追記:
  - `.ics` は `data/items.json` から `tools/build_ics.py` で生成され、Actions が `calendar/` にコミットすること。
  - **`UID` に使うドメイン文字列と `id` は、一度公開したら変更しないこと**（購読者の既存予定が壊れるため）。
  - 既存項目の `id` を振り直す運用は禁止。
- `sitemap.xml` は .ics を載せる必要はありません（HTMLではないため）。
- `robots.txt` に `Disallow: /web/` を追加してあります（開発用デモページを検索結果に出さないため）。

---

## 3. 完了条件

- [ ] `python3 tools/check_sync.py` が OK を返す
- [ ] `python3 tools/build_ics.py --input data/items.json --outdir calendar` が9本の .ics と feeds.json を出力する
- [ ] 生成された .ics が `BEGIN:VCALENDAR` / `END:VCALENDAR` で閉じ、全行が 75 オクテット以下（折り返しが正しい）
- [ ] `calendar/aikatsu-all.ics` を Google カレンダーの「URLで追加」に貼って読み込めること
- [ ] iPhone の設定 → カレンダー → アカウント追加 → その他 → 照会するカレンダー、で読み込めること
- [ ] サイト上の購読ボタン → モーダル → 各ボタンとコピーが期待通り動くこと（ライト/ダーク両方）
- [ ] 既存機能（カレンダー表示・トピックス・検索・シェア）に影響がないこと

このリポジトリの状態で確認済みの項目:
Chromium(headless) でライト/ダーク・PC(1000px)/モバイル(390px) 表示、
モーダル開閉・Esc・フィード切り替え・生成されるURL、
JSエラーなし、要素IDの重複なし、HTMLのタグ対応、3つの `<script>` ブロックの構文、
`.ics` のパース・UID重複なし・全行75オクテット以下。

---

## 4. 注意点・落とし穴

- **UID の安定性が最重要。** `id` を振り直したり UID の生成規則を変えると、
  購読済みの人のカレンダーで予定が重複したり消えたりします。
- **GitHub Pages のキャッシュ**: Pages は `Cache-Control: max-age=600` 程度を返します。
  加えて Google カレンダーの外部URL取得は数時間〜1日程度の間隔なので、
  「更新したのに反映されない」という問い合わせが来ても正常です。
  README かモーダル内に「反映まで数時間かかることがあります」と書いておくと親切です。
- **`webcal://` は Android では動きません。** Android ユーザーは Google カレンダーのボタン
  またはURLコピーを使う導線になります（デモではその2つを常に併記しています）。
- `.ics` の MIME タイプは Pages が `text/calendar` を返します（拡張子ベース）。特に設定は不要です。
- 非公式ファンメイドである旨と、各 VEVENT の `DESCRIPTION` 末尾に出典URLを入れてあります。
  権利表記の観点でこの扱いを変えたい場合は `description_for()` を調整してください。

---

## 5. 参考: 決めきれていない点（判断が必要なら聞いてください）

1. 日付未定26件を含めるか（既定はスキップ）。
2. 周年のタイトルを `<startWord>開始記念日` としているが、別の言い回しにするか
   （例:「放送開始記念日」→「放送開始日」）。`resolve_anniversary()` の1行で変えられます。
3. フィードを9本も出すか、`all` と `nobirthday` の2本に絞るか。
   （購読UI側は6本だけ提示しています。増減する場合は両方を合わせてください）
4. `VALARM`（通知）を入れるか。現状は入れていません（購読者が自分で設定できるため）。
