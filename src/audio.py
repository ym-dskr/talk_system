"""
オーディオ入出力ハンドラー

PyAudioを使用した音声入出力の低レベル制御を提供します。
ハードウェアサンプルレート（48kHz）とAPIサンプルレート（24kHz）間の
自動リサンプリング、モノラル/ステレオ変換を実行します。
"""

import pyaudio
import asyncio
import numpy as np
import time
import threading


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
        
        print(f"Opening Stream: InputIdx={INPUT_DEVICE_INDEX} (Ch={INPUT_CHANNELS}), OutputIdx={OUTPUT_DEVICE_INDEX} (Ch={OUTPUT_CHANNELS}), Rate={self.hw_rate} (Resampling from {self.target_rate})")

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
        except Exception as e:
            print(f"Failed to open output stream: {e}")
            raise e

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
        except Exception as e:
            print(f"Failed to open input stream: {e}")
            raise e
            
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
        print("Starting Record Loop")
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
                        print(f"Error upmixing audio: {e}")
                
                try:
                    # ログ出力を削減（パフォーマンス向上）
                    # print(f"Playing chunk: {len(audio_chunk)} bytes")
                    self.output_stream.write(audio_chunk)
                except Exception as e:
                    print(f"[AUDIO] Write error (possibly interrupted): {e}")

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
                    print("[AUDIO] Output stream stopped and restarted for barge-in")

                    # リサンプリング状態をリセット
                    self.output_resample_state = None
                except Exception as e:
                    print(f"[AUDIO] Error stopping playback: {e}")

    def terminate(self):
        """
        AudioHandlerを終了

        ストリームを停止し、PyAudioインスタンスを完全に終了します。
        この後、このインスタンスは再利用できません。
        """
        self.stop_stream()
        self.p.terminate()
