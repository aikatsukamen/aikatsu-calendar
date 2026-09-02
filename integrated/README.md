# aikatsu-calendar

「アイカツ！」シリーズのイベント日程・グッズ発売日・キャラクター誕生日をまとめた非公式ファンメイドカレンダーです。

サイト: https://aikatsu-info.github.io/aikatsu-calendar/

## カレンダーを購読する

サイト右上の「カレンダー購読」ボタンから、お使いのカレンダーアプリに追加できます。
URLを直接登録することもできます。

| 内容 | 購読URL |
|---|---|
| すべて | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-all.ics |
| 誕生日・周年を除く | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-nobirthday.ics |
| イベント | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-event.ics |
| グッズ | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-goods.ics |
| アニメ・映像 | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-anime.ics |
| アイカツ！アンコール | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-game.ics |
| 配信 | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-stream.ics |
| 誕生日 | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-birthday.ics |
| 周年 | https://aikatsu-info.github.io/aikatsu-calendar/calendar/aikatsu-anniversary.ics |

- 更新の反映には数時間かかることがあります（カレンダーアプリ側の取得間隔によります）。
- 日付が未定の情報は .ics には含まれません。サイトの「日程未定のトピックス」でご確認ください。
- 周年は毎年繰り返しの予定として登録されるため、カレンダー上では「◯周年」ではなく
  「放送開始記念日」のように表示されます。何周年かは予定の説明文の日付からご確認ください。
- 非公式のファンメイドです。予定は変更・中止される場合があるため、最終的な情報は各公式サイトでご確認ください。

## データ

- `data/items.json` — カレンダーデータ（JSON）
- `calendar/*.ics` — 上記から生成した iCalendar 形式（`tools/build_ics.py` / GitHub Actions が生成）
- `calendar/feeds.json` — 配信中のフィード一覧
