# talk_system リファクタリング タスクトラッカー

**作成日**: 2025-12-27
**最終更新**: 2025-12-28
**ステータス**: 🟡 Phase 1-2 完了、Phase 2追加タスク（2.3-2.7）計画中
**現在のPhase**: Phase 2.3-2.7 (アーキテクチャ改善) → Phase 3 (機能拡張) → Phase 4 (プロダクション対応)

---

## 📊 進捗サマリー

| Phase | タスク名              | ステータス | 完了タスク数 | 総タスク数 | 進捗率  |
| ----- | ----------------- | ----- | ------ | ----- | ---- |
| 0     | 準備フェーズ            | ✅ 完了  | 3      | 3     | 100% |
| 1.1   | 状態管理の明示化          | ✅ 完了  | 4      | 4     | 100% |
| 1.2   | ロギング基盤導入          | ✅ 完了  | 4      | 4     | 100% |
| 1.3   | 例外処理・復旧ロジック       | ✅ 完了  | 4      | 4     | 100% |
| 1.4   | Phase 1 統合テスト     | ✅ 完了  | 3      | 3     | 100% |
| 2.1   | 設定管理リファクタ         | ✅ 完了  | 4      | 4     | 100% |
| 2.2   | 並行処理責務整理          | ✅ 完了  | 3      | 3     | 100% |
| 2.3   | フラグ統合とイベント駆動      | ⬜ 未着手 | 0      | 7     | 0%   |
| 2.4   | タスクライフサイクル管理      | ⬜ 未着手 | 0      | 2     | 0%   |
| 2.5   | 最小テスト導入          | ⬜ 未着手 | 0      | 5     | 0%   |
| 2.6   | audioop代替         | ⬜ 未着手 | 0      | 3     | 0%   |
| 2.7   | config.py段階的廃止    | ⬜ 未着手 | 0      | 3     | 0%   |
| 3.1   | 割り込み処理改善          | ⬜ 未着手 | 0      | 3     | 0%   |
| 3.2   | 人格切替機能            | ⬜ 未着手 | 0      | 3     | 0%   |
| 4.1   | パッケージ化            | ⬜ 未着手 | 0      | 3     | 0%   |
| 4.2   | systemd対応         | ⬜ 未着手 | 0      | 3     | 0%   |

**総合進捗**: 29/57 タスク完了 (51%)

---

## Phase 0: 準備フェーズ ✅

**目的**: リファクタリングを安全に開始するための環境準備
**ステータス**: ✅ 完了

### タスクリスト

- [x] **P0-1**: 現在の動作コードをバックアップ
  - コマンド: `git checkout -b backup/pre-refactor-$(date +%Y%m%d)`
  - 確認: `git log --oneline -1`

- [x] **P0-2**: 開発ブランチを作成
  - コマンド: `git checkout -b feature/phase1-foundation`
  - 確認: `git branch --show-current`

- [x] **P0-3**: 仮想環境に開発依存関係をインストール
  ```bash
  .venv/bin/pip install pytest pytest-asyncio black mypy
  ```
  - 確認: `.venv/bin/pip list | grep pytest`

### 完了条件
- [x] すべてのタスクが完了
- [x] 現在の動作環境が保全されている

---

## Phase 1.1: 状態管理の明示化 ✅

**優先度**: 🔴 最高
**依存**: Phase 0 完了
**目標**: 状態遷移を明示的に管理し、デバッグ可能にする
**ステータス**: ✅ 完了
**完了日**: 2025-12-27
**コミット**: 115328e

### タスクリスト

- [x] **P1.1-1**: `src/state_machine.py` を作成
  - [x] `AppState` Enum を定義（IDLE, LISTENING, PROCESSING, SPEAKING, ERROR）
  - [x] `StateTransition` クラスを実装
  - [x] `is_valid_transition()` メソッドを実装
  - 確認: `python -c "from src.state_machine import AppState; print(AppState.LISTENING)"`

- [x] **P1.1-2**: `conversation_app.py` に状態遷移ロジックを組み込み
  - [x] `AppState` をインポート
  - [x] `self.state = STATE_LISTENING` → `self.state = AppState.LISTENING` に変更
  - [x] `set_state()` メソッドを追加（遷移検証付き）
  - [x] すべての状態変更箇所を `set_state()` に置き換え
  - 確認: `grep -n "self.state =" conversation_app.py` で直接代入がないことを確認

- [x] **P1.1-3**: `gui.py` の状態表示を `AppState` に対応
  - [x] `set_state()` の引数を `int` から `AppState` に変更
  - [x] インジケーター表示ロジックを更新
  - 確認: GUI起動時にエラーが出ないことを確認

- [x] **P1.1-4**: 動作確認
  - [x] アプリを起動し、状態遷移が正常に動作することを確認
  - [x] 不正な状態遷移が警告されることを確認（意図的にテスト）
  - [x] ログで状態遷移が追跡可能なことを確認

### 成果物
- `src/state_machine.py` (新規) ✅
- `conversation_app.py` (修正) ✅
- `src/gui.py` (修正) ✅

### 完了条件
- [x] すべてのタスクが完了
- [x] 動作確認テストがすべてパス
- [x] git commit済み（コミットメッセージ: "feat(phase1.1): implement explicit state machine"）

---

## Phase 1.2: ロギング基盤導入 ✅

**優先度**: 🔴 最高
**依存**: なし（Phase 1.1と並行実施可能）
**目標**: print文を卒業し、本格的なロギング基盤を導入
**ステータス**: ✅ 完了
**完了日**: 2025-12-27
**コミット**: 8380e7e

### タスクリスト

- [x] **P1.2-1**: `src/logging_config.py` を作成
  - [x] `setup_logging()` 関数を実装
  - [x] ファイルハンドラー（日次ローテーション）を設定
  - [x] コンソールハンドラーを設定
  - [x] フォーマッターを設定（タイムスタンプ、レベル、モジュール名、行番号）
  - 確認: `python -c "from src.logging_config import setup_logging; setup_logging()"`

- [x] **P1.2-2**: `logs/` ディレクトリを作成
  ```bash
  mkdir -p logs
  echo "logs/*.log" >> .gitignore
  ```
  - 確認: `ls -ld logs/`

- [x] **P1.2-3**: 全ファイルの `print()` を `logger` に置換
  - [x] `conversation_app.py`: 全print文をlogger.info/debug/errorに変更
  - [x] `src/realtime_client.py`: 全print文をlogger.info/debug/errorに変更
  - [x] `src/audio.py`: 全print文をlogger.info/debug/errorに変更
  - [x] `src/gui.py`: 全print文をlogger.info/debug/errorに変更
  - [x] `wake_word_daemon.py`: 全print文をlogger.info/debug/errorに変更
  - 確認: `grep -r "print(" --include="*.py" | grep -v ".venv" | wc -l` が0になることを確認

- [x] **P1.2-4**: 動作確認
  - [x] アプリを起動し、`logs/talk_system.log` にログが出力されることを確認
  - [x] ログファイルにタイムスタンプ、レベル、モジュール名が含まれることを確認
  - [x] コンソールにもログが表示されることを確認

### 成果物
- `src/logging_config.py` (新規) ✅
- `logs/` ディレクトリ (新規) ✅
- `.gitignore` (更新) ✅
- `conversation_app.py`, `src/*.py`, `wake_word_daemon.py` (修正) ✅

### 完了条件
- [x] すべてのタスクが完了
- [x] `print()` が完全に削除されている（.venv除く）
- [x] ログファイルが生成され、内容が確認できる
- [x] git commit済み（コミットメッセージ: "feat(phase1.2): introduce logging infrastructure"）

---

## Phase 1.3: 例外処理・復旧ロジック ✅

**優先度**: 🔴 最高
**依存**: Phase 1.2 完了（ログ基盤が必要）
**目標**: 常駐プロセスとしての安定性を向上
**ステータス**: ✅ 完了
**完了日**: 2025-12-27
**コミット**: c52ab6c

### タスクリスト

- [x] **P1.3-1**: `src/audio.py` に例外処理を追加
  - [x] `start_stream()` に try/except 追加
  - [x] `_list_audio_devices()` メソッドを実装（デバイス診断）
  - [x] エラー時にデバイス一覧をログ出力
  - [x] `terminate()` を try/finally で保護
  - 確認: マイクを接続せずに起動し、エラーメッセージとデバイス一覧が表示されることを確認

- [x] **P1.3-2**: `src/realtime_client.py` に自動再接続機能を追加
  - [x] `max_reconnect_attempts` パラメータを追加
  - [x] `reconnect_delay` パラメータを追加
  - [x] `connect()` を `_connect_internal()` に分離
  - [x] 再接続ループを実装
  - [x] 各試行でログ出力
  - 確認: 無効なAPIキーで起動し、再接続が試行されることを確認

- [x] **P1.3-3**: `conversation_app.py` のエラーハンドリングを強化
  - [x] メインループ全体を try/except で保護
  - [x] `cleanup()` を finally で必ず実行
  - [x] エラー時に `AppState.ERROR` に遷移
  - 確認: 意図的に例外を発生させて、クリーンアップが実行されることを確認

- [x] **P1.3-4**: 動作確認
  - [x] マイク未接続で起動 → エラーメッセージ表示
  - [x] WebSocket切断 → 自動再接続試行
  - [x] 例外発生 → ログ記録 + クリーンアップ実行
  - [x] 通常動作が影響を受けないことを確認

### 成果物
- `src/audio.py` (修正) ✅
- `src/realtime_client.py` (修正) ✅
- `conversation_app.py` (修正) ✅

### 完了条件
- [x] すべてのタスクが完了
- [x] エラーシナリオテストがすべてパス
- [x] git commit済み（コミットメッセージ: "feat(phase1.3): add robust exception handling and recovery"）

---

## Phase 1.4: Phase 1 統合テスト ✅

**優先度**: 🔴 高
**依存**: Phase 1.1, 1.2, 1.3 完了
**目標**: Phase 1 の成果物を統合し、安定性を確認
**ステータス**: ✅ 完了
**完了日**: 2025-12-27

### タスクリスト

- [x] **P1.4-1**: 状態遷移テスト
  - [x] IDLE → LISTENING → PROCESSING → SPEAKING の正常フロー
  - [x] 不正な状態遷移が警告ログに記録される
  - [x] エラー時に ERROR 状態に遷移する

- [x] **P1.4-2**: ログ出力テスト
  - [x] `logs/talk_system.log` にすべてのイベントが記録される
  - [x] エラー時にスタックトレースが出力される
  - [x] ログレベル（INFO, ERROR）が適切に設定されている

- [x] **P1.4-3**: 復旧テスト
  - [x] マイクを接続せずに起動 → エラーメッセージとデバイス一覧が表示される
  - [x] WebSocket切断後、自動再接続が試行される
  - [x] 再接続失敗時に適切なエラーメッセージが表示される

### 成果物
- 統合テストレポート（TESTING_CHECKLIST.mdに記録） ✅

### 完了条件
- [x] すべてのテストがパス
- [x] Phase 1 完了報告をREADMEに記載
- [x] メインブランチにマージ: `git checkout main && git merge feature/phase1-foundation`

---

## Phase 2.1: 設定管理のリファクタリング ✅

**優先度**: 🟠 中
**依存**: Phase 1 完了
**目標**: 型安全な設定管理を導入
**ステータス**: ✅ 完了
**完了日**: 2025-12-27
**コミット**: e228b77

### タスクリスト

- [x] **P2.1-1**: `src/config_models.py` を作成
  - [x] `AudioConfig` クラスを定義（pydantic.BaseModel）
  - [x] `RealtimeConfig` クラスを定義
  - [x] `AppConfig` クラスを定義
  - [x] 環境変数読み込み設定（`env_file=".env"`）
  - 確認: `python -c "from src.config_models import AppConfig; print(AppConfig)"`

- [x] **P2.1-2**: `config.py` を更新
  - [x] `AppConfig` をインポート
  - [x] インスタンスを生成（`.env` から読み込み）
  - [x] 後方互換のためのエイリアスを追加
  - 確認: `python -c "from config import SAMPLE_RATE; print(SAMPLE_RATE)"`

- [x] **P2.1-3**: 型ヒント補完を確認
  - [x] VS Code / PyCharm で `app_config.audio.` を入力し、補完が効くことを確認
  - [x] mypy で型チェック: `mypy src/config_models.py`

- [x] **P2.1-4**: 動作確認
  - [x] `.env` の設定値が正しく読み込まれることを確認
  - [x] 既存コードが影響を受けないことを確認（後方互換性）

### 成果物
- `src/config_models.py` (新規) ✅
- `config.py` (修正) ✅

### 完了条件
- [x] すべてのタスクが完了
- [x] mypy 型チェックがパス
- [x] git commit済み（コミットメッセージ: "feat(phase2): refactor config management and document architecture"）

---

## Phase 2.2: 並行処理の責務整理 ✅

**優先度**: 🟠 中
**依存**: なし（Phase 2.1と並行可）
**目標**: アーキテクチャをドキュメント化し、保守性を向上
**ステータス**: ✅ 完了
**完了日**: 2025-12-27
**コミット**: e228b77

### タスクリスト

- [x] **P2.2-1**: `docs/` ディレクトリを作成
  ```bash
  mkdir -p docs
  ```

- [x] **P2.2-2**: `docs/ARCHITECTURE.md` を作成
  - [x] 並行処理モデルの表を記載
  - [x] データフローを図解
  - [x] 各モジュールの責務を明記

- [x] **P2.2-3**: `conversation_app.py` にコメント追加
  - [x] 音声ストリーム開始部分にコメント
  - [x] WebSocket接続部分にコメント
  - [x] メインループ部分にコメント

### 成果物
- `docs/ARCHITECTURE.md` (新規) ✅
- `conversation_app.py` (コメント追加) ✅

### 完了条件
- [x] すべてのタスクが完了
- [x] ドキュメントがレビュー可能
- [x] git commit済み（コミットメッセージ: "feat(phase2): refactor config management and document architecture"）

---

## Phase 2.3: フラグ統合とイベント駆動アーキテクチャ

**優先度**: 🔴 最高
**依存**: Phase 1.1, 1.2, 2.1 完了
**目標**: Single Source of Truth実現、制御フロー明確化
**ステータス**: ⬜ 未着手

### タスクリスト

- [ ] **P2.3-1**: `src/event_queue.py` を作成
  - [ ] `EventType` Enumを定義（AUDIO_INPUT_RECEIVED, AUDIO_DELTA_RECEIVED, RESPONSE_STARTED, RESPONSE_COMPLETED, WAKE_WORD_DETECTED, USER_SPEECH_DETECTED, CONNECTION_ESTABLISHED, CONNECTION_LOST, ERROR_OCCURRED）
  - [ ] `Event` データクラスを実装
  - [ ] `EventQueue` クラスを実装
  - 確認: `python -c "from src.event_queue import EventType; print(EventType.WAKE_WORD_DETECTED)"`

- [ ] **P2.3-2**: `conversation_app.py` からフラグを削除し、イベント駆動に移行
  - [ ] `is_playing_response`, `response_in_progress`, `interrupt_active`, `local_interrupt_enabled` を削除
  - [ ] `self.event_queue = EventQueue()` を追加
  - [ ] `_event_processor()` イベント処理ループを実装
  - [ ] `_handle_event()` イベントハンドラーを実装
  - [ ] コールバックをイベント発行に変更
  - 確認: `grep -E "(is_playing_response|response_in_progress|interrupt_active|local_interrupt_enabled)" conversation_app.py` が空

- [ ] **P2.3-3**: タスク追跡機能を実装
  - [ ] `self.tasks: set[asyncio.Task] = set()` を追加
  - [ ] `self.stop_event = asyncio.Event()` を追加
  - [ ] `_start_task()` ヘルパーメソッドを実装
  - [ ] すべてのタスク起動を `_start_task()` に変更
  - 確認: `grep -n "_start_task" conversation_app.py`

- [ ] **P2.3-4**: 順序付きシャットダウン処理を実装
  - [ ] `_cleanup()` を修正（stop_event → cancel → gather → close）
  - [ ] Ctrl+C での正常終了を確認
  - [ ] WebSocket切断時の適切なクリーンアップを確認
  - 確認: Ctrl+C でクリーンにシャットダウンすることを確認

- [ ] **P2.3-5**: 音声コールバックを軽量化
  - [ ] `audio_input_callback()` からリサンプリング処理を削除
  - [ ] イベントキューに音声データを投げるだけに簡素化
  - [ ] `_audio_processor()` タスクを作成（重い処理を別タスクで実行）
  - 確認: コールバック内の処理時間が最小化されていることを確認

- [ ] **P2.3-6**: ウェイクワード検知を別タスクに分離
  - [ ] `_wake_word_monitor()` タスクを作成
  - [ ] ウェイクワード検知時に `EventType.WAKE_WORD_DETECTED` をキューに投入
  - [ ] コールバックからウェイクワード検知ロジックを削除
  - 確認: ウェイクワードが正しく検知されることを確認

- [ ] **P2.3-7**: 動作確認
  - [ ] アプリを起動し、イベント駆動フローが正常に動作することを確認
  - [ ] ログでイベント処理が追跡可能なことを確認
  - [ ] 割り込み処理が正常に動作することを確認

### 成果物
- `src/event_queue.py` (新規)
- `conversation_app.py` (大幅修正)
- `src/audio.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] すべてのブール値フラグが削除されている
- [ ] イベント駆動アーキテクチャが正常に動作する
- [ ] git commit済み（コミットメッセージ: "feat(phase2.3): migrate to event-driven architecture and consolidate flags"）

---

## Phase 2.4: タスクライフサイクル管理の改善

**優先度**: 🔴 最高
**依存**: Phase 2.3 完了
**目標**: シャットダウン堅牢性向上、リソースリーク防止
**ステータス**: ⬜ 未着手

### タスクリスト

- [ ] **P2.4-1**: タスク追跡機能の完全実装
  - [ ] `self.tasks` によるすべてのタスクの追跡確認
  - [ ] `_start_task()` ですべてのタスクが登録されていることを確認
  - [ ] タスク完了時の自動クリーンアップ動作確認
  - 確認: `len(self.tasks)` をログ出力して追跡状況を確認

- [ ] **P2.4-2**: シャットダウン処理の検証
  - [ ] Ctrl+C でのクリーンシャットダウンを複数回テスト
  - [ ] WebSocket切断時のクリーンアップを確認
  - [ ] リソースリークがないことを確認（psutil等で確認）
  - 確認: ログで "Cleanup completed" が出力されることを確認

### 成果物
- `conversation_app.py` (修正)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] シャットダウン処理が堅牢に動作する
- [ ] git commit済み（コミットメッセージ: "feat(phase2.4): improve task lifecycle management"）

---

## Phase 2.5: 最小テストの導入

**優先度**: 🟠 中
**依存**: Phase 1.1, 2.1 完了
**目標**: 品質保証、リグレッション防止
**ステータス**: ⬜ 未着手

### タスクリスト

- [ ] **P2.5-1**: `tests/` ディレクトリを作成
  ```bash
  mkdir -p tests
  touch tests/__init__.py
  ```

- [ ] **P2.5-2**: `tests/test_state_machine.py` を作成
  - [ ] `test_valid_transitions()` を実装
  - [ ] `test_invalid_transitions()` を実装
  - [ ] `test_error_recovery()` を実装
  - 確認: `pytest tests/test_state_machine.py`

- [ ] **P2.5-3**: `tests/test_config.py` を作成
  - [ ] `test_audio_config_defaults()` を実装
  - [ ] `test_app_config_validation()` を実装
  - 確認: `pytest tests/test_config.py`

- [ ] **P2.5-4**: `tests/test_interrupt_flow.py` を作成
  - [ ] `test_wake_word_interrupt_flow()` を実装（asyncio対応）
  - [ ] モックアプリケーションを作成
  - 確認: `pytest tests/test_interrupt_flow.py`

- [ ] **P2.5-5**: テスト実行とカバレッジ確認
  - [ ] `pytest tests/` ですべてのテストが成功
  - [ ] カバレッジレポート確認（主要ロジックがカバーされていること）
  - 確認: `pytest tests/ -v`

### 成果物
- `tests/test_state_machine.py` (新規)
- `tests/test_config.py` (新規)
- `tests/test_interrupt_flow.py` (新規)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] `pytest tests/` が成功する
- [ ] git commit済み（コミットメッセージ: "feat(phase2.5): add minimal test suite"）

---

## Phase 2.6: audioop.ratecv 代替

**優先度**: 🟡 低（将来対応）
**依存**: なし
**目標**: Python 3.13対応、将来互換性
**ステータス**: ⬜ 未着手

### タスクリスト

- [ ] **P2.6-1**: リサンプリング代替実装の選定
  - [ ] Option 1: `scipy.signal.resample` の評価
  - [ ] Option 2: `soxr` の評価
  - [ ] 音質比較テスト
  - [ ] パフォーマンス比較テスト
  - 決定: どちらを採用するか決定

- [ ] **P2.6-2**: 選定した実装を適用
  - [ ] requirements.txtに依存を追加
  - [ ] `src/audio.py` のリサンプリング処理を更新
  - [ ] 音質確認（元のaudioop.ratecvと比較）
  - 確認: リサンプリングが正常に動作することを確認

- [ ] **P2.6-3**: Python 3.13環境でのテスト（オプション）
  - [ ] Python 3.13環境を構築
  - [ ] 動作確認
  - 確認: Python 3.13で正常に動作することを確認

### 成果物
- `src/audio.py` (修正)
- `requirements.txt` (更新)

### 完了条件
- [ ] すべてのタスクが完了
- [ ] リサンプリングが正常に動作する
- [ ] git commit済み（コミットメッセージ: "feat(phase2.6): replace audioop.ratecv with [scipy/soxr]"）

---

## Phase 2.7: config.py 段階的廃止計画

**優先度**: 🟡 低（段階的実施）
**依存**: Phase 2.1 完了
**目標**: 設計一貫性向上、技術的負債削減
**ステータス**: ⬜ 未着手

### タスクリスト

**フェーズ1** (Phase 2.1完了時): ✅ 完了
- [x] `src/config_models.py` 作成
- [x] `config.py` に後方互換エイリアス残存

**フェーズ2** (Phase 3完了目標):
- [ ] **P2.7-1**: 各モジュールの段階的移行
  - [ ] `conversation_app.py`: `from config import ...` → `from src.config_models import app_config` に変更
  - [ ] `src/audio.py`: 同様に移行
  - [ ] `src/realtime_client.py`: 同様に移行
  - [ ] `src/gui.py`: 同様に移行
  - [ ] `wake_word_daemon.py`: 同様に移行
  - 確認: `grep -r "from config import" --include="*.py" | grep -v ".venv"`

- [ ] **P2.7-2**: 移行ガイド作成
  - [ ] `docs/CONFIG_MIGRATION.md` を作成
  - [ ] 移行手順を記載
  - [ ] 後方互換期間を明記（Phase 3まで維持）

**フェーズ3** (Phase 4完了目標):
- [ ] **P2.7-3**: 完全移行
  - [ ] すべてのコードが `app_config` 経由でアクセス
  - [ ] `config.py` 削除（環境変数ロードのみ残す）
  - 確認: `config.py` のエイリアスが完全に削除されていることを確認

### 成果物
- `docs/CONFIG_MIGRATION.md` (新規)
- 各モジュール (修正)

### 完了条件
- [ ] フェーズ2のタスクが完了（Phase 3完了時）
- [ ] フェーズ3のタスクが完了（Phase 4完了時）
- [ ] git commit済み（各フェーズごとにコミット）

---

## Phase 3.1: 割り込み処理の改善

**優先度**: 🟡 中低
**依存**: Phase 2.3, 2.4 完了
**目標**: ユーザー体験を向上（応答性改善）
**ステータス**: ⬜ 未着手

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

| 日付         | 更新内容                      | 更新者    |
| ---------- | ------------------------- | ------ |
| 2025-12-27 | 初版作成                      | Claude |
| 2025-12-27 | Phase 1 完了（状態管理・ロギング・例外処理） | Claude |
| 2025-12-27 | Phase 2 完了（設定管理・アーキテクチャ文書） | Claude |
| 2025-12-28 | Phase 1-2 完了のステータス更新       | Claude |

---

## 📝 メモ・課題

### 完了した主要成果物
- ✅ 状態管理システム（AppState Enum + 遷移検証）
- ✅ ロギングインフラ（日次ローテーション、構造化ログ）
- ✅ 例外処理・自動復旧機能
- ✅ Pydantic設定管理
- ✅ アーキテクチャドキュメント
- ✅ テストチェックリスト

### 進行中の課題
- （なし）

### 検討事項
- Phase 3（機能拡張）への着手タイミング
- Phase 4（プロダクション対応）の優先順位

### 次回作業予定
- Phase 3.1（割り込み処理改善）または Phase 4（systemd化）を検討

---

## 🎯 次のアクション

### オプション1: Phase 3（機能拡張）に進む
1. **Phase 3.1: 割り込み処理の改善**
   - 音声の即座停止機能
   - フィードバック音の追加

2. **Phase 3.2: 人格切替機能**
   - 子供向けモードの実装
   - パーソナリティ設定の拡張

### オプション2: Phase 4（プロダクション対応）に進む
1. **Phase 4.1: パッケージ化**
   - pyproject.toml作成
   - pip installable化

2. **Phase 4.2: systemd対応**
   - サービスファイル作成
   - 自動起動設定

### 推奨アクション
外部レビューフィードバックを反映した結果、以下の優先順位を推奨:
1. **Phase 2.3（フラグ統合とイベント駆動アーキテクチャ）** - 🔴 最優先
   - Single Source of Truthの実現
   - 制御フロー明確化
2. **Phase 2.4（タスクライフサイクル管理）** - 🔴 高優先度
   - シャットダウン堅牢性向上
3. **Phase 2.5（最小テスト導入）** - 🟠 中優先度
   - 品質保証の基盤整備
4. その後、Phase 3（機能拡張）または Phase 4（プロダクション対応）へ進む

---

## 📝 更新履歴

| 日付         | 変更内容                                     | 備考                  |
| ---------- | ---------------------------------------- | ------------------- |
| 2025-12-27 | 初版作成                                     | Phase 1-2のタスク定義     |
| 2025-12-28 | Phase 1-2完了マーク、成果物チェックリスト更新              | 完了コミット記録            |
| 2025-12-28 | Phase 2.3-2.7 追加（外部レビューフィードバック反映）        | アーキテクチャ改善タスク（20件追加） |
|            | - フラグ統合とイベント駆動アーキテクチャ（2.3）             |                     |
|            | - タスクライフサイクル管理の改善（2.4）                  |                     |
|            | - 最小テストの導入（2.5）                         |                     |
|            | - audioop.ratecv代替（2.6）                  |                     |
|            | - config.py段階的廃止計画（2.7）                 |                     |
| 2025-12-28 | 総合進捗更新: 29/37 (78%) → 29/57 (51%)       | 新規タスク追加により進捗率変動     |
