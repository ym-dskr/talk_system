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
import logging
from config import OPENAI_API_KEY, REALTIME_URL, REALTIME_MODEL
from utils.search_utils import TavilySearcher

logger = logging.getLogger(__name__)


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
    def __init__(self, on_audio_delta=None, on_user_transcript=None, on_agent_transcript=None, on_speech_started=None, on_response_done=None, on_response_created=None, max_reconnect_attempts=3, reconnect_delay=2.0):
        """
        RealtimeClientを初期化

        Args:
            on_audio_delta (callable, optional): 音声デルタ（bytes）を受け取るコールバック
            on_user_transcript (callable, optional): ユーザーテキスト（str）を受け取るコールバック
            on_agent_transcript (callable, optional): AIテキスト（str）を受け取るコールバック
            on_speech_started (callable, optional): ユーザー発話開始時に呼ばれるコールバック
            on_response_done (callable, optional): AI応答完了時に呼ばれるコールバック
            on_response_created (callable, optional): AI応答生成開始時に呼ばれるコールバック（割り込み判定用）
            max_reconnect_attempts (int, optional): 最大再接続試行回数（デフォルト: 3）
            reconnect_delay (float, optional): 再接続間隔（秒、デフォルト: 2.0）
        """
        self.ws = None
        self.on_audio_delta = on_audio_delta
        self.on_user_transcript = on_user_transcript
        self.on_agent_transcript = on_agent_transcript
        self.on_speech_started = on_speech_started
        self.on_response_done = on_response_done
        self.on_response_created = on_response_created
        self.session_id = None
        self.searcher = TavilySearcher()
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """
        OpenAI Realtime APIに接続（自動再接続付き）

        WebSocket接続を確立し、セッションを初期化します。
        接続失敗時は自動的に再接続を試行します。

        Raises:
            RuntimeError: 最大再接続試行回数を超えた場合
        """
        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                await self._connect_internal()
                self.logger.info(f"Connected to OpenAI Realtime API (attempt {attempt}/{self.max_reconnect_attempts})")
                return
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt}/{self.max_reconnect_attempts} failed: {e}")
                if attempt < self.max_reconnect_attempts:
                    self.logger.info(f"Retrying in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    self.logger.error("Failed to connect after maximum reconnection attempts")
                    raise RuntimeError(f"Failed to connect to OpenAI Realtime API after {self.max_reconnect_attempts} attempts") from e

    async def _connect_internal(self):
        """
        OpenAI Realtime APIへの内部接続処理

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
        self.logger.debug("WebSocket connection established")

        # Initialize Session
        await self.send_event({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": """
                あなたはキカイくん。たのしい工房からやってきた、やさしくてかわいいラズパイを模したロボットのアシスタントです。 
                きかいくん自身は自分のことを「きかいくん」とは言わず、「ぼく」と言う。
                話し方は、やわらかくて明るく、少しだけおちゃめなマスコットキャラクター風にしてください。 
                頭にはラズベリーがついており、おなかがすくと食べることができます。 手にはドライバーを持っているが、
                手が短くてうまく扱うことができないというおちゃめな面も。 音声での会話なので、自然で、聞き取りやすく話します。
                かわいらしい女性的な口調を心がけてください。 
                
                【重要】 
                1. 知らないこと、最新のニュース、天気、計算、特定の事実（有名人の情報、イベントの日時など）について聞かれたら、
                推測せず必ず web_search を使って調べてください。 
                2. ユーザーが「〜について教えて」「〜知ってる？」など、情報を求めている場合は積極的に検索を行ってください。
                3. 検索結果に基づいて回答する際は、情報を整理してわかりやすく「キカイくん」らしい口調で伝えてください。
                4. 「きかいくん」のワードで割り込み機能が走ってしまうので、きかいくん自身は自分のことを「きかいくん」とは言わず、「ぼく」と言う。
                """,
                

                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "tools": [
                    {
                        "type": "function",
                        "name": "web_search",
                        "description": "Search the web for real-time information, news, or facts that you don't know.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query."
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ],
                "tool_choice": "auto",
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
            try:
                await self.ws.send(json.dumps(event))
            except websockets.exceptions.ConnectionClosedOK:
                # Normal closure, ignore
                pass
            except Exception as e:
                self.logger.error(f"Error sending event {event.get('type')}: {e}")

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
                    self.logger.debug(f"Received event: {event_type}")
                    if event_type in ["response.created", "response.done", "conversation.item.created"]:
                        self.logger.debug(f"Event details: {json.dumps(data, indent=2)}")

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

                elif event_type == "response.function_call_arguments.done":
                    await self._handle_function_call(data)

                elif event_type == "error":
                    error_data = data.get("error", {})
                    if error_data.get("code") == "response_cancel_not_active":
                        # キャンセル失敗エラーは割り込み処理時に発生しやすいため、デバッグログに留める
                        self.logger.debug("No active response to cancel (expected during interrupt)")
                    else:
                        self.logger.error(f"Realtime API error: {data}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Realtime API connection closed")
        except Exception as e:
            self.logger.error(f"Error in receive loop: {e}", exc_info=True)

    async def disable_turn_detection(self):
        """
        Turn Detection（発話検知）を無効化

        AI応答中にユーザーの音声を検知しないようにします。
        これにより、AI発話中のユーザー音声がAPIに認識されず、
        意図しない応答が発生するのを防ぎます。

        Note:
            turn_detection を null に設定することで、
            サーバー側のVAD（Voice Activity Detection）を無効化します。
        """
        self.logger.debug("Disabling turn detection (VAD off)")
        await self.send_event({
            "type": "session.update",
            "session": {
                "turn_detection": None  # null で無効化
            }
        })

    async def enable_turn_detection(self):
        """
        Turn Detection（発話検知）を再有効化

        AI応答終了後、再びユーザーの音声を検知できるようにします。

        Note:
            初期設定と同じ server_vad 設定を使用します。
        """
        self.logger.debug("Enabling turn detection (VAD on)")
        await self.send_event({
            "type": "session.update",
            "session": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.1,           # 音声検知の閾値
                    "prefix_padding_ms": 300,   # 音声開始前のバッファ
                    "silence_duration_ms": 200  # 無音と判定する時間
                }
            }
        })

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
        self.logger.debug("Sending response.cancel to API")
        await self.send_event({
            "type": "response.cancel"
        })
        self.logger.debug("Response cancellation complete")

    async def _handle_function_call(self, data):
        """
        関数呼び出しの実行と結果の送信
        """
        fn_name = data.get("name")
        call_id = data.get("call_id")
        arguments_str = data.get("arguments", "{}")
        
        try:
            args = json.loads(arguments_str)
        except Exception as e:
            self.logger.error(f"Failed to parse function call arguments: {e}")
            return

        if fn_name == "web_search":
            query = args.get("query")
            self.logger.info(f"Executing web_search for: {query}")
            
            # 検索実行
            result = await self.searcher.search(query)
            
            # 検索結果を送信
            await self.send_event({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result
                }
            })
            
            # 応答の再生成を要求
            await self.send_event({"type": "response.create"})

    async def close(self):
        """
        WebSocket接続を切断

        OpenAI Realtime APIとのWebSocket接続を正常に切断します。
        """
        if self.ws:
            await self.ws.close()
