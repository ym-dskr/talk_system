"""イベントキュー管理

このモジュールは、talk_systemアプリケーションのイベント駆動アーキテクチャを実現します。
コールバック地獄から脱却し、中央集権的なイベント処理を可能にします。
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Optional
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class EventType(Enum):
    """イベント種別定義

    アプリケーション内で発生する全てのイベントを定義します。
    """
    AUDIO_INPUT_RECEIVED = auto()      # マイクから音声受信
    AUDIO_DELTA_RECEIVED = auto()      # AI応答音声チャンク受信
    RESPONSE_STARTED = auto()          # AI応答開始
    RESPONSE_COMPLETED = auto()        # AI応答完了
    WAKE_WORD_DETECTED = auto()        # ウェイクワード検知（割り込み）
    USER_SPEECH_DETECTED = auto()      # ユーザー発話開始検知
    CONNECTION_ESTABLISHED = auto()    # WebSocket接続確立
    CONNECTION_LOST = auto()           # WebSocket切断
    ERROR_OCCURRED = auto()            # エラー発生


@dataclass
class Event:
    """イベントデータ

    イベントの種類とデータ、タイムスタンプを保持します。

    Attributes:
        type: イベント種別
        data: イベントに紐付くデータ（オプション）
        timestamp: イベント発生時刻（自動設定）

    Examples:
        >>> event = Event(EventType.WAKE_WORD_DETECTED)
        >>> event = Event(EventType.AUDIO_DELTA_RECEIVED, data=audio_bytes)
    """
    type: EventType
    data: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)


class EventQueue:
    """イベントキュー管理

    asyncio.Queueをラップし、イベントの送受信を管理します。
    デバッグログ機能を提供し、イベントフローの追跡を可能にします。

    Examples:
        >>> queue = EventQueue()
        >>> await queue.put(Event(EventType.WAKE_WORD_DETECTED))
        >>> event = await queue.get()
    """

    def __init__(self):
        """イベントキューを初期化"""
        self.queue: asyncio.Queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)

    async def put(self, event: Event):
        """イベントをキューに追加

        Args:
            event: 追加するイベント

        Examples:
            >>> await queue.put(Event(EventType.AUDIO_INPUT_RECEIVED, data=audio_data))
        """
        await self.queue.put(event)
        self.logger.debug(f"Event queued: {event.type.name}")

    async def get(self) -> Event:
        """イベントを取得（ブロッキング）

        キューが空の場合、イベントが追加されるまで待機します。

        Returns:
            取得したイベント

        Examples:
            >>> event = await queue.get()
            >>> print(event.type.name)
        """
        return await self.queue.get()

    def empty(self) -> bool:
        """キューが空かチェック

        Returns:
            True: キューが空, False: キューに要素がある

        Examples:
            >>> if queue.empty():
            ...     print("No events pending")
        """
        return self.queue.empty()

    def qsize(self) -> int:
        """キュー内のイベント数を取得

        Returns:
            キューに格納されているイベント数

        Examples:
            >>> print(f"Pending events: {queue.qsize()}")
        """
        return self.queue.qsize()
