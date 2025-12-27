# リファクタリング クイックスタートガイド

**作成日**: 2025-12-27
**対象者**: talk_system のリファクタリングを開始する開発者

このガイドは、`REFACTORING_PLAN.md` と `TASK_TRACKER.md` を元に、**今すぐリファクタリングを始める**ための最短手順を提供します。

---

## 🚀 今日から始める 3ステップ

### ステップ1: 環境準備（5分）

```bash
cd /home/yutapi5/Programs/talk_system

# 1. 現在の動作コードをバックアップ
git checkout -b backup/pre-refactor-$(date +%Y%m%d)
git checkout main

# 2. 開発ブランチを作成
git checkout -b feature/phase1-foundation

# 3. 開発依存関係をインストール
.venv/bin/pip install pytest pytest-asyncio black mypy
```

**確認**:
```bash
git branch --show-current  # feature/phase1-foundation と表示されるはず
.venv/bin/pip list | grep pytest  # pytest がインストールされているはず
```

---

### ステップ2: Phase 1.1（状態管理）を実装（30分）

#### 2-1. 状態管理モジュールを作成

**ファイル**: `src/state_machine.py`

```python
"""アプリケーション状態管理"""

from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)


class AppState(Enum):
    """アプリケーション状態定義"""
    IDLE = auto()        # 待機中（ウェイクワード待ち）
    LISTENING = auto()   # 聞いている（ユーザー音声受付中）
    PROCESSING = auto()  # 考え中（AI応答生成中）
    SPEAKING = auto()    # 発話中（音声出力中）
    ERROR = auto()       # エラー状態（復旧処理中）


class StateTransition:
    """状態遷移管理"""

    # 許可される状態遷移の定義
    ALLOWED_TRANSITIONS = {
        AppState.IDLE: {AppState.LISTENING, AppState.ERROR},
        AppState.LISTENING: {AppState.PROCESSING, AppState.ERROR},
        AppState.PROCESSING: {AppState.SPEAKING, AppState.ERROR},
        AppState.SPEAKING: {AppState.LISTENING, AppState.PROCESSING, AppState.ERROR},
        AppState.ERROR: {AppState.IDLE, AppState.LISTENING}
    }

    @classmethod
    def is_valid_transition(cls, from_state: AppState, to_state: AppState) -> bool:
        """
        状態遷移の妥当性チェック

        Args:
            from_state: 現在の状態
            to_state: 遷移先の状態

        Returns:
            True: 遷移可能, False: 遷移不可
        """
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def get_allowed_transitions(cls, from_state: AppState) -> set:
        """
        指定した状態から遷移可能な状態の一覧を取得

        Args:
            from_state: 現在の状態

        Returns:
            遷移可能な状態のセット
        """
        return cls.ALLOWED_TRANSITIONS.get(from_state, set())
```

**確認**:
```bash
python -c "from src.state_machine import AppState, StateTransition; print(AppState.LISTENING); print(StateTransition.is_valid_transition(AppState.IDLE, AppState.LISTENING))"
# 出力: AppState.LISTENING
#       True
```

---

#### 2-2. conversation_app.py を修正

**修正箇所1**: インポート部分（ファイル先頭）

```python
# 追加
from src.state_machine import AppState, StateTransition
import logging
```

**修正箇所2**: `__init__()` メソッド

```python
# 修正前
self.state = STATE_LISTENING

# 修正後
self.logger = logging.getLogger(__name__)
self.state = AppState.LISTENING
```

**修正箇所3**: 状態遷移メソッドを追加（`__init__()` の後に挿入）

```python
def set_state(self, new_state: AppState):
    """
    状態遷移（検証付き）

    Args:
        new_state: 遷移先の状態
    """
    if StateTransition.is_valid_transition(self.state, new_state):
        old_state = self.state
        self.state = new_state
        self.logger.info(f"State transition: {old_state.name} → {new_state.name}")

        # GUIに状態を反映（既存のマッピング）
        state_map = {
            AppState.IDLE: 0,
            AppState.LISTENING: 1,
            AppState.PROCESSING: 2,
            AppState.SPEAKING: 3,
            AppState.ERROR: 0
        }
        if new_state in state_map:
            self.gui.set_state(state_map[new_state])
    else:
        self.logger.warning(
            f"Invalid state transition: {self.state.name} → {new_state.name} "
            f"(allowed: {[s.name for s in StateTransition.get_allowed_transitions(self.state)]})"
        )
```

**修正箇所4**: 状態変更箇所を更新

```bash
# 検索: conversation_app.py 内の self.gui.set_state() 呼び出し箇所を確認
grep -n "self.gui.set_state" conversation_app.py
```

以下のように変更:

```python
# 修正前（例: 行125付近）
self.gui.set_state(1)  # LISTENING

# 修正後
self.set_state(AppState.LISTENING)
```

すべての `self.gui.set_state()` を `self.set_state()` に置き換えてください。

**修正箇所5**: 定数定義を削除

```python
# 削除（ファイル先頭付近）
STATE_LISTENING = "LISTENING"
STATE_PROCESSING = "PROCESSING"
STATE_SPEAKING = "SPEAKING"
```

**確認**:
```bash
# 構文チェック
python -m py_compile conversation_app.py

# 状態遷移が正しく動作するか確認（軽く起動テスト）
timeout 5 .venv/bin/python conversation_app.py || true
```

---

### ステップ3: コミット（5分）

```bash
# 変更をステージング
git add src/state_machine.py conversation_app.py

# コミット
git commit -m "feat(phase1): implement explicit state machine

- Add AppState enum and StateTransition validator
- Replace implicit state management with explicit transitions
- Add state transition logging
- Update conversation_app to use new state machine

Refs: REFACTORING_PLAN.md Phase 1.1"

# 確認
git log --oneline -1
git diff main --stat
```

---

## 📋 チェックリスト

Phase 1.1 が完了したら、以下を確認してください：

- [ ] `src/state_machine.py` が作成されている
- [ ] `conversation_app.py` で `AppState` を使用している
- [ ] すべての状態変更が `set_state()` を経由している
- [ ] 定数定義（`STATE_LISTENING` 等）が削除されている
- [ ] アプリが起動できる（エラーが出ない）
- [ ] git commit が完了している

---

## 🎯 次のステップ

Phase 1.1 が完了したら、次は **Phase 1.2（ロギング基盤導入）** に進みましょう。

### Phase 1.2 クイックスタート

#### 1. ロギング設定モジュールを作成

**ファイル**: `src/logging_config.py`

```python
"""ロギング設定"""

import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir: str = "logs", level: int = logging.INFO):
    """
    ロギング設定を初期化

    Args:
        log_dir: ログファイル出力ディレクトリ
        level: ログレベル（デフォルト: INFO）

    Returns:
        ルートロガー
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ファイルハンドラー（日次ローテーション）
    file_handler = TimedRotatingFileHandler(
        log_path / "talk_system.log",
        when='midnight',
        backupCount=7  # 7日分保持
    )
    file_handler.setFormatter(formatter)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
```

#### 2. logs/ ディレクトリを作成

```bash
mkdir -p logs
echo "logs/*.log" >> .gitignore
git add .gitignore
```

#### 3. conversation_app.py を修正

**ファイル先頭に追加**:

```python
from src.logging_config import setup_logging

# ロギング初期化（モジュールレベル）
setup_logging()
logger = logging.getLogger(__name__)
```

**print文を置き換え**:

```python
# 修正前
print("Conversation App Started")

# 修正後
logger.info("Conversation App Started")
```

すべての `print()` を適切なログレベルに変更:
- `print("...")` → `logger.info("...")`
- エラーメッセージ → `logger.error("...")`
- デバッグ情報 → `logger.debug("...")`

#### 4. 他のファイルも同様に修正

```bash
# 対象ファイル
# - src/realtime_client.py
# - src/audio.py
# - src/gui.py
# - wake_word_daemon.py
```

各ファイルで:

```python
import logging
logger = logging.getLogger(__name__)

# print() を logger.info() / logger.error() に置き換え
```

#### 5. 確認・コミット

```bash
# ログが出力されることを確認
timeout 5 .venv/bin/python conversation_app.py || true
ls -lh logs/talk_system.log
tail logs/talk_system.log

# コミット
git add src/logging_config.py logs/ .gitignore conversation_app.py src/*.py wake_word_daemon.py
git commit -m "feat(phase1): introduce logging infrastructure

- Add logging_config module with file/console handlers
- Replace all print() with logger calls
- Add log directory with .gitignore
- Configure daily log rotation (7 days retention)

Refs: REFACTORING_PLAN.md Phase 1.2"
```

---

## 🔄 繰り返しパターン

以降の Phase も同じパターンで進めます：

1. **実装**: REFACTORING_PLAN.md の仕様に従ってコードを修正
2. **確認**: 動作確認・テスト実行
3. **コミット**: git commit with descriptive message
4. **次へ**: TASK_TRACKER.md のチェックボックスを更新して次のタスクへ

---

## 💡 トラブルシューティング

### Q1: 状態遷移エラーが出る

**症状**: `Invalid state transition: LISTENING → IDLE` のような警告が出る

**対処**:
1. `StateTransition.ALLOWED_TRANSITIONS` を確認
2. 遷移ロジックが正しいか確認
3. 必要に応じて許可する遷移を追加

---

### Q2: ログが出力されない

**症状**: `logs/talk_system.log` が生成されない

**対処**:
```bash
# ディレクトリ存在確認
ls -ld logs/

# パーミッション確認
ls -l logs/

# setup_logging() が呼ばれているか確認
grep -n "setup_logging" conversation_app.py
```

---

### Q3: import エラーが出る

**症状**: `ModuleNotFoundError: No module named 'src.state_machine'`

**対処**:
```bash
# Pythonパスを確認
cd /home/yutapi5/Programs/talk_system
python -c "import sys; print(sys.path)"

# 仮想環境が有効か確認
which python  # .venv/bin/python と表示されるべき

# ファイルが存在するか確認
ls src/state_machine.py
```

---

## 📚 参考資料

- **メイン計画書**: `REFACTORING_PLAN.md` - 全体設計と各Phaseの詳細
- **タスク管理**: `TASK_TRACKER.md` - チェックリストと進捗管理
- **このガイド**: `QUICKSTART_REFACTORING.md` - 実践的な手順

---

## 🎓 推奨作業フロー

### 1日目（Phase 1.1 + 1.2）
- [ ] 環境準備
- [ ] Phase 1.1 実装（状態管理）
- [ ] Phase 1.2 実装（ロギング）
- [ ] 動作確認

### 2日目（Phase 1.3）
- [ ] Phase 1.3 実装（例外処理）
- [ ] 統合テスト
- [ ] Phase 1 完了、mainにマージ

### 3日目（Phase 2）
- [ ] Phase 2.1 実装（設定管理）
- [ ] Phase 2.2 実装（ドキュメント）

### 4日目以降
- [ ] Phase 3: 機能拡張
- [ ] Phase 4: パッケージ化・systemd対応

---

## 🚦 ステータス更新

リファクタリング作業中は、`TASK_TRACKER.md` のチェックボックスを更新してください：

```markdown
- [x] **P1.1-1**: `src/state_machine.py` を作成  ✅ 完了
- [x] **P1.1-2**: `conversation_app.py` に状態遷移ロジックを組み込み  ✅ 完了
- [ ] **P1.1-3**: `gui.py` の状態表示を `AppState` に対応  🚧 進行中
```

---

## 📞 サポート

不明点があれば、以下を確認してください：

1. `REFACTORING_PLAN.md` の該当Phase
2. `TASK_TRACKER.md` のチェックリスト
3. このガイドのトラブルシューティング

---

**Happy Refactoring!** 🎉
