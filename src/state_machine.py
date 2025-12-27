"""アプリケーション状態管理

このモジュールは、talk_systemアプリケーションの状態遷移を明示的に管理します。
状態遷移を明確化することで、デバッグ可能性とコードの保守性を向上させます。
"""

from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)


class AppState(Enum):
    """
    アプリケーション状態定義

    Attributes:
        IDLE: 待機中（ウェイクワード待ち）
        LISTENING: 聞いている（ユーザー音声受付中）
        PROCESSING: 考え中（AI応答生成中）
        SPEAKING: 発話中（音声出力中）
        ERROR: エラー状態（復旧処理中）
    """
    IDLE = auto()        # 待機中（ウェイクワード待ち）
    LISTENING = auto()   # 聞いている（ユーザー音声受付中）
    PROCESSING = auto()  # 考え中（AI応答生成中）
    SPEAKING = auto()    # 発話中（音声出力中）
    ERROR = auto()       # エラー状態（復旧処理中）


class StateTransition:
    """
    状態遷移管理

    アプリケーションの状態遷移ルールを定義し、
    不正な状態遷移を検出します。
    """

    # 許可される状態遷移の定義
    # 各状態から遷移可能な状態のセット
    ALLOWED_TRANSITIONS = {
        AppState.IDLE: {AppState.LISTENING, AppState.ERROR},
        AppState.LISTENING: {AppState.PROCESSING, AppState.ERROR},
        AppState.PROCESSING: {AppState.SPEAKING, AppState.ERROR},
        AppState.SPEAKING: {AppState.LISTENING, AppState.PROCESSING, AppState.ERROR},
        AppState.ERROR: {AppState.IDLE, AppState.LISTENING}
    }

    @classmethod
    def is_valid_transition(cls, from_state: AppState, to_state: AppState) -> bool:
        """
        状態遷移の妥当性チェック

        Args:
            from_state: 現在の状態
            to_state: 遷移先の状態

        Returns:
            True: 遷移可能, False: 遷移不可

        Examples:
            >>> StateTransition.is_valid_transition(AppState.IDLE, AppState.LISTENING)
            True
            >>> StateTransition.is_valid_transition(AppState.IDLE, AppState.SPEAKING)
            False
        """
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def get_allowed_transitions(cls, from_state: AppState) -> set:
        """
        指定した状態から遷移可能な状態の一覧を取得

        Args:
            from_state: 現在の状態

        Returns:
            遷移可能な状態のセット

        Examples:
            >>> transitions = StateTransition.get_allowed_transitions(AppState.IDLE)
            >>> AppState.LISTENING in transitions
            True
        """
        return cls.ALLOWED_TRANSITIONS.get(from_state, set())
