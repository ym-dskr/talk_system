import time

if __name__ == "__main__":
    import asyncio
    import sys
    import struct
    import numpy as np
    from src.wake_word import WakeWordEngine
    from src.audio import AudioHandler
    from src.realtime_client import RealtimeClient
    from src.gui import GUIHandler

    # State Constants
    STATE_IDLE = "IDLE"
    STATE_LISTENING = "LISTENING"
    STATE_PROCESSING = "PROCESSING"
    STATE_SPEAKING = "SPEAKING"

    class Application:
        def __init__(self):
            self.state = STATE_IDLE
            self.gui = GUIHandler()
            self.audio = AudioHandler()
            self.wake_word = WakeWordEngine()
            
            # Pass on_speech_started to track user activity
            self.client = RealtimeClient(
                on_audio_delta=self.handle_audio_delta,
                on_user_transcript=lambda t: print(f"User: {t}"),
                on_agent_transcript=lambda t: print(f"Agent: {t}"),
                on_speech_started=self.on_user_speech_start
            )
            self.audio_queue = asyncio.Queue()
            self.is_playing_response = False
            
            # Buffer to hold recent audio for wake word
            self.pcm_buffer = [] 
            
            # Resampler for Wake Word (24000 -> 16000)
            self.wake_word_resample_state = None 
            
            self.last_interaction_time = 0

        async def run(self):
            # Start Audio Stream
            self.audio.start_stream(input_callback=self.audio_input_callback)
            asyncio.create_task(self.audio.record_loop())
            
            print("Application Started. Say 'Kikai-kun' to wake up.")

            while self.gui.running:
                # 1. Update GUI
                self.gui.update()
                
                # Check Timeout (10 seconds)
                if self.state != STATE_IDLE:
                    if time.time() - self.last_interaction_time > 10.0:
                        print("Timeout: Auto-ending conversation.")
                        self.gui.running = False # Exit application

                # 2. Process Wake Word (if IDLE)
                if self.state == STATE_IDLE:
                    if len(self.pcm_buffer) >= self.wake_word.frame_length:
                        # Process frame
                        frame = self.pcm_buffer[:self.wake_word.frame_length]
                        self.pcm_buffer = self.pcm_buffer[self.wake_word.frame_length:]
                        
                        keyword_index = self.wake_word.process(frame)
                        if keyword_index >= 0:
                            print("Wake Word Detected!")
                            await self.start_conversation()

                # 3. Audio Playback Loop (De-queueing)
                if not self.audio_queue.empty():
                    self.is_playing_response = True
                    self.gui.set_state(3) # SPEAKING
                    
                    # Update timer while speaking so we don't timeout during long response
                    self.last_interaction_time = time.time()
                    
                    chunk = await self.audio_queue.get()
                    # Play audio
                    self.audio.play_audio(chunk)
                else:
                    if self.is_playing_response:
                        self.is_playing_response = False
                        # If queue empty, go back to LISTENING (1)
                        if self.state != STATE_IDLE:
                            self.gui.set_state(1)
                
                await asyncio.sleep(0.001)

            await self.cleanup()

        async def start_conversation(self):
            self.state = STATE_LISTENING
            self.gui.set_state(1) # LISTENING (Green)
            
            try:
                await self.client.connect()
                # Reset timer AFTER connection is established to avoid immediate timeout
                self.last_interaction_time = time.time()
            except Exception as e:
                print(f"Failed to connect: {e}")
                self.state = STATE_IDLE
                self.gui.set_state(0)
                await self.reset_to_idle()

        async def reset_to_idle(self):
            print("Resetting to IDLE")
            self.state = STATE_IDLE
            self.gui.set_state(0) # IDLE
            await self.client.close()
            # clear buffer
            while not self.audio_queue.empty():
                self.audio_queue.get_nowait()
            self.pcm_buffer = []

        def on_user_speech_start(self):
            # Called when API detects user speech
            # print("User speech started")
            self.last_interaction_time = time.time()
            if self.state != STATE_IDLE:
                self.gui.set_state(2) # PROCESSING (Yellow) - indicating we hear you

        def audio_input_callback(self, in_data):
            if self.state == STATE_IDLE:
                 import audioop
                 resampled_data, self.wake_word_resample_state = audioop.ratecv(
                     in_data, 2, 1, 24000, 16000, self.wake_word_resample_state
                 )
                 
                 pcm = struct.unpack_from("h" * (len(resampled_data) // 2), resampled_data)
                 self.pcm_buffer.extend(pcm)
            
            elif self.state == STATE_LISTENING or self.state == STATE_SPEAKING:
                # Send to OpenAI
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.client.send_audio(in_data))
                except RuntimeError:
                    pass 

        def handle_audio_delta(self, audio_bytes):
            # Enqueue for playback
            # print(f"Received Audio Chunk: {len(audio_bytes)} bytes") 
            self.last_interaction_time = time.time() # Reset timer on receiving content
            self.audio_queue.put_nowait(audio_bytes)

        async def cleanup(self):
            print("Cleaning up...")
            await self.client.close()
            self.audio.terminate()
            self.wake_word.delete()
            self.gui.quit()

    if __name__ == "__main__":
        app = Application()
        try:
            asyncio.run(app.run())
        except KeyboardInterrupt:
            pass
