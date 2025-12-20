# Kikai-kun (キカイくん)

Raspberry Pi 5上で動作する、OpenAI GPT-4o Realtime APIを活用した音声対話型アシスタントシステムです。
画面上のキャラクターが、あなたの呼びかけ「Kikai-kun（キカイくん）」に応答し、自然な会話を行います。

## 特徴
- **リアルタイム対話**: OpenAI Realtime APIによる低遅延な音声対話
- **ウェイクワード検知**: Picovoice Porcupineを使用した省電力な待機
- **ビジュアルフィードバック**: Pygameによるキャラクターアニメーション

## 動作環境
- **ハードウェア**: Raspberry Pi 5 (推奨) / Linux環境
- **OS**: Raspberry Pi OS (または互換Linux)
- **Python**: 3.11以上

## セットアップ

1. **リポジトリのクローン**
   ```bash
   git clone <repository_url>
   cd talk_system
   ```

2. **依存ライブラリのインストール**
   ```bash
   # 仮想環境の作成（推奨）
   python3 -m venv .venv
   source .venv/bin/activate

   # ライブラリのインストール
   pip install -r requirements.txt
   ```

3. **環境変数の設定**
   `.env`ファイルを作成し、以下のAPIキーを設定してください。

   ```env
   OPENAI_API_KEY=your_openai_api_key
   PICOVOICE_ACCESS_KEY=your_picovoice_access_key
   ```
   ※ `OPENAI_API_KEY` は `gpt-4o-realtime-preview` へのアクセス権限が必要です。

4. **モデルファイルの配置**
   `model/` ディレクトリにPorcupineのモデルファイル (`.ppn`) が配置されていることを確認してください。

## 実行方法

```bash
python main.py
```

起動後、マイクに向かって「Kikai-kun（またはキカイくん）」と話しかけると会話が開始されます。

## ディレクトリ構成
- `main.py`: アプリケーションのエントリーポイント
- `src/`: ソースコード (音声処理、API通信、GUI)
- `assets/`: 画像・音声リソース
- `model/`: ウェイクワード検知モデル
