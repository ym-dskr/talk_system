"""ロギング設定

このモジュールは、talk_systemアプリケーション全体のロギング設定を管理します。
ファイル出力とコンソール出力の両方に対応し、日次ローテーションを実装しています。
"""

import logging
import re
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Redact sensitive values (e.g., bearer tokens) from log messages."""

    _patterns = (
        (re.compile(r"(Authorization\s*:\s*Bearer\s+)([^\s]+)", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(Bearer\s+)([A-Za-z0-9._-]+)"), r"\1[REDACTED]"),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True

        sanitized = message
        for pattern, replacement in self._patterns:
            sanitized = pattern.sub(replacement, sanitized)

        if sanitized != message:
            record.msg = sanitized
            record.args = ()

        return True


def setup_logging(log_dir: str = "logs", level: int = logging.INFO, file_level: Optional[int] = None):
    """
    ロギング設定を初期化

    ファイルハンドラー（日次ローテーション）とコンソールハンドラーを設定し、
    アプリケーション全体で統一されたログフォーマットを提供します。

    Args:
        log_dir: ログファイル出力ディレクトリ（デフォルト: "logs"）
        level: ログレベル（デフォルト: logging.INFO）
        file_level: ファイルログのレベル（Noneの場合はINFO以上に制限）

    Returns:
        ルートロガー

    Examples:
        >>> from src.logging_config import setup_logging
        >>> logger = setup_logging()
        >>> logger.info("Application started")

    Note:
        - ログファイルは毎日0時にローテーションされます
        - 過去7日分のログが保持されます
        - ログフォーマット: "YYYY-MM-DD HH:MM:SS [LEVEL] module:line - message"
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # フォーマッター（タイムスタンプ、レベル、モジュール名、行番号、メッセージ）
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ファイルハンドラー（日次ローテーション、7日分保持、UTF-8エンコーディング）
    file_handler = TimedRotatingFileHandler(
        log_path / "talk_system.log",
        when='midnight',
        backupCount=7,  # 7日分保持
        encoding='utf-8'  # 日本語の文字化け防止
    )
    file_handler.setFormatter(formatter)
    if file_level is None:
        file_level = max(level, logging.INFO)
    file_handler.setLevel(file_level)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 既存のハンドラーをクリア（重複を防ぐ）
    root_logger.handlers.clear()

    sensitive_filter = SensitiveDataFilter()
    file_handler.addFilter(sensitive_filter)
    console_handler.addFilter(sensitive_filter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Avoid leaking headers via verbose websocket logs.
    for logger_name in ("websockets", "websockets.client", "websockets.server", "websockets.protocol"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # 初期化完了メッセージ
    root_logger.debug(f"Logging initialized (log_dir={log_dir}, level={logging.getLevelName(level)})")

    return root_logger
