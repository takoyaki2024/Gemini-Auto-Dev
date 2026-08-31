# Codex Reset Notifier

Codex の 5時間利用枠がリセットされる時刻に、Windows へ通知を出す小さなツールです。

現在は2方式あります。

## 1. 自動検出モード（推奨）

`start-auto.bat` を起動すると、`%USERPROFILE%\.codex` 配下のローカル履歴ファイルから、Codex が表示した利用上限メッセージや `5h limit ... resets ...` の時刻を探します。

検出できた例:

```text
You've hit your usage limit ... try again at Sep 13th, 2026 7:11 PM
```

```text
5h limit: 0% left (resets 16:10)
```

未来のリセット時刻を検出すると、その時刻まで待機して Windows のメッセージ通知を出します。

### 自動検出モードの特徴

- OpenAI APIを呼ばない
- APIキー不要
- モデルを消費する定期プローブを行わない
- `auth.json` と `config.toml` は読み取り対象から除外
- ローカルPC内だけで処理
- 30秒ごとにローカル履歴だけを確認

### 注意

Codex のローカルファイル形式は将来変更される可能性があります。また、Codex がリセット時刻をローカル履歴へ残さないケースでは自動検出できません。その場合は手動モードを使ってください。

## 2. 手動モード

Codex の Settings → Usage や `/status` などに表示されたリセット時刻を入力して通知予約します。

1. `set-reset.bat` をダブルクリック
2. `HH:mm` または `yyyy-MM-dd HH:mm` 形式で入力

例:

```text
23:40
```

または

```text
2026-09-01 23:40
```

`HH:mm` の場合、その時刻が今日すでに過ぎていれば翌日として扱います。

通知予約を取り消す場合は `cancel-reset.bat` を実行します。

## ファイル

- `start-auto.bat` — 自動検出を開始
- `auto-watch.ps1` — Codexローカル履歴を監視して自動通知
- `set-reset.bat` — 手動通知設定
- `set-reset.ps1` — 手動設定処理
- `watch-reset.ps1` — 手動モードの待機・通知
- `cancel-reset.bat` — 手動通知の取消
- `cancel-reset.ps1` — 手動通知の取消処理

## 方針

- 追加料金なし
- OpenAI API利用なし
- 外部Pythonパッケージ不要
- Windows標準PowerShellのみ
- 認証情報を外部へ送信しない

## 今後

Codex が将来、公式の機械読み取り可能な usage/status コマンドやAPIを提供した場合は、ローカル履歴解析より公式手段を優先します。
