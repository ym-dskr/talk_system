import asyncio
import websockets
import json
import base64
from config import OPENAI_API_KEY, REALTIME_URL, REALTIME_MODEL

class RealtimeClient:
    def __init__(self, on_audio_delta=None, on_user_transcript=None, on_agent_transcript=None, on_speech_started=None, on_response_done=None):
        self.ws = None
        self.on_audio_delta = on_audio_delta
        self.on_user_transcript = on_user_transcript
        self.on_agent_transcript = on_agent_transcript
        self.on_speech_started = on_speech_started
        self.on_response_done = on_response_done
        self.session_id = None

    async def connect(self):
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        url = f"{REALTIME_URL}?model={REALTIME_MODEL}"
        self.ws = await websockets.connect(url, additional_headers=headers)
        print("Connected to OpenAI Realtime API")
        
        # Initialize Session
        await self.send_event({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "You are Kikai-kun, a friendly and helpful mechanical assistant. Keep your responses concise and conversational. You are chatting via voice.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad"
                }
            }
        })
        asyncio.create_task(self.receive_loop())

    async def send_event(self, event):
        if self.ws:
            # print(f"Sending Event: {event.get('type')}") # Too noisy for audio append
            try:
                await self.ws.send(json.dumps(event))
            except websockets.exceptions.ConnectionClosedOK:
                # Normal closure, ignore
                pass
            except Exception as e:
                print(f"Error sending event: {e}")

    async def send_audio(self, audio_bytes):
        # audio_bytes is raw pcm16, need to base64 encode
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        await self.send_event({
            "type": "input_audio_buffer.append",
            "audio": b64_audio
        })

    async def receive_loop(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                event_type = data.get("type")
                
                if event_type != "response.audio.delta":
                    print(f"Received Event: {event_type}")
                    if event_type in ["response.created", "response.done", "conversation.item.created"]:
                        print(json.dumps(data, indent=2))

                if event_type == "response.audio.delta":
                    delta = data.get("delta")
                    if delta and self.on_audio_delta:
                        audio_bytes = base64.b64decode(delta)
                        self.on_audio_delta(audio_bytes)

                elif event_type == "input_audio_buffer.speech_started":
                    if self.on_speech_started:
                        self.on_speech_started()

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    if self.on_user_transcript:
                        self.on_user_transcript(data.get("transcript"))

                elif event_type == "response.audio_transcript.done":
                    if self.on_agent_transcript:
                        self.on_agent_transcript(data.get("transcript"))

                elif event_type == "response.done":
                    if self.on_response_done:
                        self.on_response_done()

                elif event_type == "error":
                    print(f"Realtime API Error: {data}")

        except websockets.exceptions.ConnectionClosed:
            print("Realtime API Connection Closed")
        except Exception as e:
            print(f"Error in receive loop: {e}")

    async def close(self):
        if self.ws:
            await self.ws.close()
