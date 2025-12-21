#!/usr/bin/env python3
"""
Conversation GUI Application
Launched when wake word is detected, exits after conversation ends
"""
import asyncio
import time
from src.audio import AudioHandler
from src.realtime_client import RealtimeClient
from src.gui import GUIHandler

# State Constants
STATE_LISTENING = "LISTENING"
STATE_PROCESSING = "PROCESSING"
STATE_SPEAKING = "SPEAKING"

class ConversationApp:
    def __init__(self):
        self.state = STATE_LISTENING
        self.gui = GUIHandler()
        self.audio = AudioHandler()

        self.client = RealtimeClient(
            on_audio_delta=self.handle_audio_delta,
            on_user_transcript=self.handle_user_transcript,
            on_agent_transcript=self.handle_agent_transcript,
            on_speech_started=self.on_user_speech_start,
            on_response_done=self.on_response_done
        )

        self.audio_queue = asyncio.Queue()
        self.is_playing_response = False
        self.last_interaction_time = 0
        self.response_in_progress = False
        self.inactivity_timeout = 15.0  # 15 seconds of inactivity to exit

    async def run(self):
        print("Conversation App Started")

        # Start Audio Stream
        self.audio.start_stream(input_callback=self.audio_input_callback)
        asyncio.create_task(self.audio.record_loop())

        # Connect to OpenAI
        try:
            await self.client.connect()
            self.last_interaction_time = time.time()
            self.gui.set_state(1)  # LISTENING
            print("Connected to OpenAI Realtime API")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.gui.running = False
            return

        # Main loop
        while self.gui.running:
            self.gui.update()

            # Check inactivity timeout - exit app
            if time.time() - self.last_interaction_time > self.inactivity_timeout:
                print(f"Inactivity timeout ({self.inactivity_timeout}s). Exiting conversation.")
                self.gui.running = False
                break

            # Audio playback
            if not self.audio_queue.empty():
                self.is_playing_response = True
                self.gui.set_state(3)  # SPEAKING
                self.last_interaction_time = time.time()

                chunk = await self.audio_queue.get()
                self.audio.play_audio(chunk)
            else:
                if self.is_playing_response:
                    self.is_playing_response = False
                    self.gui.set_state(1)  # Back to LISTENING

            await asyncio.sleep(0.001)

        await self.cleanup()

    def audio_input_callback(self, in_data):
        """Send audio to OpenAI"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.client.send_audio(in_data))
        except RuntimeError:
            pass

    def on_user_speech_start(self):
        """Called when API detects user speech"""
        self.last_interaction_time = time.time()
        self.response_in_progress = False
        self.gui.set_state(2)  # PROCESSING

    def on_response_done(self):
        """Called when AI finishes a response"""
        print("Response done")
        self.response_in_progress = False
        self.last_interaction_time = time.time()

    def handle_audio_delta(self, audio_bytes):
        """Enqueue audio for playback"""
        self.last_interaction_time = time.time()
        self.response_in_progress = True
        self.audio_queue.put_nowait(audio_bytes)

    def handle_user_transcript(self, text):
        print(f"User: {text}")
        self.gui.set_user_text(text)

    def handle_agent_transcript(self, text):
        print(f"Agent: {text}")
        self.gui.set_agent_text(text)

    async def cleanup(self):
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
