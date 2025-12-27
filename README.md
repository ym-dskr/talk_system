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
- `conversation_app.py`: アプリケーションのメインエントリーポイント
- `wake_word_daemon.py`: ウェイクワード検知デーモン
- `src/`: ソースコード (音声処理、API通信、GUI、アニメーション)
  - `animation/`: キャラクターアニメーション関連
  - `audio.py`: 音声入出力
  - `realtime_client.py`: OpenAI Realtime API クライアント
  - `gui.py`: GUI管理
  - `wake_word.py`: ウェイクワード検知エンジン
- `assets/`: 画像・音声リソース
- `model/`: ウェイクワード検知モデル
- `utils/`: ユーティリティ関数
- `config.py`: 設定管理

## 📚 開発ドキュメント

### リファクタリング計画（v0.2.0 に向けて）

このプロジェクトは現在、プロトタイプから本格稼働システムへの移行を進めています。

- **[リファクタリング計画書](REFACTORING_PLAN.md)** - 全体設計と各Phaseの詳細仕様
- **[タスクトラッカー](TASK_TRACKER.md)** - 工程管理・進捗チェックリスト
- **[クイックスタートガイド](QUICKSTART_REFACTORING.md)** - 実装手順の実践ガイド

#### 主要な改善項目

1. **Phase 1: 基盤強化**（優先度: 🔴 最高）
   - 状態管理の明示化
   - ロギング基盤導入
   - 例外処理・復旧ロジック

2. **Phase 2: 設計改善**（優先度: 🟠 中）
   - 設定管理のリファクタリング（pydantic導入）
   - 並行処理の責務整理

3. **Phase 3: 機能拡張**（優先度: 🟡 中低）
   - 割り込み処理の改善
   - 人格切替機能（子供向けモード）

4. **Phase 4: 本格運用対応**（優先度: 🟢 低）
   - パッケージ化
   - systemd サービス化

### アーキテクチャ

詳細は開発中ですが、基本構成：
- **音声入力**: PyAudio (Thread) → asyncio Queue → WebSocket
- **Realtime API**: WebSocket (asyncio) → イベント駆動処理
- **音声出力**: asyncio Queue → PyAudio (Thread)
- **GUI**: pygame (メインスレッド)

## 🤝 コントリビューション

リファクタリング作業に参加する場合は、`QUICKSTART_REFACTORING.md` を参照してください。

## 📄 ライセンス

（ライセンス情報を記載してください）
