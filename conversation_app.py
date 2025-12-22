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
"""

import asyncio
import time
from src.audio import AudioHandler
from src.realtime_client import RealtimeClient
from src.gui import GUIHandler

# ================================================================================
# 状態定数
# ================================================================================
STATE_LISTENING = "LISTENING"    # 聞いている（緑色インジケーター）
STATE_PROCESSING = "PROCESSING"  # 考え中（黄色インジケーター）
STATE_SPEAKING = "SPEAKING"      # 発話中（口パクアニメーション）


class ConversationApp:
    """
    会話GUIアプリケーション管理クラス

    OpenAI Realtime APIとの接続、音声入出力、GUI表示、
    アニメーション制御、タイムアウト管理を一元的に行います。

    Attributes:
        state (str): 現在のアプリケーション状態
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
        self.state = STATE_LISTENING
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

        # 音声再生バッファとタイムアウト管理
        self.audio_queue = asyncio.Queue()      # AI応答音声のバッファリング用キュー
        self.is_playing_response = False        # 音声再生中フラグ
        self.last_interaction_time = time.time()  # 最後の操作時刻（タイムアウト判定用）
        self.response_in_progress = False       # AI応答処理中フラグ
        self.interrupt_active = False           # 割り込み中フラグ（音声受信を無視）
        self.inactivity_timeout = 60.0          # 無操作タイムアウト（60秒）
        self.connection_time = 0                # API接続時刻（ノイズ除外用）

    async def run(self):
        """
        アプリケーションのメインループ

        OpenAI Realtime APIに接続し、音声入出力とGUI更新を並行処理します。
        無操作タイムアウト（15秒）でアプリケーションを終了します。

        処理フロー:
        1. 音声ストリーム開始
        2. OpenAI APIに接続
        3. メインループ（GUI更新、音声再生、タイムアウト監視）
        4. クリーンアップ
        """
        print("Conversation App Started")

        # ================================================================================
        # 音声ストリームの開始
        # ================================================================================
        self.audio.start_stream(input_callback=self.audio_input_callback)
        asyncio.create_task(self.audio.record_loop())

        # ================================================================================
        # OpenAI Realtime APIに接続
        # ================================================================================
        try:
            await self.client.connect()
            self.connection_time = time.time()  # 接続時刻を記録
            self.last_interaction_time = time.time()
            self.gui.set_state(1)  # LISTENING（緑色インジケーター）
            print("Connected to OpenAI Realtime API")
        except Exception as e:
            print(f"Failed to connect: {e}")
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
                print(f"[TIMEOUT] Inactivity timeout ({self.inactivity_timeout}s elapsed: {elapsed:.1f}s). Exiting conversation.")
                self.gui.running = False
                break

            # AI応答音声の再生（キューから取り出して再生）
            if not self.audio_queue.empty():
                if not self.is_playing_response:
                    self.is_playing_response = True
                    self.gui.set_state(3)  # SPEAKING（口パクアニメーション）
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
                    self.gui.set_state(1)  # Back to LISTENING
                    print("[PLAYBACK] All audio chunks played, back to LISTENING")

            await asyncio.sleep(0.001)  # イベントループに制御を返す

        # ================================================================================
        # クリーンアップ
        # ================================================================================
        await self.cleanup()

    def audio_input_callback(self, in_data):
        """
        マイク入力コールバック

        AudioHandlerから呼ばれ、録音された音声データを
        OpenAI Realtime APIに送信します。

        Args:
            in_data (bytes): 録音された音声データ（PCM16, 24kHz, モノラル）
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.client.send_audio(in_data))

            # デバッグ: マイク入力送信を定期的にログ出力
            if not hasattr(self, '_input_counter'):
                self._input_counter = 0
            self._input_counter += 1
            if self._input_counter % 100 == 0:  # 100チャンクごとに出力
                print(f"[MIC] Sending audio to API (chunk #{self._input_counter}, {len(in_data)} bytes)")
        except RuntimeError:
            pass  # イベントループ未起動時は無視

    def on_user_speech_start(self):
        """
        ユーザー発話開始コールバック（割り込み処理）

        OpenAI Realtime APIがユーザーの発話開始を検知した際に呼ばれます。
        AI応答中の場合は割り込み処理を実行し、即座に音声を停止します。

        割り込み処理フロー:
        1. ローカル音声キューをクリア（未再生のAI音声を破棄）
        2. 音声再生を停止（現在再生中の音声を中断）
        3. Realtime APIに応答キャンセルを送信
        4. GUIをPROCESSING状態に更新
        """
        # 接続直後2秒間はノイズとして無視
        if time.time() - self.connection_time < 2.0:
            print("[BARGE-IN] Ignoring noise during connection startup")
            return

        print("[BARGE-IN] User speech started - initiating interrupt")
        self.last_interaction_time = time.time()  # タイムアウトリセット

        # 🆕 割り込みフラグを立てる（新しい音声チャンクを拒否）
        self.interrupt_active = True
        print("[BARGE-IN] Interrupt flag set - will ignore incoming audio")

        # 🆕 割り込み処理：音声キューをクリア（常に実行）
        queue_size = self.audio_queue.qsize()
        if queue_size > 0:
            print(f"[BARGE-IN] Clearing audio queue ({queue_size} chunks)")
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        else:
            print("[BARGE-IN] Audio queue already empty")

        # 🆕 割り込み処理：音声再生を停止（フラグに関係なく常に実行）
        # 理由: play_audio()はバッファに書き込むだけで、実際の再生は遅延する
        # キューが空でも、スピーカーバッファにはまだ音声が残っている可能性がある
        print("[BARGE-IN] Forcing audio playback stop")
        self.audio.stop_playback()

        # 🆕 割り込み処理：Realtime APIに中断を通知
        # 応答生成中の場合のみキャンセルを送信（サーバー側エラー回避）
        if self.response_in_progress:
            print(f"[BARGE-IN] Sending cancel (in_progress={self.response_in_progress}, is_playing={self.is_playing_response})")
            asyncio.create_task(self.client.cancel_response())
        else:
            print("[BARGE-IN] No active response to cancel on server")

        self.response_in_progress = False
        self.is_playing_response = False
        self.gui.reset_texts()  # 🆕 GUI側のテキスト表示を即座にリセット
        self.gui.set_state(2)  # PROCESSING（考え中）
        print("[BARGE-IN] Interrupt complete")

    def on_response_created(self):
        """
        AI応答生成開始コールバック

        OpenAI Realtime APIがAI応答の生成を開始した際に呼ばれます。
        割り込み判定のために、応答生成中フラグを立てます。
        新しい応答が開始されたため、割り込みフラグをリセットします。
        """
        print("Response created (generation started)")
        self.response_in_progress = True
        self.interrupt_active = False  # 新しい応答開始、割り込みフラグをリセット
        print("[RESPONSE] Interrupt flag cleared - accepting new audio")
        self.last_interaction_time = time.time()  # タイムアウトリセット

    def on_response_done(self):
        """
        AI応答完了コールバック

        OpenAI Realtime APIがAI応答の生成を完了した際に呼ばれます。
        応答生成中フラグをクリアします。
        """
        print("Response done")
        self.response_in_progress = False
        self.last_interaction_time = time.time()  # タイムアウトリセット

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
            print(f"[AUDIO] Ignoring audio chunk during interrupt ({len(audio_bytes)} bytes)")
            return

        # Note: response_in_progress は on_response_created で管理される
        self.audio_queue.put_nowait(audio_bytes)

    def handle_user_transcript(self, text):
        """
        ユーザー発話テキスト受信コールバック
        """
        print(f"User: {text}")
        self.gui.set_user_text(text)

        # 🆕 終了キーワードのチェック
        exit_keywords = ["ストップ", "おわり", "終わり", "終了", "バイバイ", "さようなら", "またね"]
        if any(kw in text for kw in exit_keywords):
            print(f"[EXIT] Exit keyword detected in user speech: {text}")
            # AIが最後に応答する時間を少しだけ確保してから終了するようにスケジュール
            asyncio.create_task(self.delayed_exit(2.0))

    async def delayed_exit(self, delay):
        """
        指定秒数後にアプリを終了する
        """
        await asyncio.sleep(delay)
        print("[EXIT] Exiting application by voice command.")
        self.gui.running = False

    def handle_agent_transcript(self, text):
        """
        AI応答テキスト受信コールバック

        OpenAI Realtime APIから受信したAI応答のトランスクリプトを
        GUIに表示します。

        Args:
            text (str): AI応答のテキスト
        """
        print(f"Agent: {text}")
        self.gui.set_agent_text(text)

    async def cleanup(self):
        """
        アプリケーションのクリーンアップ

        WebSocket接続を切断し、音声ストリームを停止し、
        GUIを終了します。
        """
        print("Cleaning up conversation app...")
        await self.client.close()
        self.audio.terminate()
        self.gui.quit()
        print("Conversation app exited")

if __name__ == "__main__":
    app = ConversationApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
