# Gemini-Auto-Dev

Gemini API を1モデル固定で使う、ローカル自動開発システムの v1 です。

## 方針

- 固定モデル: `gemini-3.7-flash`
- モデル自動切替なし
- 有料モデルへの自動フォールバックなし
- 指定 workspace 内のファイル作成 / 編集 / ファイル削除を自動化
- ビルド / テスト / 依存関係インストール用コマンドを自動実行
- Git checkpoint / commit
- 同一失敗の反復を検知し、1回だけ別アプローチを要求
- それでも改善しなければ `STUCK_DETECTED` で停止
- `.env` 等の秘密情報はコンテキストから除外
- workspace 外へのファイル操作を拒否
- OS破壊系コマンドを拒否

## セットアップ (Windows PowerShell)

```powershell
git clone https://github.com/takoyaki2024/Gemini-Auto-Dev.git
cd Gemini-Auto-Dev

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:GEMINI_API_KEY="あなたのAPIキー"
```

永続的に設定する場合:

```powershell
setx GEMINI_API_KEY "あなたのAPIキー"
```

`setx` 後は新しい PowerShell を開いてください。

## テスト

```powershell
pytest -q
```

## 実行

```powershell
python app.py D:\GitHub\対象プロジェクト --task "このプロジェクトを完成させて"
```

または:

```powershell
python app.py D:\GitHub\対象プロジェクト
```

すると `開発依頼>` が表示されます。

## 注意

この v1 は自動実行を重視していますが、以下は強制的に拒否します。

- workspace 外へのファイル書き込み
- ルート / Windows / Users 等を対象にした破壊的削除
- `format`, `diskpart`, `shutdown`, `reg delete` 等

開発に必要な `pip install`, `npm install`, `dotnet` 系コマンド等は Gemini が返した場合に実行できます。

## v2

v1 が安定した後に、複数 Gemini ワーカーの並列処理を追加します。
