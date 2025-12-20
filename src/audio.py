import pyaudio
import asyncio
import numpy as np

class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self._running = False
        
        # Resampling states
        self.input_resample_state = None
        self.output_resample_state = None

    def start_stream(self, rate=24000, chunk=1024, input_callback=None):
        """
        Starts input and output streams.
        :param input_callback: function to call with recorded audio chunk (bytes)
        """
    def start_stream(self, rate=24000, chunk=1024, input_callback=None):
        """
        Starts input and output streams.
        :param input_callback: function to call with recorded audio chunk (bytes) at 'rate'
        """
        from config import INPUT_DEVICE_INDEX, OUTPUT_DEVICE_INDEX, INPUT_CHANNELS, OUTPUT_CHANNELS, HARDWARE_SAMPLE_RATE
        
        self._running = True
        self.output_channels = OUTPUT_CHANNELS
        self.target_rate = rate # API Rate (24k)
        self.hw_rate = HARDWARE_SAMPLE_RATE # HW Rate (48k)
        
        print(f"Opening Stream: InputIdx={INPUT_DEVICE_INDEX} (Ch={INPUT_CHANNELS}), OutputIdx={OUTPUT_DEVICE_INDEX} (Ch={OUTPUT_CHANNELS}), Rate={self.hw_rate} (Resampling from {self.target_rate})")

        # Output Stream
        try:
            self.output_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=OUTPUT_CHANNELS,
                rate=self.hw_rate,
                output=True,
                output_device_index=OUTPUT_DEVICE_INDEX
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
                frames_per_buffer=chunk * 2, # Buffer needs to be larger for higher rate? Rough approx.
                input_device_index=INPUT_DEVICE_INDEX
            )
        except Exception as e:
            print(f"Failed to open input stream: {e}")
            raise e
            
        self.chunk_size = chunk * (self.hw_rate // self.target_rate) # Adjust chunk read size
        self.input_callback = input_callback
        self.chunk_size = chunk
        self.input_callback = input_callback

    def stop_stream(self):
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
        Continuously reads from input stream and calls callback.
        """
        import audioop
        print("Starting Record Loop")
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
        Plays raw PCM audio bytes.
        """
        import audioop
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
            
            print(f"Playing chunk: {len(audio_chunk)} bytes")
            self.output_stream.write(audio_chunk)

    def terminate(self):
        self.stop_stream()
        self.p.terminate()
