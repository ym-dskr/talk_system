#!/usr/bin/env python3
"""
Wake Word Detection Daemon
Runs in background, launches GUI app when wake word is detected
"""
import time
import struct
import subprocess
import sys

# Disable output buffering for proper logging
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), 'w', buffering=1)

from src.wake_word import WakeWordEngine
from src.audio import AudioHandler

class WakeWordDaemon:
    def __init__(self):
        self.audio = AudioHandler()
        self.wake_word = WakeWordEngine()
        self.pcm_buffer = []
        self.wake_word_resample_state = None
        self.running = True
        self.gui_process = None
        self.debug_counter = 0  # For periodic debug output

    def audio_input_callback(self, in_data):
        """Process audio input for wake word detection"""
        # Only process audio when GUI is not running
        if self.gui_process is not None:
            return

        import audioop
        # Resample 24000 -> 16000 for wake word
        try:
            resampled_data, self.wake_word_resample_state = audioop.ratecv(
                in_data, 2, 1, 24000, 16000, self.wake_word_resample_state
            )

            pcm = struct.unpack_from("h" * (len(resampled_data) // 2), resampled_data)
            self.pcm_buffer.extend(pcm)
        except Exception as e:
            print(f"[Error] Audio callback error: {e}")

    def launch_gui_app(self):
        """Launch the GUI conversation app"""
        if self.gui_process is None or self.gui_process.poll() is not None:
            print("Launching GUI conversation app...")

            # Stop audio stream to release device for GUI app
            print("Stopping audio stream...")
            self.audio.stop_stream()

            script_dir = "/home/yutapi5/Programs/talk_system"
            python_path = f"{script_dir}/.venv/bin/python3"

            self.gui_process = subprocess.Popen(
                [python_path, f"{script_dir}/conversation_app.py"],
                cwd=script_dir
            )
            print(f"GUI app launched (PID: {self.gui_process.pid})")

    async def run(self):
        """Main daemon loop"""
        import asyncio

        print("Wake Word Daemon Started")
        print("Listening for 'Kikai-kun'...")

        # Start audio stream
        # Use larger chunk for wake word (need 512 samples at 16kHz)
        # 48kHz -> 24kHz -> 16kHz: need 1536 samples at 48kHz to get 512 at 16kHz
        self.audio.start_stream(input_callback=self.audio_input_callback, chunk=1536)

        # Start audio recording loop
        asyncio.create_task(self.audio.record_loop())

        try:
            while self.running:
                # Check if GUI app is running
                if self.gui_process and self.gui_process.poll() is not None:
                    print("GUI app exited. Resuming wake word detection.")
                    self.gui_process = None
                    self.pcm_buffer = []  # Clear buffer
                    self.wake_word_resample_state = None

                    # Restart audio stream for wake word detection
                    print("Restarting audio stream...")
                    self.audio.start_stream(input_callback=self.audio_input_callback, chunk=1536)

                    # Restart record loop
                    print("Restarting record loop...")
                    asyncio.create_task(self.audio.record_loop())

                    await asyncio.sleep(0.5)  # Wait for stream to stabilize
                    print("Audio stream restarted. Listening for wake word...")

                # Process wake word only when GUI is not running
                if self.gui_process is None:
                    if len(self.pcm_buffer) >= self.wake_word.frame_length:
                        frame = self.pcm_buffer[:self.wake_word.frame_length]
                        self.pcm_buffer = self.pcm_buffer[self.wake_word.frame_length:]

                        keyword_index = self.wake_word.process(frame)
                        if keyword_index >= 0:
                            print("Wake Word Detected!")
                            self.launch_gui_app()

                    # Debug output every 500 iterations (~5 seconds)
                    self.debug_counter += 1
                    if self.debug_counter >= 500:
                        print(f"[Debug] Listening... (buffer: {len(self.pcm_buffer)} samples)")
                        self.debug_counter = 0

                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            print("\nShutting down daemon...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        if self.gui_process and self.gui_process.poll() is None:
            self.gui_process.terminate()
            self.gui_process.wait()
        self.audio.terminate()
        self.wake_word.delete()
        print("Daemon stopped")

if __name__ == "__main__":
    import asyncio
    daemon = WakeWordDaemon()
    asyncio.run(daemon.run())
