# talk_system リファクタリング タスクトラッカー

**作成日**: 2025-12-27
**ステータス**: 🟡 進行中
**現在のPhase**: Phase 0 (準備)

---

## 📊 進捗サマリー

| Phase | タスク名         | ステータス | 完了タスク数 | 総タスク数 | 進捗率 |
| ----- | ------------ | ----- | ------ | ----- | --- |
| 0     | 準備フェーズ       | ⬜ 未着手 | 0      | 3     | 0%  |
| 1.1   | 状態管理の明示化     | ⬜ 未着手 | 0      | 4     | 0%  |
| 1.2   | ロギング基盤導入     | ⬜ 未着手 | 0      | 4     | 0%  |
| 1.3   | 例外処理・復旧ロジック  | ⬜ 未着手 | 0      | 4     | 0%  |
| 1.4   | Phase 1 統合テスト | ⬜ 未着手 | 0      | 3     | 0%  |
| 2.1   | 設定管理リファクタ    | ⬜ 未着手 | 0      | 4     | 0%  |
| 2.2   | 並行処理責務整理     | ⬜ 未着手 | 0      | 3     | 0%  |
| 3.1   | 割り込み処理改善     | ⬜ 未着手 | 0      | 3     | 0%  |
| 3.2   | 人格切替機能       | ⬜ 未着手 | 0      | 3     | 0%  |
| 4.1   | パッケージ化       | ⬜ 未着手 | 0      | 3     | 0%  |
| 4.2   | systemd対応    | ⬜ 未着手 | 0      | 3     | 0%  |

**総合進捗**: 0/37 タスク完了 (0%)

---

## Phase 0: 準備フェーズ

**目的**: リファクタリングを安全に開始するための環境準備

### タスクリスト

- [ ] **P0-1**: 現在の動作コードをバックアップ
  - コマンド: `git checkout -b backup/pre-refactor-$(date +%Y%m%d)`
  - 確認: `git log --oneline -1`

- [ ] **P0-2**: 開発ブランチを作成
  - コマンド: `git checkout -b feature/phase1-state-management`
  - 確認: `git branch --show-current`

- [ ] **P0-3**: 仮想環境に開発依存関係をインストール
  ```bash
  .venv/bin/pip install pytest pytest-asyncio black mypy
  ```
  - 確認: `.venv/bin/pip list | grep pytest`

### 完了条件
- [ ] すべてのタスクが完了
- [ ] 現在の動作環境が保全されている

---

## Phase 1.1: 状態管理の明示化

**優先度**: 🔴 最高
**依存**: Phase 0 完了
**目標**: 状態遷移を明示的に管理し、デバッグ可能にする

### タスクリスト

- [ ] **P1.1-1**: `src/state_machine.py` を作成
  - [ ] `AppState` Enum を定義（IDLE, LISTENING, PROCESSING, SPEAKING, ERROR）
  - [ ] `StateTransition` クラスを実装
  - [ ] `is_valid_transition()` メソッドを実装
  - 確認: `python -c "from src.state_machine import AppState; print(AppState.LISTENING)"`

- [ ] **P1.1-2**: `conversation_app.py` に状態遷移ロジックを組み込み
  - [ ] `AppState` をインポート
  - [ ] `self.state = STATE_LISTENING` → `self.state = AppState.LISTENING` に変更
  - [ ] `set_state()` メソッドを追加（遷移検証付き）
  - [ ] すべての状態変更箇所を `set_state()` に置き換え
  - 確認: `grep -n "self.state =" conversation_app.py` で直接代入がないことを確認

- [ ] **P1.1-3**: `gui.py` の状態表示を `AppState` に対応
  - [ ] `set_state()` の引数を `int` から `AppState` に変更
  - [ ] インジケーター表示ロジックを更新
  - 確認: GUI起動時にエラーが出ないことを確認

- [ ] **P1.1-4**: 動作確認
  - [ ] アプリを起動し、状態遷移が正常に動作することを確認
  - [ ] 不正な状態遷移が警告されることを確認（意図的にテスト）
  - [ ] ログで状態遷移が追跡可能なことを確認

### 成果物
- `src/state_machine.py` (新規)
- `conversation_app.py` (修正)
- `src/gui.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] 動作確認テストがすべてパス
- [ ] git commit済み（コミットメッセージ: "feat: implement explicit state machine"）

---

## Phase 1.2: ロギング基盤導入

**優先度**: 🔴 最高
**依存**: なし（Phase 1.1と並行実施可能）
**目標**: print文を卒業し、本格的なロギング基盤を導入

### タスクリスト

- [ ] **P1.2-1**: `src/logging_config.py` を作成
  - [ ] `setup_logging()` 関数を実装
  - [ ] ファイルハンドラー（日次ローテーション）を設定
  - [ ] コンソールハンドラーを設定
  - [ ] フォーマッターを設定（タイムスタンプ、レベル、モジュール名、行番号）
  - 確認: `python -c "from src.logging_config import setup_logging; setup_logging()"`

- [ ] **P1.2-2**: `logs/` ディレクトリを作成
  ```bash
  mkdir -p logs
  echo "logs/*.log" >> .gitignore
  ```
  - 確認: `ls -ld logs/`

- [ ] **P1.2-3**: 全ファイルの `print()` を `logger` に置換
  - [ ] `conversation_app.py`: 全print文をlogger.info/debug/errorに変更
  - [ ] `src/realtime_client.py`: 全print文をlogger.info/debug/errorに変更
  - [ ] `src/audio.py`: 全print文をlogger.info/debug/errorに変更
  - [ ] `src/gui.py`: 全print文をlogger.info/debug/errorに変更
  - [ ] `wake_word_daemon.py`: 全print文をlogger.info/debug/errorに変更
  - 確認: `grep -r "print(" --include="*.py" | grep -v ".venv" | wc -l` が0になることを確認

- [ ] **P1.2-4**: 動作確認
  - [ ] アプリを起動し、`logs/talk_system.log` にログが出力されることを確認
  - [ ] ログファイルにタイムスタンプ、レベル、モジュール名が含まれることを確認
  - [ ] コンソールにもログが表示されることを確認

### 成果物
- `src/logging_config.py` (新規)
- `logs/` ディレクトリ (新規)
- `.gitignore` (更新)
- `conversation_app.py`, `src/*.py`, `wake_word_daemon.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] `print()` が完全に削除されている（.venv除く）
- [ ] ログファイルが生成され、内容が確認できる
- [ ] git commit済み（コミットメッセージ: "feat: introduce logging infrastructure"）

---

## Phase 1.3: 例外処理・復旧ロジック

**優先度**: 🔴 最高
**依存**: Phase 1.2 完了（ログ基盤が必要）
**目標**: 常駐プロセスとしての安定性を向上

### タスクリスト

- [ ] **P1.3-1**: `src/audio.py` に例外処理を追加
  - [ ] `start_stream()` に try/except 追加
  - [ ] `_list_audio_devices()` メソッドを実装（デバイス診断）
  - [ ] エラー時にデバイス一覧をログ出力
  - [ ] `terminate()` を try/finally で保護
  - 確認: マイクを接続せずに起動し、エラーメッセージとデバイス一覧が表示されることを確認

- [ ] **P1.3-2**: `src/realtime_client.py` に自動再接続機能を追加
  - [ ] `max_reconnect_attempts` パラメータを追加
  - [ ] `reconnect_delay` パラメータを追加
  - [ ] `connect()` を `_connect_internal()` に分離
  - [ ] 再接続ループを実装
  - [ ] 各試行でログ出力
  - 確認: 無効なAPIキーで起動し、再接続が試行されることを確認

- [ ] **P1.3-3**: `conversation_app.py` のエラーハンドリングを強化
  - [ ] メインループ全体を try/except で保護
  - [ ] `cleanup()` を finally で必ず実行
  - [ ] エラー時に `AppState.ERROR` に遷移
  - 確認: 意図的に例外を発生させて、クリーンアップが実行されることを確認

- [ ] **P1.3-4**: 動作確認
  - [ ] マイク未接続で起動 → エラーメッセージ表示
  - [ ] WebSocket切断 → 自動再接続試行
  - [ ] 例外発生 → ログ記録 + クリーンアップ実行
  - [ ] 通常動作が影響を受けないことを確認

### 成果物
- `src/audio.py` (修正)
- `src/realtime_client.py` (修正)
- `conversation_app.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] エラーシナリオテストがすべてパス
- [ ] git commit済み（コミットメッセージ: "feat: add robust exception handling and recovery"）

---

## Phase 1.4: Phase 1 統合テスト

**優先度**: 🔴 高
**依存**: Phase 1.1, 1.2, 1.3 完了
**目標**: Phase 1 の成果物を統合し、安定性を確認

### タスクリスト

- [ ] **P1.4-1**: 状態遷移テスト
  - [ ] IDLE → LISTENING → PROCESSING → SPEAKING の正常フロー
  - [ ] 不正な状態遷移が警告ログに記録される
  - [ ] エラー時に ERROR 状態に遷移する

- [ ] **P1.4-2**: ログ出力テスト
  - [ ] `logs/talk_system.log` にすべてのイベントが記録される
  - [ ] エラー時にスタックトレースが出力される
  - [ ] ログレベル（INFO, ERROR）が適切に設定されている

- [ ] **P1.4-3**: 復旧テスト
  - [ ] マイクを接続せずに起動 → エラーメッセージとデバイス一覧が表示される
  - [ ] WebSocket切断後、自動再接続が試行される
  - [ ] 再接続失敗時に適切なエラーメッセージが表示される

### 成果物
- 統合テストレポート（このファイルに記録）

### 完了条件
- [ ] すべてのテストがパス
- [ ] Phase 1 完了報告をREADMEに記載
- [ ] git tag付与: `git tag v0.1.0-phase1`
- [ ] メインブランチにマージ: `git checkout main && git merge feature/phase1-state-management`

---

## Phase 2.1: 設定管理のリファクタリング

**優先度**: 🟠 中
**依存**: Phase 1 完了
**目標**: 型安全な設定管理を導入

### タスクリスト

- [ ] **P2.1-1**: `src/config_models.py` を作成
  - [ ] `AudioConfig` クラスを定義（pydantic.BaseModel）
  - [ ] `RealtimeConfig` クラスを定義
  - [ ] `AppConfig` クラスを定義
  - [ ] 環境変数読み込み設定（`env_file=".env"`）
  - 確認: `python -c "from src.config_models import AppConfig; print(AppConfig)"`

- [ ] **P2.1-2**: `config.py` を更新
  - [ ] `AppConfig` をインポート
  - [ ] インスタンスを生成（`.env` から読み込み）
  - [ ] 後方互換のためのエイリアスを追加
  - 確認: `python -c "from config import SAMPLE_RATE; print(SAMPLE_RATE)"`

- [ ] **P2.1-3**: 型ヒント補完を確認
  - [ ] VS Code / PyCharm で `app_config.audio.` を入力し、補完が効くことを確認
  - [ ] mypy で型チェック: `mypy src/config_models.py`

- [ ] **P2.1-4**: 動作確認
  - [ ] `.env` の設定値が正しく読み込まれることを確認
  - [ ] 既存コードが影響を受けないことを確認（後方互換性）

### 成果物
- `src/config_models.py` (新規)
- `config.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] mypy 型チェックがパス
- [ ] git commit済み（コミットメッセージ: "refactor: introduce pydantic-based config management"）

---

## Phase 2.2: 並行処理の責務整理

**優先度**: 🟠 中
**依存**: なし（Phase 2.1と並行可）
**目標**: アーキテクチャをドキュメント化し、保守性を向上

### タスクリスト

- [ ] **P2.2-1**: `docs/` ディレクトリを作成
  ```bash
  mkdir -p docs
  ```

- [ ] **P2.2-2**: `docs/ARCHITECTURE.md` を作成
  - [ ] 並行処理モデルの表を記載
  - [ ] データフローを図解
  - [ ] 各モジュールの責務を明記

- [ ] **P2.2-3**: `conversation_app.py` にコメント追加
  - [ ] 音声ストリーム開始部分にコメント
  - [ ] WebSocket接続部分にコメント
  - [ ] メインループ部分にコメント

### 成果物
- `docs/ARCHITECTURE.md` (新規)
- `conversation_app.py` (コメント追加)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] ドキュメントがレビュー可能
- [ ] git commit済み（コミットメッセージ: "docs: add architecture documentation"）

---

## Phase 3.1: 割り込み処理の改善

**優先度**: 🟡 中低
**依存**: Phase 1 完了
**目標**: ユーザー体験を向上（応答性改善）

### タスクリスト

- [ ] **P3.1-1**: `src/audio.py` に即座停止機能を追加
  - [ ] `playback_active` フラグを追加
  - [ ] `stop_requested` フラグを追加
  - [ ] `play_audio()` をチャンク単位で停止可能に
  - [ ] `stop_playback()` でストリームバッファをクリア

- [ ] **P3.1-2**: `conversation_app.py` の割り込み処理を強化
  - [ ] `execute_interrupt()` で `audio.stop_playback()` を呼び出し
  - [ ] ログで割り込みフローを記録

- [ ] **P3.1-3**: 動作確認
  - [ ] AI応答中にウェイクワード発話 → 音声が即座停止
  - [ ] 残存チャンクが再生されないことを確認
  - [ ] ログで割り込みが追跡可能

### 成果物
- `src/audio.py` (修正)
- `conversation_app.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] 割り込みテストがパス
- [ ] git commit済み（コミットメッセージ: "feat: improve interrupt responsiveness"）

---

## Phase 3.2: 人格切替機能（子供向けモード）

**優先度**: 🟡 中低
**依存**: Phase 2.1 完了推奨
**目標**: 利用シーン拡大

### タスクリスト

- [ ] **P3.2-1**: `src/personality.py` を作成
  - [ ] `PersonalityMode` Enum を定義
  - [ ] `PersonalityConfig` クラスを実装
  - [ ] INSTRUCTIONS 辞書を定義（NORMAL, CHILD_FRIENDLY, CONCISE）
  - [ ] VAD_SETTINGS 辞書を定義

- [ ] **P3.2-2**: `config.py` に人格モード設定を追加
  - [ ] `PERSONALITY_MODE` を環境変数から読み込み
  - [ ] デフォルトは `normal`

- [ ] **P3.2-3**: `src/realtime_client.py` に人格モード対応を追加
  - [ ] `connect()` に `personality_mode` パラメータを追加
  - [ ] セッション設定で instructions を差し替え
  - [ ] VAD設定をモードに応じて調整

### 成果物
- `src/personality.py` (新規)
- `config.py` (修正)
- `src/realtime_client.py` (修正)

### 完了条件
- [ ] `.env` に `PERSONALITY_MODE=child_friendly` を設定して起動
- [ ] AI応答が子供向けの口調になる
- [ ] VAD設定が適用される
- [ ] git commit済み（コミットメッセージ: "feat: add personality mode switching"）

---

## Phase 4.1: パッケージ化

**優先度**: 🟢 低
**依存**: Phase 1, 2, 3 完了
**目標**: 本格的なPythonパッケージとして整備

### タスクリスト

- [ ] **P4.1-1**: `pyproject.toml` を作成
  - [ ] プロジェクトメタデータを記載
  - [ ] 依存関係を記載
  - [ ] スクリプトエントリーポイントを定義

- [ ] **P4.1-2**: ディレクトリ構造をリファクタリング
  - [ ] `src/` → `talk_system/` にリネーム
  - [ ] `conversation_app.py` → `talk_system/app.py` に移動
  - [ ] インポートパスを更新

- [ ] **P4.1-3**: インストールテスト
  ```bash
  pip install -e .
  talk-system  # コマンドで起動可能か確認
  ```

### 成果物
- `pyproject.toml` (新規)
- ディレクトリ構造変更

### 完了条件
- [ ] `pip install -e .` でインストール可能
- [ ] `talk-system` コマンドで起動可能
- [ ] git commit済み（コミットメッセージ: "refactor: package structure"）

---

## Phase 4.2: systemd サービス化

**優先度**: 🟢 低
**依存**: Phase 4.1 完了
**目標**: Raspberry Pi 常駐サービスとして動作

### タスクリスト

- [ ] **P4.2-1**: `systemd/talk-system.service` を作成
  - [ ] ユニットファイルを作成
  - [ ] 環境変数を設定
  - [ ] 自動再起動設定

- [ ] **P4.2-2**: `scripts/install_service.sh` を作成
  - [ ] サービスファイルをコピー
  - [ ] systemd リロード
  - [ ] サービス有効化

- [ ] **P4.2-3**: インストールテスト
  ```bash
  chmod +x scripts/install_service.sh
  ./scripts/install_service.sh
  sudo systemctl start talk-system
  sudo journalctl -u talk-system -f
  ```

### 成果物
- `systemd/talk-system.service` (新規)
- `scripts/install_service.sh` (新規)

### 完了条件
- [ ] サービスがインストールされる
- [ ] `sudo systemctl start talk-system` で起動
- [ ] Raspberry Pi 再起動後、自動起動する
- [ ] git commit済み（コミットメッセージ: "feat: add systemd service support"）

---

## 🔄 更新履歴

| 日付         | 更新内容    | 更新者    |
| ---------- | ------- | ------ |
| 2025-12-27 | 初版作成    | Claude |
|            |         |        |
|            |         |        |

---

## 📝 メモ・課題

### 進行中の課題
- （なし）

### 検討事項
- （なし）

### 次回作業予定
- Phase 0 の準備作業から開始

---

## 🎯 次のアクション

1. **Phase 0** を完了させる
   - バックアップブランチ作成
   - 開発ブランチ作成
   - 開発依存関係インストール

2. **Phase 1.1** または **Phase 1.2** に着手（並行可）
   - 状態管理の明示化
   - ロギング基盤導入

3. このファイル（TASK_TRACKER.md）を更新し続ける
   - タスク完了時にチェックボックスを更新
   - 進捗率を更新
   - 課題・メモを記録
