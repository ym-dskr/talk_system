#!/usr/bin/env python3
"""
会話GUIアプリケーション

ウェイクワード検知後に起動され、OpenAI Realtime APIを使用した
リアルタイム音声対話を提供します。15秒の無操作で自動終了し、
デーモンがウェイクワード検知モードに戻ります。

主要機能:
- OpenAI Realtime APIとのWebSocket接続
- リアルタイム音声入出力（24kHz PCM16）
- Live2D風キャラクターアニメーション
- 発話テキストの画面表示（日本語対応）
- 無操作タイムアウト（15秒）

動作フロー:
1. wake_word_daemon.pyから起動
2. OpenAI Realtime APIに接続
3. ユーザーの音声入力を受け付け
4. AIの応答を音声とテキストで表示
5. 15秒無操作でアプリ終了
6. デーモンがウェイクワード検知を再開

並行処理モデル:
このアプリケーションは3つの実行コンテキストで動作します:

1. **メインスレッド（このファイル）**:
   - pygameイベントループとGUI更新（60 FPS）
   - タイムアウト監視とアプリケーションライフサイクル管理
   - asyncioスレッドの起動と停止
   - 責務: ユーザーインターフェースとアプリケーション全体の制御

2. **asyncioスレッド**:
   - WebSocket通信（OpenAI Realtime API）
   - 音声データの送受信（非同期I/O）
   - イベント駆動のコールバック処理
   - 責務: ネットワーク通信とAPIイベント処理

3. **PyAudioコールバックスレッド**:
   - リアルタイム音声入出力（ハードウェア割り込み駆動）
   - 音声データのキューイング（queue.Queue経由でスレッド間通信）
   - 責務: 低レイテンシ音声処理

スレッド間通信:
- queue.Queue: PyAudioスレッド → asyncioスレッド（音声データ転送）
- threading.Event: asyncioスレッド → メインスレッド（状態同期）
- コールバック関数: asyncioスレッド → メインスレッド（イベント通知）

詳細は docs/ARCHITECTURE.md を参照してください。
"""

import asyncio
import time
import struct
import logging
from src.audio import AudioHandler
from src.realtime_client import RealtimeClient
from src.gui import GUIHandler
from src.wake_word import WakeWordEngine
from src.state_machine import AppState, StateTransition
from src.logging_config import setup_logging
from src.event_queue import EventQueue, Event, EventType

# ロギング初期化（本番はINFOをデフォルトにし、必要時のみDEBUG）
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationApp:
    """
    会話GUIアプリケーション管理クラス

    OpenAI Realtime APIとの接続、音声入出力、GUI表示、
    アニメーション制御、タイムアウト管理を一元的に行います。

    Attributes:
        state (AppState): 現在のアプリケーション状態
        gui (GUIHandler): GUI表示とアニメーション管理
        audio (AudioHandler): 音声入出力管理
        client (RealtimeClient): OpenAI Realtime APIクライアント
        audio_queue (asyncio.Queue): AI応答音声のバッファ
        is_playing_response (bool): 応答音声再生中フラグ
        last_interaction_time (float): 最後の操作時刻（Unix時間）
        response_in_progress (bool): AI応答処理中フラグ
        interrupt_active (bool): 割り込み中フラグ（True時は音声受信を破棄）
        inactivity_timeout (float): 無操作タイムアウト時間（秒）
        connection_time (float): API接続時刻（ノイズ除外用）
    """
    def __init__(self):
        """
        ConversationAppを初期化

        GUI、オーディオハンドラー、Realtime APIクライアントを初期化し、
        各種コールバックを設定します。
        """
        self.logger = logging.getLogger(__name__)
        self.state = AppState.IDLE  # 初期状態はIDLE（接続前）
        self.gui = GUIHandler()
        self.audio = AudioHandler()

        # OpenAI Realtime APIクライアントの初期化（コールバック設定）
        self.client = RealtimeClient(
            on_audio_delta=self.handle_audio_delta,          # AI応答音声受信時
            on_user_transcript=self.handle_user_transcript,  # ユーザー発話テキスト受信時
            on_agent_transcript=self.handle_agent_transcript,  # AI応答テキスト受信時
            on_speech_started=self.on_user_speech_start,    # ユーザー発話開始検知時
            on_response_done=self.on_response_done,         # AI応答完了時
            on_response_created=self.on_response_created    # AI応答生成開始時（割り込み判定用）
        )

        # イベント駆動アーキテクチャ（Phase 2.3）
        self.event_queue = EventQueue()         # イベントキュー（中央制御）
        self.tasks: set[asyncio.Task] = set()   # タスク追跡（適切なライフサイクル管理）
        self.stop_event = asyncio.Event()       # シャットダウンシグナル

        # 音声再生バッファとタイムアウト管理
        self.audio_queue = asyncio.Queue()      # AI応答音声のバッファリング用キュー
        self.is_playing_response = False        # 音声再生中フラグ（TODO: Phase 2.3で削除）
        self.last_interaction_time = time.time()  # 最後の操作時刻（タイムアウト判定用）
        self.response_in_progress = False       # AI応答処理中フラグ（TODO: Phase 2.3で削除）
        self.interrupt_active = False           # 割り込み中フラグ（TODO: Phase 2.3で削除）
        self.inactivity_timeout = 180.0         # 無操作タイムアウト（180秒 = 3分）
        self.connection_time = 0                # API接続時刻（ノイズ除外用）
        self.exit_requested = False             # 終了キーワード検知時にTrue（重複終了を防止）

        # ローカルウェイクワード検知（割り込み用）
        self.wake_word = WakeWordEngine()       # Porcupineエンジン
        self.wake_word_buffer = []              # ウェイクワード検知用PCMバッファ
        self.wake_word_resample_state = None    # リサンプリング状態（24kHz → 16kHz）
        self.local_interrupt_enabled = False    # ローカル割り込み検知フラグ（AI応答中のみTrue）

    def set_state(self, new_state: AppState):
        """
        状態遷移（検証付き）

        Args:
            new_state: 遷移先の状態

        Note:
            状態遷移が不正な場合は警告ログを出力し、遷移を行いません。
            GUIの状態表示も自動的に更新されます。
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
                AppState.ERROR: 4  # 赤色インジケーター表示
            }
            if new_state in state_map:
                self.gui.set_state(state_map[new_state])
        else:
            allowed = [s.name for s in StateTransition.get_allowed_transitions(self.state)]
            self.logger.warning(
                f"Invalid state transition: {self.state.name} → {new_state.name} "
                f"(allowed: {allowed})"
            )

    async def run(self):
        """
        アプリケーションのメインループ（asyncio event loop内で実行）

        OpenAI Realtime APIに接続し、音声入出力とGUI更新を並行処理します。
        無操作タイムアウト（15秒）でアプリケーションを終了します。

        処理フロー:
        1. 音声ストリーム開始
        2. OpenAI APIに接続
        3. メインループ（GUI更新、音声再生、タイムアウト監視）
        4. クリーンアップ

        並行処理構造:
        - このメソッドはasyncioイベントループで実行されます
        - pygameのGUI更新（self.gui.update）は同期的に呼び出されます（60 FPS）
        - WebSocket通信（self.client）はasyncioタスクとして並行実行されます
        - PyAudio音声処理は別スレッドのコールバックとして並行実行されます
        - 各処理間の通信はキューとコールバックで行われます
        """
        self.logger.info("Conversation App Started")

        try:
            # ================================================================================
            # 音声ストリームの開始
            # ================================================================================
            try:
                self.audio.start_stream(input_callback=self.audio_input_callback)
                self._start_task(self.audio.record_loop())  # タスク追跡を有効化
            except RuntimeError as e:
                self.logger.error(f"Failed to initialize audio stream: {e}")
                self.set_state(AppState.ERROR)
                self.gui.running = False
                return
            except Exception as e:
                self.logger.error(f"Unexpected error during audio initialization: {e}", exc_info=True)
                self.set_state(AppState.ERROR)
                self.gui.running = False
                return

            # ================================================================================
            # OpenAI Realtime APIに接続
            # ================================================================================
            try:
                await self.client.connect()
                self.connection_time = time.time()  # 接続時刻を記録
                self.last_interaction_time = time.time()
                self.set_state(AppState.LISTENING)
                self.logger.info("Connected to OpenAI Realtime API")
            except RuntimeError as e:
                self.logger.error(f"Failed to connect to Realtime API: {e}")
                self.set_state(AppState.ERROR)
                self.gui.running = False
                return
            except Exception as e:
                self.logger.error(f"Unexpected error during API connection: {e}", exc_info=True)
                self.set_state(AppState.ERROR)
                self.gui.running = False
                return

            # ================================================================================
            # メインループ
            # ================================================================================
            while self.gui.running:
                # GUI更新（キャラクターアニメーション、テキスト表示、イベント処理）
                self.gui.update()

                # 無操作タイムアウトチェック（15秒）
                elapsed = time.time() - self.last_interaction_time
                if elapsed > self.inactivity_timeout:
                    self.logger.info(f"Inactivity timeout ({self.inactivity_timeout}s elapsed: {elapsed:.1f}s). Exiting conversation.")
                    self.gui.running = False
                    break

                # AI応答音声の再生（キューから取り出して再生）
                if not self.audio_queue.empty():
                    if not self.is_playing_response:
                        self.is_playing_response = True
                        # LISTENING → PROCESSING → SPEAKING の順に遷移
                        if self.state == AppState.LISTENING:
                            self.set_state(AppState.PROCESSING)
                        if self.state == AppState.PROCESSING:
                            self.set_state(AppState.SPEAKING)
                            # SPEAKING状態に入ったらウェイクワード検知を有効化（割り込み可能）
                            self.local_interrupt_enabled = True
                            self.logger.debug("Wake word detection enabled during SPEAKING")
                    self.last_interaction_time = time.time()  # タイムアウトリセット

                    chunk = await self.audio_queue.get()
                    # チャンク取得直後に割り込みが発生していないか再確認
                    if not self.interrupt_active:
                        # play_audioをスレッドで実行してブロッキングを回避
                        await asyncio.get_event_loop().run_in_executor(None, self.audio.play_audio, chunk)
                else:
                    # 音声再生完了時、LISTENINGモードに戻る
                    if self.is_playing_response:
                        self.is_playing_response = False
                        self.local_interrupt_enabled = False
                        self.set_state(AppState.LISTENING)
                        self.logger.debug("Playback complete, back to LISTENING")

                        # 音声再生完了後、Turn Detectionを再有効化してユーザー音声を検知可能にする
                        task = asyncio.create_task(self.client.enable_turn_detection())
                        self.tasks.add(task)
                        task.add_done_callback(self.tasks.discard)

                await asyncio.sleep(0.001)  # イベントループに制御を返す

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
            self.set_state(AppState.ERROR)
        finally:
            # ================================================================================
            # クリーンアップ
            # ================================================================================
            await self.cleanup()

    def audio_input_callback(self, in_data):
        """
        マイク入力コールバック

        AudioHandlerから呼ばれ、録音された音声データを
        OpenAI Realtime APIに送信します。

        SPEAKING中は音声送信を停止し、ウェイクワード検知のみ実行します。
        ウェイクワード検知時は割り込み処理でLISTENING状態に戻ります。

        Args:
            in_data (bytes): 録音された音声データ（PCM16, 24kHz, モノラル）
        """
        try:
            loop = asyncio.get_running_loop()

            # LISTENING状態の時のみAPIに音声を送信
            # SPEAKING/PROCESSING中はAPIに送信しない（AIの声を拾うのを防ぐ）
            # ただし、ウェイクワード検知は継続（割り込み可能）
            if self.state == AppState.LISTENING:
                loop.create_task(self.client.send_audio(in_data))

            # ================================================================================
            # ローカルウェイクワード検知（AI応答中のみ）
            # ================================================================================
            if self.local_interrupt_enabled:
                import audioop
                # リサンプリング: 24kHz → 16kHz（Porcupine用）
                resampled_data, self.wake_word_resample_state = audioop.ratecv(
                    in_data, 2, 1, 24000, 16000, self.wake_word_resample_state
                )

                # バイト列をPCMサンプル（int16）に変換してバッファに追加
                pcm = struct.unpack_from("h" * (len(resampled_data) // 2), resampled_data)
                self.wake_word_buffer.extend(pcm)

                # バッファに十分なサンプルが溜まったら検知処理
                if len(self.wake_word_buffer) >= self.wake_word.frame_length:
                    # 必要なサンプル数（512）を取り出す
                    frame = self.wake_word_buffer[:self.wake_word.frame_length]
                    self.wake_word_buffer = self.wake_word_buffer[self.wake_word.frame_length:]

                    # Porcupineでウェイクワード検知
                    keyword_index = self.wake_word.process(frame)
                    if keyword_index >= 0:
                        self.logger.info("Wake word detected - interrupting AI response")
                        # 割り込み処理を実行
                        self.execute_interrupt()

        except RuntimeError:
            pass  # イベントループ未起動時は無視
        except Exception as e:
            self.logger.error(f"Audio callback error: {e}")

    def on_user_speech_start(self):
        """
        ユーザー発話開始コールバック

        OpenAI Realtime APIがユーザーの発話開始を検知した際に呼ばれます。
        キーワード検知ベースの割り込み機能を使用するため、
        ここでは自動割り込みは行わず、タイムアウトリセットのみ実行します。

        実際の割り込み処理は handle_user_transcript() でキーワード検知時に実行されます。
        """
        # 接続直後2秒間はノイズとして無視
        if time.time() - self.connection_time < 2.0:
            return

        self.last_interaction_time = time.time()  # タイムアウトリセット

    def on_response_created(self):
        """
        AI応答生成開始コールバック

        OpenAI Realtime APIがAI応答の生成を開始した際に呼ばれます。
        割り込み判定のために、応答生成中フラグを立てます。
        新しい応答が開始されたため、割り込みフラグをリセットします。

        また、AI応答中にユーザーの音声を検知しないよう、
        Turn Detection（VAD）を無効化します。

        ローカルウェイクワード検知を有効化し、「きかいくん」で
        割り込み可能にします。
        """
        self.logger.debug("AI response started")
        self.response_in_progress = True
        self.interrupt_active = False  # 新しい応答開始、割り込みフラグをリセット
        self.last_interaction_time = time.time()  # タイムアウトリセット

        # AI応答中はユーザーの音声を検知しないよう、Turn Detectionを無効化
        task = asyncio.create_task(self.client.disable_turn_detection())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        # ローカルウェイクワード検知を有効化（AI応答中の割り込み用）
        self.local_interrupt_enabled = True
        self.wake_word_buffer = []              # バッファをクリア
        self.wake_word_resample_state = None    # リサンプリング状態をリセット

    def on_response_done(self):
        """
        AI応答完了コールバック

        OpenAI Realtime APIがAI応答の生成を完了した際に呼ばれます。
        応答生成中フラグをクリアします。

        応答が完了またはキャンセルされた場合、Turn Detectionを再有効化して
        次のユーザー発話を検知できるようにします。
        """
        self.logger.debug("AI response completed")
        self.response_in_progress = False
        self.last_interaction_time = time.time()  # タイムアウトリセット

        # Turn Detectionを再有効化（次のユーザー発話を検知可能にする）
        # 音声キューが空の場合（キャンセルされた場合）に即座に有効化
        if self.audio_queue.empty():
            self.logger.debug("Response cancelled or empty, re-enabling turn detection immediately")
            task = asyncio.create_task(self.client.enable_turn_detection())
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    def handle_audio_delta(self, audio_bytes):
        """
        AI応答音声受信コールバック

        OpenAI Realtime APIから受信した音声デルタをキューに追加します。
        メインループで順次再生されます。

        割り込み中（interrupt_active=True）の場合は、受信した音声を破棄します。
        これにより、APIがキャンセル後も送信してくる音声チャンクを無視できます。

        Args:
            audio_bytes (bytes): AI応答音声データ（PCM16, 24kHz, モノラル）
        """
        self.last_interaction_time = time.time()  # タイムアウトリセット

        # 割り込み中は音声チャンクを破棄
        if self.interrupt_active:
            return

        # Note: response_in_progress は on_response_created で管理される
        self.audio_queue.put_nowait(audio_bytes)

    def execute_interrupt(self):
        """
        割り込み処理を実行

        AI応答中にユーザーが特定のキーワードを発話した際に呼ばれます。
        音声キューのクリア、音声再生停止、APIへのキャンセル送信を行います。
        """
        self.logger.info("Executing interrupt")

        # 既にLISTENING状態の場合は何もしない（重複検知を防ぐ）
        if self.state == AppState.LISTENING:
            self.logger.debug("Already in LISTENING state, skipping interrupt")
            return

        # 割り込みフラグを立てる（新しい音声チャンクを拒否）
        self.interrupt_active = True

        # 音声キューをクリア
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # 音声再生を停止
        self.audio.stop_playback()

        # Realtime APIに中断を通知
        if self.response_in_progress:
            task = asyncio.create_task(self.client.cancel_response())
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

        self.response_in_progress = False
        self.is_playing_response = False
        self.gui.reset_texts()  # GUI側のテキスト表示を即座にリセット

        # ウェイクワード検知後はLISTENING状態に戻る
        self.set_state(AppState.LISTENING)

        # ローカルウェイクワード検知を無効化（割り込み完了）
        self.local_interrupt_enabled = False

        # 割り込み後、Turn Detectionを再有効化してユーザーの次の発話を受け付ける
        task = asyncio.create_task(self.client.enable_turn_detection())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        self.logger.debug("Interrupt complete - back to LISTENING")

    def handle_user_transcript(self, text):
        """
        ユーザー発話テキスト受信コールバック

        Note:
            AI応答中の割り込みはローカルウェイクワード検知で処理されるため、
            ここでは終了キーワードのみチェックします。
        """
        if text is None:
            self.logger.debug("User transcript missing; skipping keyword check")
            return
        self.logger.info(f"User: {text}")
        self.gui.set_user_text(text)

        # 終了キーワードのチェック
        exit_keywords = ["ストップ", "おわり", "終わり", "おしまい", "終了", "バイバイ", "さようなら", "またね"]
        if any(kw in text for kw in exit_keywords):
            self.logger.info(f"Exit keyword detected in user speech: {text}")
            if not self.exit_requested:
                self.exit_requested = True
                self.logger.info("Exit requested; will quit in 3 seconds")
                task = asyncio.create_task(self.delayed_exit(3.0))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)

    async def delayed_exit(self, delay):
        """
        指定秒数後にアプリを終了する
        """
        await asyncio.sleep(delay)
        self.logger.info("Exiting application by voice command")
        self.gui.running = False

    def handle_agent_transcript(self, text):
        """
        AI応答テキスト受信コールバック

        OpenAI Realtime APIから受信したAI応答のトランスクリプトを
        GUIに表示します。

        Args:
            text (str): AI応答のテキスト
        """
        self.logger.info(f"Agent: {text}")
        self.gui.set_agent_text(text)

    def _start_task(self, coro):
        """
        タスクを起動して追跡

        asyncioタスクを作成し、タスクセットに追加して追跡します。
        タスク完了時に自動的にセットから削除されます。

        Args:
            coro: 実行するコルーチン

        Returns:
            作成されたasyncio.Task
        """
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def cleanup(self):
        """
        アプリケーションのクリーンアップ（順序付きシャットダウン）

        Phase 2.3: イベント駆動アーキテクチャ対応
        1. 停止シグナル設定
        2. タスクキャンセル
        3. タスク完了待機
        4. リソース解放

        WebSocket接続を切断し、音声ストリームを停止し、
        GUIを終了します。
        """
        self.logger.info("Starting cleanup...")

        # 1. 停止シグナル設定
        self.stop_event.set()

        # 2. タスクキャンセル
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # 3. タスク完了待機（例外を無視）
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.logger.debug(f"All {len(self.tasks)} tasks cancelled")

        # 4. リソース解放
        try:
            await self.client.close()
        except Exception as e:
            self.logger.error(f"Error closing WebSocket client: {e}")

        try:
            self.audio.terminate()
        except Exception as e:
            self.logger.error(f"Error terminating audio: {e}")

        try:
            self.gui.quit()
        except Exception as e:
            self.logger.error(f"Error quitting GUI: {e}")

        # WakeWordEngineリソースを解放
        if hasattr(self, 'wake_word'):
            try:
                self.wake_word.delete()
            except Exception as e:
                self.logger.error(f"Error deleting wake word engine: {e}")

        self.logger.info("Cleanup completed")

if __name__ == "__main__":
    app = ConversationApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
