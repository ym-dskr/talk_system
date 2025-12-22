#!/usr/bin/env python3
"""
ウェイクワード検知デーモン

systemdサービスとしてバックグラウンドで常駐し、
マイク入力からウェイクワード「Kikai-kun（キカイくん）」を検知します。
検知時にconversation_app.pyを起動し、終了後は再びウェイクワード検知に戻ります。

動作フロー:
1. マイクから音声入力（48kHz → 24kHz → 16kHzとリサンプリング）
2. Picovoice Porcupineでウェイクワード検知（512サンプル単位）
3. 検知時にGUIアプリ（conversation_app.py）を起動
4. GUIアプリ終了後、音声ストリームを再起動してウェイクワード検知を再開

リサンプリングチェーン:
- マイクハードウェア: 48kHz（Raspberry Piデフォルト）
- AudioHandler処理: 48kHz → 24kHz（OpenAI Realtime API用）
- Wake Word検知: 24kHz → 16kHz（Porcupine用）

注意:
- GUIアプリ起動時は音声デバイスを解放（デバイス競合回避）
- GUIアプリ終了後は音声ストリームを再起動
"""

import time
import struct
import subprocess
import sys

# ================================================================================
# ログ出力のバッファリング無効化（systemdログ用）
# ================================================================================
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), 'w', buffering=1)

from src.wake_word import WakeWordEngine
from src.audio import AudioHandler


class WakeWordDaemon:
    """
    ウェイクワード検知デーモン管理クラス

    バックグラウンドでマイク入力を監視し、ウェイクワード検知時に
    GUIアプリを起動します。GUIアプリ終了後は自動的にウェイクワード検知を再開します。

    Attributes:
        audio (AudioHandler): 音声入出力管理
        wake_word (WakeWordEngine): Picovoice Porcupineエンジン
        pcm_buffer (list): リサンプリング済みPCMサンプルバッファ
        wake_word_resample_state: リサンプリング状態（24kHz → 16kHz）
        running (bool): デーモン実行中フラグ
        gui_process (subprocess.Popen): GUIアプリプロセス
        debug_counter (int): デバッグ出力用カウンター
    """
    def __init__(self):
        """
        WakeWordDaemonを初期化

        AudioHandler、WakeWordEngineを初期化し、
        バッファとプロセス管理用の変数を設定します。
        """
        self.audio = AudioHandler()
        self.wake_word = WakeWordEngine()
        self.pcm_buffer = []                     # ウェイクワード検知用PCMサンプルバッファ
        self.wake_word_resample_state = None     # リサンプリング状態（24kHz → 16kHz）
        self.running = True                      # デーモン実行中フラグ
        self.gui_process = None                  # GUIアプリプロセス
        self.debug_counter = 0                   # デバッグ出力用カウンター

    def audio_input_callback(self, in_data):
        """
        マイク入力コールバック（ウェイクワード検知用）

        AudioHandlerから呼ばれ、録音された音声データをリサンプリングして
        ウェイクワード検知用のバッファに追加します。

        リサンプリング:
        - 入力: 24kHz（AudioHandlerで48kHz→24kHzに変換済み）
        - 出力: 16kHz（Porcupineの要求サンプルレート）

        Args:
            in_data (bytes): 録音された音声データ（PCM16, 24kHz, モノラル）

        注意:
            GUIアプリ起動中（gui_process != None）は処理をスキップします。
            これにより、会話中はウェイクワード検知を停止します。
        """
        # GUIアプリ起動中はウェイクワード検知を停止
        if self.gui_process is not None:
            return

        import audioop
        # リサンプリング: 24kHz → 16kHz（Porcupine用）
        try:
            resampled_data, self.wake_word_resample_state = audioop.ratecv(
                in_data, 2, 1, 24000, 16000, self.wake_word_resample_state
            )

            # バイト列をPCMサンプル（int16）に変換してバッファに追加
            pcm = struct.unpack_from("h" * (len(resampled_data) // 2), resampled_data)
            self.pcm_buffer.extend(pcm)
        except Exception as e:
            print(f"[Error] Audio callback error: {e}")

    def launch_gui_app(self):
        """
        GUIアプリ（conversation_app.py）を起動

        ウェイクワード検知時に呼ばれ、会話GUIアプリを起動します。
        音声デバイスの競合を避けるため、起動前にデーモン側の音声ストリームを停止します。

        処理フロー:
        1. 音声ストリームを停止（デバイスを解放）
        2. 仮想環境のPythonで conversation_app.py を起動
        3. プロセスIDを保存して、終了監視に使用

        Note:
            GUIアプリが終了すると、メインループで検知され、
            音声ストリームが再起動されてウェイクワード検知が再開されます。
        """
        # GUIプロセスが起動していないか、既に終了している場合のみ起動
        if self.gui_process is None or self.gui_process.poll() is not None:
            print("Launching GUI conversation app...")

            # 音声ストリームを停止してデバイスを解放（GUIアプリが使用するため）
            print("Stopping audio stream...")
            self.audio.stop_stream()

            # プロジェクトパスと仮想環境のPythonパス
            script_dir = "/home/yutapi5/Programs/talk_system"
            python_path = f"{script_dir}/.venv/bin/python3"

            # GUIアプリをサブプロセスとして起動
            self.gui_process = subprocess.Popen(
                [python_path, f"{script_dir}/conversation_app.py"],
                cwd=script_dir
            )
            print(f"GUI app launched (PID: {self.gui_process.pid})")

    async def run(self):
        """
        デーモンのメインループ

        ウェイクワード検知とGUIアプリ管理を行うメインループです。
        無限ループでマイク入力を監視し、ウェイクワード検知時にGUIアプリを起動します。

        処理フロー:
        1. 音声ストリーム開始（48kHz、chunk=1536）
        2. 録音ループ開始
        3. メインループ：
           a. GUIアプリ終了監視
           b. GUIアプリ終了時は音声ストリームを再起動
           c. ウェイクワード検知処理（512サンプル単位）
           d. 検知時にGUIアプリ起動

        チャンクサイズの計算:
        - Porcupineは16kHzで512サンプル必要
        - 48kHz → 24kHz → 16kHz とリサンプリング
        - 48kHzで1536サンプル = 16kHzで512サンプル

        Raises:
            KeyboardInterrupt: Ctrl+Cでデーモン終了
        """
        import asyncio

        print("Wake Word Daemon Started")
        print("Listening for 'Kikai-kun'...")

        # ================================================================================
        # 音声ストリーム開始
        # ================================================================================
        # チャンクサイズ1536: Porcupineに必要な512サンプル（16kHz）を得るため
        # 48kHz → 24kHz → 16kHz のリサンプリングチェーンで、
        # 48kHzの1536サンプルが16kHzの512サンプルに変換される
        self.audio.start_stream(input_callback=self.audio_input_callback, chunk=1536)

        # 録音ループを非同期タスクとして起動
        asyncio.create_task(self.audio.record_loop())

        try:
            # ================================================================================
            # メインループ
            # ================================================================================
            while self.running:
                # ────────────────────────────────────────────────────────────
                # GUIアプリ終了監視
                # ────────────────────────────────────────────────────────────
                if self.gui_process and self.gui_process.poll() is not None:
                    print("GUI app exited. Resuming wake word detection.")
                    self.gui_process = None
                    self.pcm_buffer = []                    # バッファクリア
                    self.wake_word_resample_state = None    # リサンプリング状態リセット

                    # 音声ストリームを再起動（GUIアプリが解放したデバイスを再取得）
                    print("Restarting audio stream...")
                    self.audio.start_stream(input_callback=self.audio_input_callback, chunk=1536)

                    # 録音ループを再起動
                    print("Restarting record loop...")
                    asyncio.create_task(self.audio.record_loop())

                    await asyncio.sleep(0.5)  # ストリーム安定化待ち
                    print("Audio stream restarted. Listening for wake word...")

                # ────────────────────────────────────────────────────────────
                # ウェイクワード検知処理（GUIアプリ未起動時のみ）
                # ────────────────────────────────────────────────────────────
                if self.gui_process is None:
                    # バッファに十分なサンプルが溜まったら検知処理
                    if len(self.pcm_buffer) >= self.wake_word.frame_length:
                        # 必要なサンプル数（512）を取り出す
                        frame = self.pcm_buffer[:self.wake_word.frame_length]
                        self.pcm_buffer = self.pcm_buffer[self.wake_word.frame_length:]

                        # Porcupineでウェイクワード検知
                        keyword_index = self.wake_word.process(frame)
                        if keyword_index >= 0:
                            print("Wake Word Detected!")
                            self.launch_gui_app()

                    # デバッグ出力（約5秒ごと）
                    self.debug_counter += 1
                    if self.debug_counter >= 500:
                        print(f"[Debug] Listening... (buffer: {len(self.pcm_buffer)} samples)")
                        self.debug_counter = 0

                await asyncio.sleep(0.01)  # イベントループに制御を返す

        except KeyboardInterrupt:
            print("\nShutting down daemon...")
        finally:
            self.cleanup()

    def cleanup(self):
        """
        デーモン終了時のクリーンアップ

        リソースを適切に解放してデーモンを終了します。

        処理内容:
        1. 起動中のGUIアプリを終了
        2. 音声ストリームを停止してPyAudioを終了
        3. Porcupineエンジンを解放

        Note:
            systemdサービスの停止時に自動的に呼ばれます。
        """
        print("Cleaning up...")

        # GUIアプリが起動中なら終了
        if self.gui_process and self.gui_process.poll() is None:
            self.gui_process.terminate()  # 終了シグナル送信
            self.gui_process.wait()       # プロセス終了待機

        # オーディオリソース解放
        self.audio.terminate()

        # Porcupineエンジン解放
        self.wake_word.delete()

        print("Daemon stopped")

if __name__ == "__main__":
    import asyncio
    daemon = WakeWordDaemon()
    asyncio.run(daemon.run())
