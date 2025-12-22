"""
OpenAI Realtime APIクライアント

WebSocket経由でOpenAI Realtime API（gpt-4o-mini-realtime-preview）に接続し、
リアルタイム音声対話を実現します。音声データの送受信、トランスクリプト取得、
イベント処理をコールバックベースで管理します。
"""

import asyncio
import websockets
import json
import base64
from config import OPENAI_API_KEY, REALTIME_URL, REALTIME_MODEL


class RealtimeClient:
    """
    OpenAI Realtime API WebSocketクライアント

    WebSocket接続を管理し、音声データの送受信、イベント処理、
    セッション設定を行います。サーバーサイドVAD（Voice Activity Detection）を
    使用して、ユーザーの発話開始/終了を自動検出します。

    イベントフロー:
        送信: 音声データ（PCM16, 24kHz, Base64エンコード）
        受信: 音声デルタ、トランスクリプト、応答完了イベント

    Attributes:
        ws (websockets.WebSocketClientProtocol): WebSocket接続
        on_audio_delta (callable): 音声デルタ受信時のコールバック
        on_user_transcript (callable): ユーザートランスクリプト完了時のコールバック
        on_agent_transcript (callable): AIトランスクリプト完了時のコールバック
        on_speech_started (callable): ユーザー発話開始検知時のコールバック
        on_response_done (callable): AI応答完了時のコールバック
        session_id (str): セッションID
    """
    def __init__(self, on_audio_delta=None, on_user_transcript=None, on_agent_transcript=None, on_speech_started=None, on_response_done=None, on_response_created=None):
        """
        RealtimeClientを初期化

        Args:
            on_audio_delta (callable, optional): 音声デルタ（bytes）を受け取るコールバック
            on_user_transcript (callable, optional): ユーザーテキスト（str）を受け取るコールバック
            on_agent_transcript (callable, optional): AIテキスト（str）を受け取るコールバック
            on_speech_started (callable, optional): ユーザー発話開始時に呼ばれるコールバック
            on_response_done (callable, optional): AI応答完了時に呼ばれるコールバック
            on_response_created (callable, optional): AI応答生成開始時に呼ばれるコールバック（割り込み判定用）
        """
        self.ws = None
        self.on_audio_delta = on_audio_delta
        self.on_user_transcript = on_user_transcript
        self.on_agent_transcript = on_agent_transcript
        self.on_speech_started = on_speech_started
        self.on_response_done = on_response_done
        self.on_response_created = on_response_created
        self.session_id = None

    async def connect(self):
        """
        OpenAI Realtime APIに接続してセッションを初期化

        WebSocket接続を確立し、セッション設定（音声形式、モデル、
        サーバーVAD有効化など）を送信します。接続後、受信ループを開始します。

        セッション設定:
            - モダリティ: audio, text
            - 音声形式: PCM16, 24kHz
            - ターン検出: サーバーVAD（自動発話検知）
            - 音声: alloy
            - インストラクション: Kikai-kunとしての振る舞い

        Raises:
            websockets.exceptions.WebSocketException: 接続失敗時
        """
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
                    "type": "server_vad",
                    "threshold": 0.1,           # 音声検知の閾値（0.0-1.0、低いほど敏感）
                    "prefix_padding_ms": 300,   # 音声開始前のバッファ（ミリ秒）
                    "silence_duration_ms": 200  # 無音と判定する時間（ミリ秒、短くして反応を早く）
                }
            }
        })
        asyncio.create_task(self.receive_loop())

    async def send_event(self, event):
        """
        イベントをOpenAI Realtime APIに送信

        イベントをJSON形式でWebSocket経由で送信します。

        Args:
            event (dict): 送信するイベント（type, その他のフィールド）

        Note:
            ConnectionClosedOKは正常な切断として無視されます
        """
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
        """
        音声データをOpenAI Realtime APIに送信

        生のPCM16音声データをBase64エンコードして送信します。

        Args:
            audio_bytes (bytes): 音声データ（PCM16, 24kHz, モノラル）
        """
        # audio_bytes is raw pcm16, need to base64 encode
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        await self.send_event({
            "type": "input_audio_buffer.append",
            "audio": b64_audio
        })

    async def receive_loop(self):
        """
        WebSocketからイベントを受信し続けるループ

        OpenAI Realtime APIから送られてくるイベントを受信し、
        イベントタイプに応じて適切なコールバックを呼び出します。

        処理されるイベント:
            - response.audio.delta: 音声デルタ（Base64デコード後、コールバックに渡す）
            - input_audio_buffer.speech_started: ユーザー発話開始検知
            - conversation.item.input_audio_transcription.completed: ユーザートランスクリプト完了
            - response.audio_transcript.done: AIトランスクリプト完了
            - response.created: AI応答生成開始（割り込み判定用）
            - response.done: AI応答完了
            - error: エラーイベント

        Note:
            このメソッドはconnect()内で自動的にタスクとして起動されます
        """
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

                elif event_type == "response.created":
                    if self.on_response_created:
                        self.on_response_created()

                elif event_type == "response.done":
                    if self.on_response_done:
                        self.on_response_done()

                elif event_type == "error":
                    error_data = data.get("error", {})
                    if error_data.get("code") == "response_cancel_not_active":
                        # キャンセル失敗エラーは割り込み処理時に発生しやすいため、デバッグログに留める
                        print("[API] Info: No active response to cancel.")
                    else:
                        print(f"Realtime API Error: {data}")

        except websockets.exceptions.ConnectionClosed:
            print("Realtime API Connection Closed")
        except Exception as e:
            print(f"Error in receive loop: {e}")

    async def cancel_response(self):
        """
        現在のAI応答を中断する（割り込み処理）

        ユーザー発話開始時に呼び出され、以下の処理を行います：
        1. 進行中の応答生成を停止（response.cancel）
        2. サーバー側の音声バッファをクリア（conversation.item.truncate）
        3. 新しいユーザー入力に備える

        Note:
            この処理により、AIが喋っている最中にユーザーが話し始めた場合、
            即座にAI音声を停止し、ユーザー発話を優先することができます。
        """
        print("[API] Sending response.cancel")
        await self.send_event({
            "type": "response.cancel"
        })
        print("[API] Cancel response complete")

    async def close(self):
        """
        WebSocket接続を切断

        OpenAI Realtime APIとのWebSocket接続を正常に切断します。
        """
        if self.ws:
            await self.ws.close()
