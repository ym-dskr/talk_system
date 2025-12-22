"""
talk_system - Raspberry Pi上で動作するリアルタイム音声対話システム

このパッケージは、Picovoiceウェイクワード検知とOpenAI Realtime APIを組み合わせ、
ウェイクワード「Kikai-kun（キカイくん）」で起動する音声対話システムを提供します。

主要モジュール:
- audio: PyAudioベースの音声入出力ハンドラー
- realtime_client: OpenAI Realtime API WebSocketクライアント
- wake_word: Picovoice Porcupineベースのウェイクワード検知エンジン
- gui: Pygameベースのフルスクリーン表示とアニメーション管理

システムアーキテクチャ:
1. wake_word_daemon.py: バックグラウンドでウェイクワード検知
2. conversation_app.py: 検知後にGUIアプリを起動して音声対話
"""

from .audio import AudioHandler
from .realtime_client import RealtimeClient
from .wake_word import WakeWordEngine
from .gui import GUIHandler

__all__ = [
    'AudioHandler',
    'RealtimeClient',
    'WakeWordEngine',
    'GUIHandler',
]

__version__ = '1.0.0'
