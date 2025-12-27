"""
オーディオ入出力ハンドラー

PyAudioを使用した音声入出力の低レベル制御を提供します。
ハードウェアサンプルレート（48kHz）とAPIサンプルレート（24kHz）間の
自動リサンプリング、モノラル/ステレオ変換を実行します。

並行処理の責務:
このモジュールは**PyAudioコールバックスレッド**で実行されます。
PyAudioはC拡張で実装されたオーディオライブラリであり、
オーディオデバイスからの割り込みを専用スレッドで処理します。

スレッドモデル:
1. **PyAudioコールバックスレッド** (input_callback, output_callback):
   - オーディオハードウェアの割り込み駆動で実行
   - リアルタイム性が要求されるため、重い処理は禁止
   - queue.Queue経由でデータを受け渡し（スレッドセーフ）

2. **asyncioスレッド** (record_loop, play_audio):
   - キューからデータを取り出してWebSocketに送信
   - WebSocketからデータを受信してキューに格納

重要な制約:
- コールバック内では重い処理やブロッキング処理を避けること
- スレッド間通信はqueue.Queueを使用すること（threading.Lock不要）
- コールバック内でprint()を使わないこと（ロギングはOK、バッファリングされるため）
"""

import pyaudio
import asyncio
import numpy as np
import time
import threading
import logging

logger = logging.getLogger(__name__)


class AudioHandler:
    """
    PyAudioベースの音声入出力ハンドラー

    ハードウェアとアプリケーション間のサンプルレート変換、
    チャンネル数変換（モノラル/ステレオ）を自動的に処理します。

    サンプリングフロー:
        入力: マイク(48kHz, モノラル) -> リサンプリング -> アプリ(24kHz, モノラル)
        出力: アプリ(24kHz, モノラル) -> リサンプリング -> スピーカー(48kHz, ステレオ)

    Attributes:
        p (pyaudio.PyAudio): PyAudioインスタンス
        input_stream (pyaudio.Stream): 入力ストリーム
        output_stream (pyaudio.Stream): 出力ストリーム
        _running (bool): ストリーム実行中フラグ
        input_resample_state: 入力リサンプリング状態
        output_resample_state: 出力リサンプリング状態
        chunk_size (int): チャンクサイズ
        input_callback (callable): 入力コールバック関数
        output_channels (int): 出力チャンネル数
        target_rate (int): ターゲットサンプルレート（24kHz）
        hw_rate (int): ハードウェアサンプルレート（48kHz）
    """

    def __init__(self):
        """
        AudioHandlerを初期化

        PyAudioインスタンスを作成し、ストリームとリサンプリング状態を初期化します。
        """
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self._running = False
        self._output_lock = threading.Lock()

        # Resampling states
        self.input_resample_state = None
        self.output_resample_state = None
        self.logger = logging.getLogger(__name__)

    def _list_audio_devices(self):
        """
        利用可能なオーディオデバイスを列挙（デバイス診断用）

        PyAudioが認識している全てのオーディオデバイスをログに出力します。
        デバイス初期化エラー時の診断に使用されます。
        """
        try:
            info = self.p.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')

            self.logger.info("Available audio devices:")
            for i in range(num_devices):
                try:
                    device_info = self.p.get_device_info_by_host_api_device_index(0, i)
                    device_name = device_info.get('name')
                    max_input_channels = device_info.get('maxInputChannels')
                    max_output_channels = device_info.get('maxOutputChannels')
                    default_sample_rate = device_info.get('defaultSampleRate')

                    device_type = []
                    if max_input_channels > 0:
                        device_type.append(f"Input({max_input_channels}ch)")
                    if max_output_channels > 0:
                        device_type.append(f"Output({max_output_channels}ch)")

                    self.logger.info(
                        f"  [{i}] {device_name} - {'/'.join(device_type)} @ {default_sample_rate}Hz"
                    )
                except Exception as e:
                    self.logger.warning(f"  [{i}] Error reading device info: {e}")
        except Exception as e:
            self.logger.error(f"Failed to enumerate audio devices: {e}")

    def start_stream(self, rate=24000, chunk=1024, input_callback=None):
        """
        入力および出力ストリームを開始

        ハードウェアサンプルレート（48kHz）でストリームを開き、
        内部でターゲットレート（24kHz）との間でリサンプリングを実行します。

        Args:
            rate (int): アプリケーション側のサンプルレート（デフォルト: 24000Hz）
            chunk (int): チャンクサイズ（フレーム数、デフォルト: 1024）
            input_callback (callable, optional): 録音された音声チャンク（bytes）を受け取るコールバック関数
        """
        from config import INPUT_DEVICE_INDEX, OUTPUT_DEVICE_INDEX, INPUT_CHANNELS, OUTPUT_CHANNELS, HARDWARE_SAMPLE_RATE
        
        self._running = True
        self.output_channels = OUTPUT_CHANNELS
        self.target_rate = rate # API Rate (24k)
        self.hw_rate = HARDWARE_SAMPLE_RATE # HW Rate (48k)

        self.logger.info(
            f"Opening audio stream: Input=[device={INPUT_DEVICE_INDEX}, ch={INPUT_CHANNELS}], "
            f"Output=[device={OUTPUT_DEVICE_INDEX}, ch={OUTPUT_CHANNELS}], "
            f"HW_rate={self.hw_rate}Hz, Target_rate={self.target_rate}Hz"
        )

        # Output Stream（バッファサイズを大きくして音飛びを防止）
        try:
            self.output_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=OUTPUT_CHANNELS,
                rate=self.hw_rate,
                output=True,
                output_device_index=OUTPUT_DEVICE_INDEX,
                frames_per_buffer=chunk * 4  # バッファサイズを4倍に増やして安定化
            )
            self.logger.info(f"Output stream opened successfully (device={OUTPUT_DEVICE_INDEX})")
        except OSError as e:
            self.logger.error(f"Failed to open output stream (device={OUTPUT_DEVICE_INDEX}): {e}")
            self._list_audio_devices()
            raise RuntimeError(f"Audio output device not available (device={OUTPUT_DEVICE_INDEX})") from e
        except Exception as e:
            self.logger.error(f"Unexpected error opening output stream: {e}")
            raise

        # Input Stream
        try:
            self.input_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=INPUT_CHANNELS,
                rate=self.hw_rate,
                input=True,
                frames_per_buffer=chunk * 3,  # 入力バッファも増やす
                input_device_index=INPUT_DEVICE_INDEX
            )
            self.logger.info(f"Input stream opened successfully (device={INPUT_DEVICE_INDEX})")
        except OSError as e:
            self.logger.error(f"Failed to open input stream (device={INPUT_DEVICE_INDEX}): {e}")
            self._list_audio_devices()
            # 出力ストリームが開いている場合はクリーンアップ
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            raise RuntimeError(f"Audio input device not available (device={INPUT_DEVICE_INDEX})") from e
        except Exception as e:
            self.logger.error(f"Unexpected error opening input stream: {e}")
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            raise
            
        self.chunk_size = chunk
        self.input_callback = input_callback

    def stop_stream(self):
        """
        入力および出力ストリームを停止

        ストリームを停止してクローズしますが、PyAudioインスタンスは
        再起動可能なように維持します（terminate()は呼ばない）。
        """
        self._running = False
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        # self.p.terminate() # Keep PyAudio alive for restarts

    async def record_loop(self):
        """
        入力ストリームから継続的に音声を読み取ってコールバックを呼び出す

        ハードウェアサンプルレート（48kHz）からターゲットレート（24kHz）へ
        リサンプリングした後、コールバック関数に渡します。

        録音ループ処理フロー:
            1. 入力ストリームから音声データを読み取り（48kHz）
            2. audioop.ratecvでリサンプリング（48kHz -> 24kHz）
            3. コールバック関数に渡す
            4. ループを繰り返す（_running=Falseまで）
        """
        import audioop
        self.logger.info("Starting audio record loop")
        # ループカウンターは削除（パフォーマンス向上）
        while self._running:
            if self.input_stream.get_read_available() >= self.chunk_size:
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Resample: HW Rate -> Target Rate (Downsample)
                if self.hw_rate != self.target_rate:
                    data, self.input_resample_state = audioop.ratecv(
                        data, 2, 1, self.hw_rate, self.target_rate, self.input_resample_state
                    )

                if self.input_callback:
                    # Offload processing if needed, but here we just await or call
                    if asyncio.iscoroutinefunction(self.input_callback):
                        await self.input_callback(data)
                    else:
                        self.input_callback(data)
            else:
                await asyncio.sleep(0.01)

    def play_audio(self, audio_chunk):
        """
        生のPCM音声バイトを再生

        ターゲットレート（24kHz, モノラル）からハードウェアレート（48kHz, ステレオ）へ
        リサンプリングおよびチャンネル変換した後、出力ストリームに書き込みます。

        再生処理フロー:
            1. リサンプリング（24kHz -> 48kHz）
            2. モノラル -> ステレオ変換（audioop.tostereo）
            3. 出力ストリームに書き込み

        Args:
            audio_chunk (bytes): 再生する音声データ（PCM16, 24kHz, モノラル）
        """
        import audioop
        with self._output_lock:
            if self.output_stream and self.output_stream.is_active():
                
                # Resample: Target Rate -> HW Rate (Upsample)
                if self.hw_rate != self.target_rate:
                    audio_chunk, self.output_resample_state = audioop.ratecv(
                        audio_chunk, 2, 1, self.target_rate, self.hw_rate, self.output_resample_state
                    )

                # If output is stereo (2 channels) and input is mono (from API), duplicate channels
                if self.output_channels == 2:
                    # Simple mono to stereo expansion for 16-bit audio
                    try:
                        # audioop.tostereo(fragment, width, lfactor, rfactor)
                        audio_chunk = audioop.tostereo(audio_chunk, 2, 1, 1)
                    except Exception as e:
                        self.logger.warning(f"Error upmixing audio to stereo: {e}")

                try:
                    self.output_stream.write(audio_chunk)
                except Exception as e:
                    self.logger.warning(f"Audio write error (possibly interrupted): {e}")

    def stop_playback(self):
        """
        音声再生を即座に停止する（割り込み処理用）

        割り込み時に呼び出され、現在再生中の音声を中断します。
        PyAudioストリームをフラッシュ・停止することで、内部バッファをクリアします。
        """
        with self._output_lock:
            if self.output_stream:
                try:
                    # 出力ストリームを停止してフラッシュ（バッファを即座にクリア）
                    if self.output_stream.is_active():
                        self.output_stream.stop_stream()
                    self.output_stream.start_stream()
                    self.logger.debug("Output stream stopped and restarted for interrupt")

                    # リサンプリング状態をリセット
                    self.output_resample_state = None
                except Exception as e:
                    self.logger.error(f"Error stopping playback: {e}")

    def terminate(self):
        """
        AudioHandlerを終了

        ストリームを停止し、PyAudioインスタンスを完全に終了します。
        この後、このインスタンスは再利用できません。
        """
        try:
            self.logger.info("Terminating audio handler")
            self.stop_stream()
            self.p.terminate()
            self.logger.debug("Audio handler terminated successfully")
        except Exception as e:
            self.logger.error(f"Error during audio handler termination: {e}", exc_info=True)
