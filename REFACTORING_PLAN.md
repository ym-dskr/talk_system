# talk_system リファクタリング計画書

**作成日**: 2025-12-27
**対象**: talk_system (Raspberry Pi 常駐型対話エージェント)
**目標**: プロトタイプから本格稼働システムへの移行

---

## 📋 総評・現状分析

### ✅ 優れている点

1. **責務分離の意識が明確**
   - `conversation_app.py` - オーケストレーション層
   - `src/realtime_client.py` - OpenAI Realtime API通信
   - `src/audio.py` - 音声I/O
   - `src/gui.py` - UI表示
   - `src/animation/*` - キャラクター表現層

2. **イベント駆動設計**
   - コールバックベースのアーキテクチャ
   - `on_audio_delta`, `on_response_done` 等のイベント分離
   - 拡張性が高い設計

3. **Live2D風アニメーション構造**
   - 目/口/手/胴を個別Animator化
   - AnimationControllerで統合
   - CharacterRendererが描画責務のみ担当

### ⚠️ 改善が必要な点

1. **状態管理が暗黙的**（優先度: 🔴 高）
   - 定数は定義されているが状態遷移ロジックが散在
   - デバッグ困難、割り込み処理の破綻リスク

2. **例外・復旧処理が弱い**（優先度: 🔴 高）
   - マイク初期化失敗時の対応不十分
   - WebSocket切断時の自動再接続なし
   - 常駐プロセスとしては致命的

3. **async/thread責務が曖昧**（優先度: 🟠 中）
   - 音声、WebSocket、UIの並行処理が整理されていない
   - 将来的な保守性リスク

4. **設定管理の拡張性**（優先度: 🟠 中）
   - `config.py` が肥大化する可能性
   - 型安全性・補完サポートなし

5. **パッケージ化されていない**（優先度: 🟡 低）
   - スクリプト集合体
   - テストが書きづらい、再利用性低い

---

## 🎯 リファクタリング方針

### 段階的アプローチ

**Phase 1**: 基盤強化（状態管理 + ログ + 例外処理）
**Phase 2**: 設計改善（設定管理 + 並行処理整理）
**Phase 3**: 機能拡張（割り込み改善 + 人格切替）
**Phase 4**: 長期運用対応（パッケージ化 + systemd対応）

### 互換性ポリシー

- 既存の動作を壊さない
- 段階的にマイグレーション可能
- 各Phaseは独立してマージ可能

---

## 📦 Phase 1: 基盤強化（状態管理 + ログ + 例外処理）

**目標**: システムの安定性を向上し、デバッグ可能性を確保する
**期間目安**: 実装 + テスト（タスクベース、時間見積もりなし）
**優先度**: 🔴 最重要

### 1.1 状態管理の明示化

#### 実装内容

**ファイル**: `src/state_machine.py` (新規作成)

```python
from enum import Enum, auto

class AppState(Enum):
    """アプリケーション状態定義"""
    IDLE = auto()        # 待機中（ウェイクワード待ち）
    LISTENING = auto()   # 聞いている（ユーザー音声受付中）
    PROCESSING = auto()  # 考え中（AI応答生成中）
    SPEAKING = auto()    # 発話中（音声出力中）
    ERROR = auto()       # エラー状態（復旧処理中）

class StateTransition:
    """状態遷移管理"""
    ALLOWED_TRANSITIONS = {
        AppState.IDLE: {AppState.LISTENING},
        AppState.LISTENING: {AppState.PROCESSING, AppState.ERROR},
        AppState.PROCESSING: {AppState.SPEAKING, AppState.ERROR},
        AppState.SPEAKING: {AppState.LISTENING, AppState.PROCESSING, AppState.ERROR},
        AppState.ERROR: {AppState.IDLE, AppState.LISTENING}
    }

    @classmethod
    def is_valid_transition(cls, from_state: AppState, to_state: AppState) -> bool:
        """状態遷移の妥当性チェック"""
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())
```

**ファイル**: `conversation_app.py` (修正)

```python
# 修正前
self.state = STATE_LISTENING

# 修正後
from src.state_machine import AppState, StateTransition

class ConversationApp:
    def __init__(self):
        self.state = AppState.LISTENING

    def set_state(self, new_state: AppState):
        """状態遷移（検証付き）"""
        if StateTransition.is_valid_transition(self.state, new_state):
            logger.info(f"State: {self.state.name} → {new_state.name}")
            self.state = new_state
        else:
            logger.warning(f"Invalid transition: {self.state.name} → {new_state.name}")
```

#### 成果物チェックリスト

- [ ] `src/state_machine.py` 作成
- [ ] `conversation_app.py` に状態遷移ロジック組み込み
- [ ] `gui.py` の状態表示を `AppState` に対応
- [ ] 状態遷移ログが全て出力されることを確認

---

### 1.2 ロギング基盤導入

#### 実装内容

**ファイル**: `src/logging_config.py` (新規作成)

```python
import logging
import sys
from pathlib import Path

def setup_logging(log_dir: str = "logs", level: int = logging.INFO):
    """ロギング設定を初期化"""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ファイルハンドラー（日次ローテーション）
    from logging.handlers import TimedRotatingFileHandler
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

**ファイル**: `conversation_app.py` (修正)

```python
# 修正前
print("Conversation App Started")

# 修正後
import logging
from src.logging_config import setup_logging

logger = setup_logging()

class ConversationApp:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def run(self):
        self.logger.info("Conversation App Started")
```

#### 成果物チェックリスト

- [ ] `src/logging_config.py` 作成
- [ ] 全ての `print()` を `logger.info/debug/error()` に置換
- [ ] `logs/` ディレクトリに日次ログが出力されることを確認
- [ ] エラー発生時にスタックトレースがログファイルに記録されることを確認

---

### 1.3 例外処理・復旧ロジック

#### 実装内容

**ファイル**: `src/audio.py` (修正)

```python
# 修正前
def start_stream(self, input_callback=None):
    self.stream = self.pyaudio.open(...)

# 修正後
import logging

class AudioHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start_stream(self, input_callback=None):
        """音声ストリーム開始（エラーハンドリング付き）"""
        try:
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=INPUT_CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=INPUT_DEVICE_INDEX,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=input_callback
            )
            self.logger.info(f"Audio stream started (device: {INPUT_DEVICE_INDEX})")
        except OSError as e:
            self.logger.error(f"Audio device initialization failed: {e}")
            # デバイス一覧を表示して診断を支援
            self._list_audio_devices()
            raise RuntimeError("Audio device not available") from e
        except Exception as e:
            self.logger.exception("Unexpected error during audio stream start")
            raise

    def _list_audio_devices(self):
        """利用可能なオーディオデバイスを列挙"""
        info = self.pyaudio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        self.logger.info("Available audio devices:")
        for i in range(num_devices):
            device_info = self.pyaudio.get_device_info_by_host_api_device_index(0, i)
            self.logger.info(f"  [{i}] {device_info.get('name')}")
```

**ファイル**: `src/realtime_client.py` (修正)

```python
# WebSocket自動再接続機能を追加

class RealtimeClient:
    def __init__(self, ..., max_reconnect_attempts=3):
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = 2.0  # 秒
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """OpenAI Realtime APIに接続（自動再接続付き）"""
        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                await self._connect_internal()
                self.logger.info(f"Connected to Realtime API (attempt {attempt})")
                return
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt} failed: {e}")
                if attempt < self.max_reconnect_attempts:
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    raise RuntimeError("Failed to connect after max attempts") from e

    async def _connect_internal(self):
        """内部接続処理（例外を上位に伝播）"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        url = f"{REALTIME_URL}?model={REALTIME_MODEL}"
        self.ws = await websockets.connect(url, additional_headers=headers)
        # ... セッション初期化
```

#### 成果物チェックリスト

- [ ] `audio.py` にデバイス診断機能追加
- [ ] `realtime_client.py` に自動再接続ロジック追加
- [ ] マイク未接続状態で起動した場合のエラーメッセージ確認
- [ ] WebSocket切断→再接続の動作確認

---

### 1.4 Phase 1 統合テスト

#### テスト項目

1. **状態遷移テスト**
   - [ ] IDLE → LISTENING → PROCESSING → SPEAKING の正常フロー
   - [ ] 不正な状態遷移が警告ログに記録される

2. **ログ出力テスト**
   - [ ] `logs/talk_system.log` にすべてのイベントが記録される
   - [ ] エラー時にスタックトレースが出力される

3. **復旧テスト**
   - [ ] マイクを接続せずに起動 → エラーメッセージとデバイス一覧が表示される
   - [ ] WebSocket切断後、自動再接続が試行される

---

## 📦 Phase 2: 設計改善（設定管理 + 並行処理整理）

**目標**: 保守性と拡張性を向上させる
**優先度**: 🟠 中

### 2.1 設定管理のリファクタリング

#### 実装内容

**ファイル**: `src/config_models.py` (新規作成)

```python
from pydantic import BaseModel, Field
from typing import Optional

class AudioConfig(BaseModel):
    """音声設定"""
    sample_rate: int = Field(default=24000, description="サンプルレート（Hz）")
    input_channels: int = Field(default=1, description="入力チャンネル数")
    output_channels: int = Field(default=2, description="出力チャンネル数")
    chunk_size: int = Field(default=1024, description="バッファサイズ")
    input_device_index: Optional[int] = None
    output_device_index: Optional[int] = None
    input_device_name: Optional[str] = None
    output_device_name: Optional[str] = None

class RealtimeConfig(BaseModel):
    """Realtime API設定"""
    model: str = "gpt-4o-mini-realtime-preview"
    url: str = "wss://api.openai.com/v1/realtime"
    max_reconnect_attempts: int = 3
    reconnect_delay: float = 2.0

class AppConfig(BaseModel):
    """アプリケーション全体設定"""
    audio: AudioConfig = AudioConfig()
    realtime: RealtimeConfig = RealtimeConfig()
    openai_api_key: str
    picovoice_access_key: str
    inactivity_timeout: float = 180.0

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
```

**ファイル**: `config.py` (修正)

```python
# 修正前
SAMPLE_RATE = 24000
INPUT_DEVICE_INDEX = int(os.getenv("INPUT_DEVICE_INDEX", -1))

# 修正後
from src.config_models import AppConfig
import os

# .env から読み込み
app_config = AppConfig(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    picovoice_access_key=os.getenv("PICOVOICE_ACCESS_KEY"),
)

# 後方互換のためのエイリアス
SAMPLE_RATE = app_config.audio.sample_rate
INPUT_DEVICE_INDEX = app_config.audio.input_device_index
```

#### 成果物チェックリスト

- [ ] `src/config_models.py` 作成
- [ ] 既存の `config.py` を段階的に移行
- [ ] 型ヒントによる補完が効くことを確認
- [ ] `.env` の変更が正しく反映されることを確認

---

### 2.2 並行処理の責務整理

#### 実装内容

**ファイル**: `docs/ARCHITECTURE.md` (新規作成)

```markdown
# talk_system アーキテクチャ

## 並行処理モデル

| 処理                | 実行形態         | 理由                          |
| ----------------- | ------------ | --------------------------- |
| 音声入力              | Thread       | PyAudioコールバック（ブロッキングI/O）    |
| 音声出力              | Thread       | PyAudio再生（ブロッキングI/O）        |
| Realtime WS       | asyncio Task | 非同期I/O、イベントループと親和性高い       |
| GUI / pygame      | メインスレッド      | pygameはメインスレッドでのみ動作可能       |
| ウェイクワード検知（ローカル） | Thread       | Porcupine処理（CPU集約、イベントループに影響なし） |

## データフロー

1. マイク → AudioHandler (Thread) → asyncio.Queue → RealtimeClient (WS)
2. RealtimeClient → audio_queue (asyncio) → AudioHandler (Thread) → スピーカー
3. RealtimeClient → GUIHandler (メイン) → pygame描画
```

**ファイル**: `conversation_app.py` (コメント追加)

```python
class ConversationApp:
    async def run(self):
        # ================================================================================
        # 音声ストリームの開始（Thread）
        # PyAudioのコールバックは別スレッドで実行される
        # ================================================================================
        self.audio.start_stream(input_callback=self.audio_input_callback)
        asyncio.create_task(self.audio.record_loop())

        # ================================================================================
        # OpenAI Realtime APIに接続（asyncio Task）
        # WebSocketはイベントループで非同期処理される
        # ================================================================================
        await self.client.connect()

        # ================================================================================
        # メインループ（メインスレッド）
        # GUIイベント処理はpygameの制約によりメインスレッドで実行
        # ================================================================================
        while self.gui.running:
            self.gui.update()  # pygameイベント処理（メインスレッドのみ可）
            await asyncio.sleep(0.001)
```

#### 成果物チェックリスト

- [ ] `docs/ARCHITECTURE.md` 作成
- [ ] 各並行処理の責務を明確化
- [ ] コードコメントを追加して設計意図を記録

---

### 2.3 フラグ統合とイベント駆動アーキテクチャ

**背景**: 現状の課題として、状態機械（AppState）が導入されているにも関わらず、複数のブール値フラグ（`is_playing_response`, `response_in_progress`, `interrupt_active`, `local_interrupt_enabled`）が並存し、「単一の信頼できる情報源（Single Source of Truth）」という設計原則が弱まっています。また、コールバックベースの設計により制御フローが追跡困難になっています。

#### 実装内容

**ファイル**: `src/event_queue.py` (新規作成)

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class EventType(Enum):
    """イベント種別定義"""
    AUDIO_INPUT_RECEIVED = auto()      # マイクから音声受信
    AUDIO_DELTA_RECEIVED = auto()      # AI応答音声チャンク受信
    RESPONSE_STARTED = auto()          # AI応答開始
    RESPONSE_COMPLETED = auto()        # AI応答完了
    WAKE_WORD_DETECTED = auto()        # ウェイクワード検知（割り込み）
    USER_SPEECH_DETECTED = auto()      # ユーザー発話開始検知
    CONNECTION_ESTABLISHED = auto()    # WebSocket接続確立
    CONNECTION_LOST = auto()           # WebSocket切断
    ERROR_OCCURRED = auto()            # エラー発生

@dataclass
class Event:
    """イベントデータ"""
    type: EventType
    data: Optional[Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()

class EventQueue:
    """イベントキュー管理"""
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)

    async def put(self, event: Event):
        """イベントをキューに追加"""
        await self.queue.put(event)
        self.logger.debug(f"Event queued: {event.type.name}")

    async def get(self) -> Event:
        """イベントを取得（ブロッキング）"""
        return await self.queue.get()

    def empty(self) -> bool:
        """キューが空かチェック"""
        return self.queue.empty()
```

**ファイル**: `conversation_app.py` (大幅修正)

```python
from src.event_queue import EventQueue, Event, EventType
from src.state_machine import AppState, StateTransition

class ConversationApp:
    def __init__(self):
        self.state = AppState.IDLE
        self.event_queue = EventQueue()

        # ❌ 削除するフラグ（状態機械に統合）
        # self.is_playing_response = False
        # self.response_in_progress = False
        # self.interrupt_active = False
        # self.local_interrupt_enabled = False

        # ✅ タスク管理（適切なライフサイクル管理）
        self.tasks: set[asyncio.Task] = set()
        self.stop_event = asyncio.Event()

        self.logger = logging.getLogger(__name__)

    async def run(self):
        """メインイベントループ"""
        # タスク起動
        self._start_task(self._event_processor())
        self._start_task(self._audio_record_loop())
        self._start_task(self._wake_word_monitor())
        self._start_task(self._websocket_receiver())

        # メインループ（GUI更新）
        while self.gui.running and not self.stop_event.is_set():
            self.gui.update()
            await asyncio.sleep(0.001)

        # クリーンアップ
        await self._cleanup()

    def _start_task(self, coro):
        """タスクを起動して追跡"""
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def _event_processor(self):
        """イベント処理ループ（中央制御）"""
        while not self.stop_event.is_set():
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=0.1
                )
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue

    async def _handle_event(self, event: Event):
        """イベント種別に応じた処理"""
        self.logger.debug(f"Processing event: {event.type.name} in state {self.state.name}")

        if event.type == EventType.WAKE_WORD_DETECTED:
            # 割り込み処理（SPEAKING中のみ有効）
            if self.state == AppState.SPEAKING:
                self.logger.info("Wake word interrupt detected")
                await self._execute_interrupt()
                self.set_state(AppState.LISTENING)

        elif event.type == EventType.RESPONSE_STARTED:
            if self.state == AppState.PROCESSING:
                self.set_state(AppState.SPEAKING)

        elif event.type == EventType.RESPONSE_COMPLETED:
            if self.state == AppState.SPEAKING:
                self.set_state(AppState.LISTENING)

        elif event.type == EventType.AUDIO_DELTA_RECEIVED:
            # 音声再生キューに追加
            if self.state == AppState.SPEAKING:
                await self.audio.enqueue_playback(event.data)

        # ... 他のイベント処理

    async def _cleanup(self):
        """シャットダウン処理（順序付き）"""
        self.logger.info("Starting cleanup...")

        # 1. 停止シグナル設定
        self.stop_event.set()

        # 2. タスクキャンセル
        for task in self.tasks:
            task.cancel()

        # 3. タスク完了待機
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # 4. リソース解放
        if self.client.ws:
            await self.client.disconnect()
        self.audio.terminate()

        self.logger.info("Cleanup completed")
```

**ファイル**: `src/audio.py` (修正: コールバックからイベントキューへ)

```python
class AudioHandler:
    def __init__(self, event_queue: EventQueue):
        self.event_queue = event_queue
        self.resample_buffer = bytearray()  # リサンプリングバッファ

    def audio_input_callback(self, in_data, frame_count, time_info, status):
        """音声入力コールバック（軽量化）"""
        # ❌ 重い処理をコールバック内で実行しない
        # ✅ イベントキューに投げて別タスクで処理
        asyncio.create_task(
            self.event_queue.put(Event(EventType.AUDIO_INPUT_RECEIVED, in_data))
        )
        return (None, pyaudio.paContinue)

    async def _audio_processor(self):
        """音声処理タスク（リサンプリング、ウェイクワード検知）"""
        while not self.stop_event.is_set():
            event = await self.event_queue.get()
            if event.type == EventType.AUDIO_INPUT_RECEIVED:
                # リサンプリング処理（重い）
                resampled = self._resample(event.data)

                # LISTENING状態の場合のみAPI送信
                if self.app.state == AppState.LISTENING:
                    await self.client.send_audio(resampled)
```

#### 成果物チェックリスト

- [ ] `src/event_queue.py` 作成
- [ ] `conversation_app.py` からフラグ削除（`is_playing_response`, `response_in_progress`, `interrupt_active`, `local_interrupt_enabled`）
- [ ] イベント駆動アーキテクチャへの移行完了
- [ ] タスク追跡機能実装（`self.tasks: set[asyncio.Task]`）
- [ ] 順序付きシャットダウン処理実装（stop_event → cancel → gather → close）
- [ ] 音声コールバック軽量化（重い処理を別タスクへ移動）
- [ ] ウェイクワード検知を別タスクに分離

---

### 2.4 タスクライフサイクル管理の改善

#### 実装内容

**問題点**: 現状の `cleanup()` はリソース解放のみで、実行中タスクの適切なキャンセルがない。

**改善策**:
1. 全asyncioタスクを `self.tasks: set[asyncio.Task]` で追跡
2. シャットダウン時に順序付きキャンセル（stop_event → cancel → gather → close）
3. タスク完了時の自動クリーンアップ

上記2.3のコード例に含まれています。

#### 成果物チェックリスト

- [ ] `self.tasks` によるタスク追跡実装
- [ ] `_start_task()` ヘルパーメソッド実装
- [ ] `_cleanup()` の順序付きシャットダウン実装
- [ ] Ctrl+C での正常終了確認
- [ ] WebSocket切断時の適切なクリーンアップ確認

---

### 2.5 最小テストの導入

#### 実装内容

**ファイル**: `tests/test_state_machine.py` (新規作成)

```python
import pytest
from src.state_machine import AppState, StateTransition

def test_valid_transitions():
    """有効な状態遷移のテスト"""
    assert StateTransition.is_valid_transition(AppState.IDLE, AppState.LISTENING)
    assert StateTransition.is_valid_transition(AppState.LISTENING, AppState.PROCESSING)
    assert StateTransition.is_valid_transition(AppState.PROCESSING, AppState.SPEAKING)
    assert StateTransition.is_valid_transition(AppState.SPEAKING, AppState.LISTENING)

def test_invalid_transitions():
    """無効な状態遷移のテスト"""
    assert not StateTransition.is_valid_transition(AppState.IDLE, AppState.SPEAKING)
    assert not StateTransition.is_valid_transition(AppState.LISTENING, AppState.SPEAKING)
    assert not StateTransition.is_valid_transition(AppState.PROCESSING, AppState.LISTENING)

def test_error_recovery():
    """エラーからの復旧遷移テスト"""
    assert StateTransition.is_valid_transition(AppState.ERROR, AppState.IDLE)
    assert StateTransition.is_valid_transition(AppState.ERROR, AppState.LISTENING)
    assert not StateTransition.is_valid_transition(AppState.ERROR, AppState.SPEAKING)
```

**ファイル**: `tests/test_config.py` (新規作成)

```python
import pytest
from pydantic import ValidationError
from src.config_models import AppConfig, AudioConfig

def test_audio_config_defaults():
    """音声設定のデフォルト値テスト"""
    config = AudioConfig()
    assert config.sample_rate == 24000
    assert config.input_channels == 1
    assert config.output_channels == 2

def test_app_config_validation():
    """必須フィールドバリデーションテスト"""
    with pytest.raises(ValidationError):
        # API キーが必須
        AppConfig()

    # 正常なケース
    config = AppConfig(
        openai_api_key="test_key",
        picovoice_access_key="test_key"
    )
    assert config.openai_api_key == "test_key"
```

**ファイル**: `tests/test_interrupt_flow.py` (新規作成)

```python
import pytest
import asyncio
from src.event_queue import EventQueue, Event, EventType
from src.state_machine import AppState

@pytest.mark.asyncio
async def test_wake_word_interrupt_flow():
    """ウェイクワード割り込みフローのテスト"""
    # テスト用アプリケーションインスタンス
    app = MockConversationApp()
    app.state = AppState.SPEAKING

    # ウェイクワードイベント送信
    await app.event_queue.put(Event(EventType.WAKE_WORD_DETECTED))

    # イベント処理待機
    await asyncio.sleep(0.1)

    # SPEAKING → LISTENING への遷移確認
    assert app.state == AppState.LISTENING
```

#### 成果物チェックリスト

- [ ] `tests/test_state_machine.py` 作成
- [ ] `tests/test_config.py` 作成
- [ ] `tests/test_interrupt_flow.py` 作成
- [ ] `pytest tests/` で全テスト成功
- [ ] カバレッジ確認（最低でも主要ロジックがカバーされていること）

---

### 2.6 将来対応: audioop.ratecv 代替

**背景**: Python 3.13 で `audioop` モジュールが削除予定。現在使用している `audioop.ratecv()` のリサンプリング処理に代替実装が必要。

#### 実装内容

**オプション1**: `scipy.signal.resample` (高品質、依存追加)

```python
# requirements.txt に追加
scipy>=1.11.0

# src/audio.py
import numpy as np
from scipy import signal

def resample_audio(data: bytes, src_rate: int, dst_rate: int) -> bytes:
    """scipyベースのリサンプリング"""
    # bytesをnumpy配列に変換
    audio_array = np.frombuffer(data, dtype=np.int16)

    # リサンプリング
    num_samples = int(len(audio_array) * dst_rate / src_rate)
    resampled = signal.resample(audio_array, num_samples)

    # int16に戻す
    return resampled.astype(np.int16).tobytes()
```

**オプション2**: `soxr` (高速、軽量)

```python
# requirements.txt に追加
soxr>=0.3.0

# src/audio.py
import soxr
import numpy as np

def resample_audio(data: bytes, src_rate: int, dst_rate: int) -> bytes:
    """soxrベースのリサンプリング（高速）"""
    audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    resampled = soxr.resample(audio_array, src_rate, dst_rate)
    return (resampled * 32768.0).astype(np.int16).tobytes()
```

#### 成果物チェックリスト

- [ ] リサンプリング代替実装の選定（scipy or soxr）
- [ ] `src/audio.py` のリサンプリング処理を更新
- [ ] Python 3.13環境でのテスト
- [ ] 音質確認（元のaudioop.ratecvと比較）

---

### 2.7 config.py 段階的廃止計画

**現状**: `config.py` に後方互換エイリアスが残存。pydantic移行後は段階的に削除。

#### マイルストーン

**フェーズ1** (Phase 2.1完了時): pydantic導入、後方互換維持
- ✅ `src/config_models.py` 作成
- ✅ `config.py` に後方互換エイリアス残存
- ✅ 既存コードは動作継続

**フェーズ2** (Phase 3完了時): 直接参照の段階的移行
- [ ] 各モジュールで `from config import SAMPLE_RATE` → `from src.config_models import app_config` に変更
- [ ] `config.py` のエイリアスに `DeprecationWarning` 追加

**フェーズ3** (Phase 4完了時): 完全移行
- [ ] すべてのコードが `app_config` 経由でアクセス
- [ ] `config.py` 削除（環境変数ロードのみ残す）

#### 成果物チェックリスト

- [ ] 各フェーズのマイルストーン設定
- [ ] 移行ガイド作成（`docs/CONFIG_MIGRATION.md`）
- [ ] 後方互換期間の明確化（例: Phase 3まで維持）

---

## 📦 Phase 3: 機能拡張（割り込み改善 + 人格切替）

**目標**: ユーザー体験を向上させる
**優先度**: 🟡 中（Phase 1/2 完了後）

### 3.1 割り込み処理の改善

#### 実装内容

**現状の問題**:
- ウェイクワード検知ベースの割り込みのみ
- 音声キューのクリア後も残存チャンクが再生される可能性

**改善策**:
1. 割り込みフラグ（`interrupt_active`）の動作確認を強化
2. 音声再生スレッドに即座停止機能を追加
3. 割り込み時のフィードバック音追加（オプション）

**ファイル**: `src/audio.py` (修正)

```python
class AudioHandler:
    def __init__(self):
        self.playback_active = False
        self.stop_requested = False

    def play_audio(self, audio_bytes):
        """音声再生（停止可能）"""
        self.playback_active = True
        self.stop_requested = False

        # チャンクに分割して再生
        chunk_size = 1024
        for i in range(0, len(audio_bytes), chunk_size):
            if self.stop_requested:
                self.logger.info("Playback stopped by request")
                break
            chunk = audio_bytes[i:i+chunk_size]
            self.output_stream.write(chunk)

        self.playback_active = False

    def stop_playback(self):
        """再生を即座停止"""
        self.stop_requested = True
        # ストリームバッファをクリア
        if self.output_stream and self.output_stream.is_active():
            self.output_stream.stop_stream()
            self.output_stream.start_stream()
```

#### 成果物チェックリスト

- [ ] 割り込み時に音声が即座停止することを確認
- [ ] 残存チャンクが再生されないことを確認
- [ ] ログで割り込みフローが追跡可能なことを確認

---

### 3.2 人格切替機能（子供向けモード）

#### 実装内容

**ファイル**: `src/personality.py` (新規作成)

```python
from enum import Enum

class PersonalityMode(Enum):
    NORMAL = "normal"
    CHILD_FRIENDLY = "child_friendly"
    CONCISE = "concise"

class PersonalityConfig:
    """人格設定"""
    INSTRUCTIONS = {
        PersonalityMode.NORMAL: """
        あなたはキカイくん。やさしくてかわいいラズパイロボットのアシスタントです。
        話し方は、やわらかくて明るく、少しだけおちゃめなマスコットキャラクター風です。
        """,

        PersonalityMode.CHILD_FRIENDLY: """
        あなたはキカイくん。ちいさなおともだちとおはなしする、やさしいロボットです。
        ことばはかんたんで、みじかく、わかりやすくします。
        むずかしいことばはつかいません。たのしく、やさしくおはなしします。
        """,

        PersonalityMode.CONCISE: """
        あなたはキカイくん。簡潔で効率的なアシスタントです。
        回答は短く、要点のみを伝えます。
        """
    }

    VAD_SETTINGS = {
        PersonalityMode.NORMAL: {
            "threshold": 0.1,
            "silence_duration_ms": 200
        },
        PersonalityMode.CHILD_FRIENDLY: {
            "threshold": 0.15,  # 少し敏感に（子供の声は小さい）
            "silence_duration_ms": 500  # 長めに待つ（発話が遅い）
        }
    }
```

**ファイル**: `config.py` (追加)

```python
from src.personality import PersonalityMode
import os

# 人格モード（環境変数 or デフォルト）
PERSONALITY_MODE = PersonalityMode(os.getenv("PERSONALITY_MODE", "normal"))
```

**ファイル**: `src/realtime_client.py` (修正)

```python
from src.personality import PersonalityConfig

class RealtimeClient:
    async def connect(self, personality_mode: PersonalityMode = PersonalityMode.NORMAL):
        """接続時に人格モードを設定"""
        instructions = PersonalityConfig.INSTRUCTIONS[personality_mode]
        vad_settings = PersonalityConfig.VAD_SETTINGS.get(
            personality_mode,
            PersonalityConfig.VAD_SETTINGS[PersonalityMode.NORMAL]
        )

        await self.send_event({
            "type": "session.update",
            "session": {
                "instructions": instructions,
                "turn_detection": {
                    "type": "server_vad",
                    **vad_settings
                }
            }
        })
```

#### 成果物チェックリスト

- [ ] `.env` に `PERSONALITY_MODE=child_friendly` を設定して起動
- [ ] AI応答が子供向けの口調になることを確認
- [ ] VAD設定が適用されることを確認（ログで確認）

---

## 📦 Phase 4: 長期運用対応（パッケージ化 + systemd対応）

**目標**: 本格稼働に向けた基盤整備
**優先度**: 🟢 低（Phase 3 完了後）

### 4.1 パッケージ化

#### 実装内容

**新しいディレクトリ構造**:

```
talk_system/
├── talk_system/           # パッケージルート（旧src/）
│   ├── __init__.py
│   ├── app.py             # 旧conversation_app.py
│   ├── audio.py
│   ├── realtime_client.py
│   ├── gui.py
│   ├── state_machine.py
│   ├── personality.py
│   ├── animation/
│   │   ├── __init__.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       └── ...
├── config.py              # 設定（ルートに残す）
├── wake_word_daemon.py    # デーモン（ルートに残す）
├── pyproject.toml         # パッケージメタデータ
├── setup.py               # インストールスクリプト
└── README.md
```

**ファイル**: `pyproject.toml` (新規作成)

```toml
[project]
name = "talk-system"
version = "0.2.0"
description = "Raspberry Pi voice assistant with Live2D character"
requires-python = ">=3.9"
dependencies = [
    "pygame>=2.5.0",
    "pyaudio>=0.2.13",
    "websockets>=12.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "pvporcupine>=3.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0"
]

[project.scripts]
talk-system = "talk_system.app:main"
talk-daemon = "wake_word_daemon:main"
```

#### 成果物チェックリスト

- [ ] パッケージ構造にリファクタリング
- [ ] `pip install -e .` でインストール可能
- [ ] `talk-system` コマンドで起動可能

---

### 4.2 systemd サービス化

#### 実装内容

**ファイル**: `systemd/talk-system.service` (新規作成)

```ini
[Unit]
Description=Talk System Daemon (Wake Word Detection)
After=network.target sound.target

[Service]
Type=simple
User=yutapi5
WorkingDirectory=/home/yutapi5/Programs/talk_system
ExecStart=/home/yutapi5/Programs/talk_system/.venv/bin/python wake_word_daemon.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# 環境変数
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**ファイル**: `scripts/install_service.sh` (新規作成)

```bash
#!/bin/bash
# systemdサービスをインストール

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$PROJECT_DIR/systemd/talk-system.service"

echo "Installing talk-system service..."

# サービスファイルをコピー
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# systemdをリロード
sudo systemctl daemon-reload

# サービスを有効化
sudo systemctl enable talk-system.service

echo "Service installed. Start with: sudo systemctl start talk-system"
```

#### 成果物チェックリスト

- [ ] `./scripts/install_service.sh` でサービスインストール
- [ ] `sudo systemctl start talk-system` で起動
- [ ] `sudo journalctl -u talk-system -f` でログ確認
- [ ] Raspberry Pi再起動後、自動起動することを確認

---

## 🎯 実装優先順位まとめ

| Phase | タスク                   | 優先度 | 依存関係          | 期待効果                           |
| ----- | --------------------- | --- | ------------- | ------------------------------ |
| 1.1   | 状態管理の明示化              | 🔴  | なし            | デバッグ性向上、バグ減少                   |
| 1.2   | ロギング基盤導入              | 🔴  | なし            | 運用時のトラブルシュート可能化                |
| 1.3   | 例外処理・復旧ロジック           | 🔴  | 1.2 推奨       | 常駐プロセスとしての安定性向上                |
| 2.1   | 設定管理のリファクタリング         | 🟠  | なし            | 型安全性向上、設定ミス防止                  |
| 2.2   | 並行処理の責務整理             | 🟠  | なし            | 保守性向上、ドキュメント整備                 |
| 2.3   | フラグ統合とイベント駆動アーキテクチャ   | 🔴  | 1.1, 1.2, 2.1 | Single Source of Truth実現、制御フロー明確化 |
| 2.4   | タスクライフサイクル管理の改善       | 🔴  | 2.3           | シャットダウン堅牢性向上、リソースリーク防止         |
| 2.5   | 最小テストの導入              | 🟠  | 1.1, 2.1      | 品質保証、リグレッション防止                 |
| 2.6   | audioop.ratecv代替       | 🟡  | なし            | Python 3.13対応、将来互換性            |
| 2.7   | config.py段階的廃止計画      | 🟡  | 2.1           | 設計一貫性向上、技術的負債削減                |
| 3.1   | 割り込み処理の改善             | 🟡  | 2.3, 2.4      | UX向上（応答性改善）                   |
| 3.2   | 人格切替機能                | 🟡  | 2.1 推奨       | 子供向け対応、利用シーン拡大                 |
| 4.1   | パッケージ化                | 🟢  | 全Phase       | テスト可能性向上、再利用性向上                |
| 4.2   | systemd サービス化         | 🟢  | 4.1           | 本格稼働対応（自動起動・自動復旧）              |

---

## 📋 各Phaseの完了条件

### Phase 1 完了条件
- [ ] すべてのログが `logger` 経由で出力される
- [ ] 状態遷移が明示的に管理され、ログで追跡可能
- [ ] マイク・WebSocket障害時に適切なエラーメッセージが表示される
- [ ] WebSocket再接続が自動的に試行される

### Phase 2 完了条件
- [ ] `pydantic` ベースの設定管理が導入される
- [ ] 並行処理モデルがドキュメント化される
- [ ] 型ヒント補完が効く
- [ ] すべてのブール値フラグが状態機械に統合される
- [ ] イベント駆動アーキテクチャへ移行完了
- [ ] タスク追跡機能とクリーンアップ処理が実装される
- [ ] 最小限のテストが整備され、`pytest tests/` が成功する
- [ ] audioop.ratecv の代替実装が選定・実装される

### Phase 3 完了条件
- [ ] 割り込み時に音声が即座停止する
- [ ] 子供向けモードが `.env` で切り替え可能
- [ ] VAD設定がモードに応じて自動調整される

### Phase 4 完了条件
- [ ] `pip install -e .` でインストール可能
- [ ] systemd サービスとして起動可能
- [ ] Raspberry Pi 再起動後、自動起動する

---

## 🔄 リファクタリング実施フロー

### 推奨作業手順

1. **Phase 1 を完了させる**（最重要）
   - 1.1 → 1.2 → 1.3 の順に実装
   - 各サブタスクごとに動作確認
   - エラーログが適切に出力されることを確認

2. **Phase 2 を完了させる**（設計改善）
   - 2.1: 設定管理をリファクタリング
   - 2.2: ドキュメント整備

3. **Phase 3 を実装**（機能拡張）
   - 3.1: 割り込み改善
   - 3.2: 人格切替

4. **Phase 4 を実装**（本格運用）
   - 4.1: パッケージ化
   - 4.2: systemd対応

### Git ブランチ戦略

```bash
main                  # 現在の動作するコード
├── feature/phase1-state-management
├── feature/phase1-logging
├── feature/phase1-exception-handling
├── feature/phase2-config-refactor
├── feature/phase2-architecture-doc
├── feature/phase3-interrupt-improvement
├── feature/phase3-personality
├── feature/phase4-packaging
└── feature/phase4-systemd
```

各Phaseのブランチは独立してマージ可能。

---

## 📌 追加推奨事項

### テスト戦略

**ファイル**: `tests/test_state_machine.py` (新規作成例)

```python
import pytest
from src.state_machine import AppState, StateTransition

def test_valid_transition():
    assert StateTransition.is_valid_transition(AppState.IDLE, AppState.LISTENING)
    assert StateTransition.is_valid_transition(AppState.LISTENING, AppState.PROCESSING)

def test_invalid_transition():
    assert not StateTransition.is_valid_transition(AppState.IDLE, AppState.SPEAKING)
    assert not StateTransition.is_valid_transition(AppState.SPEAKING, AppState.IDLE)
```

実行:
```bash
pytest tests/
```

### CI/CD（オプション）

GitHub Actions を使った自動テスト例:

**ファイル**: `.github/workflows/test.yml`

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .[dev]
      - run: pytest tests/
      - run: mypy talk_system/
```

---

## 🎓 学習リソース

Phase実装時に参考になるドキュメント:

- **状態管理**: [Python Enum](https://docs.python.org/3/library/enum.html)
- **ロギング**: [Python logging](https://docs.python.org/3/library/logging.html)
- **Pydantic**: [Pydantic Documentation](https://docs.pydantic.dev/)
- **asyncio**: [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- **systemd**: [systemd.service](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

---

## 📞 質問・フィードバック

このリファクタリング計画について不明点があれば、以下の優先順位で進めてください：

1. Phase 1 を最優先で完了
2. Phase 2/3 は必要に応じて実装
3. Phase 4 は本格運用時に検討

---

**改訂履歴**:
- 2025-12-27: 初版作成
- 2025-12-28: Phase 2に追加タスク（2.3-2.7）を追加（外部レビューフィードバック反映）
  - フラグ統合とイベント駆動アーキテクチャ（2.3）
  - タスクライフサイクル管理の改善（2.4）
  - 最小テストの導入（2.5）
  - audioop.ratecv代替（2.6）
  - config.py段階的廃止計画（2.7）
