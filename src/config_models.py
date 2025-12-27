"""
設定モデル - Pydanticベースの型安全な設定管理

このモジュールは、アプリケーション全体の設定を型安全に管理します。
環境変数（.envファイル）から自動的に読み込まれ、デフォルト値とバリデーションを提供します。
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioConfig(BaseModel):
    """
    音声設定

    音声入出力に関する設定を管理します。
    サンプルレート、チャンネル数、デバイスインデックスなどを含みます。

    Attributes:
        sample_rate: アプリケーション側のサンプルレート（24kHz）
        hardware_sample_rate: ハードウェアサンプルレート（48kHz）
        input_channels: 入力チャンネル数（モノラル: 1）
        output_channels: 出力チャンネル数（ステレオ: 2）
        chunk_size: バッファサイズ（フレーム数）
        input_device_index: 入力デバイスインデックス
        output_device_index: 出力デバイスインデックス
        input_device_name: 入力デバイス名（フォールバック検索用）
        output_device_name: 出力デバイス名（フォールバック検索用）
    """
    sample_rate: int = Field(default=24000, description="OpenAI Realtime API用サンプルレート")
    hardware_sample_rate: int = Field(default=48000, description="ハードウェアサンプルレート")
    input_channels: int = Field(default=1, description="入力チャンネル数（モノラル）")
    output_channels: int = Field(default=2, description="出力チャンネル数（ステレオ）")
    chunk_size: int = Field(default=1024, description="バッファサイズ（フレーム数）")
    input_device_index: Optional[int] = Field(default=None, description="入力デバイスインデックス")
    output_device_index: Optional[int] = Field(default=None, description="出力デバイスインデックス")
    input_device_name: Optional[str] = Field(default=None, description="入力デバイス名")
    output_device_name: Optional[str] = Field(default=None, description="出力デバイス名")


class RealtimeAPIConfig(BaseModel):
    """
    OpenAI Realtime API設定

    Realtime APIへの接続に関する設定を管理します。

    Attributes:
        model: 使用するモデル名
        url: WebSocket接続URL
        max_reconnect_attempts: 最大再接続試行回数
        reconnect_delay: 再接続間隔（秒）
    """
    model: str = Field(default="gpt-4o-mini-realtime-preview", description="Realtime APIモデル")
    url: str = Field(default="wss://api.openai.com/v1/realtime", description="WebSocket URL")
    max_reconnect_attempts: int = Field(default=3, description="最大再接続試行回数")
    reconnect_delay: float = Field(default=2.0, description="再接続間隔（秒）")


class PathsConfig(BaseModel):
    """
    ファイルパス設定

    モデルファイル、アセットディレクトリなどのパスを管理します。

    Attributes:
        base_dir: プロジェクトルートディレクトリ
        model_file: ウェイクワードモデルファイルパス
        porcupine_language_model: Porcupine言語モデルパス
        assets_dir: アセットディレクトリ
        char_assets_dir: キャラクターアセットディレクトリ
    """
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent, description="ベースディレクトリ")
    model_file: Path = Field(default=None, description="ウェイクワードモデルファイル")
    porcupine_language_model: Path = Field(default=None, description="Porcupine言語モデル")
    assets_dir: Path = Field(default=None, description="アセットディレクトリ")
    char_assets_dir: Path = Field(default=None, description="キャラクターアセットディレクトリ")

    def __init__(self, **data):
        super().__init__(**data)
        # デフォルトパスを設定
        if self.model_file is None:
            self.model_file = self.base_dir / "model" / "kikaikun_ja_raspberry-pi_v4_0_0.ppn"
        if self.porcupine_language_model is None:
            self.porcupine_language_model = self.base_dir / "model" / "porcupine_params_ja.pv"
        if self.assets_dir is None:
            self.assets_dir = self.base_dir / "assets"
        if self.char_assets_dir is None:
            self.char_assets_dir = self.assets_dir / "character"


class AppConfig(BaseSettings):
    """
    アプリケーション全体設定

    環境変数から自動的に読み込まれる、アプリケーション全体の設定を管理します。
    .env ファイルからの読み込みに対応しています。

    Attributes:
        openai_api_key: OpenAI APIキー
        picovoice_access_key: Picovoice APIキー
        tavily_api_key: Tavily Search APIキー（オプション）
        audio: 音声設定
        realtime: Realtime API設定
        paths: ファイルパス設定
        inactivity_timeout: 無操作タイムアウト（秒）

    Examples:
        >>> from src.config_models import AppConfig
        >>> config = AppConfig()
        >>> print(config.audio.sample_rate)
        24000
        >>> print(config.realtime.model)
        gpt-4o-mini-realtime-preview
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )

    # APIキー
    openai_api_key: str = Field(..., description="OpenAI APIキー")
    picovoice_access_key: str = Field(..., description="Picovoice APIキー")
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily Search APIキー")

    # ネストされた設定
    audio: AudioConfig = Field(default_factory=AudioConfig, description="音声設定")
    realtime: RealtimeAPIConfig = Field(default_factory=RealtimeAPIConfig, description="Realtime API設定")
    paths: PathsConfig = Field(default_factory=PathsConfig, description="パス設定")

    # アプリケーション設定
    inactivity_timeout: float = Field(default=180.0, description="無操作タイムアウト（秒）")

    def __init__(self, **data):
        super().__init__(**data)
        # 環境変数から個別設定を読み込み
        self._load_audio_config_from_env()
        self._load_paths_config_from_env()

    def _load_audio_config_from_env(self):
        """環境変数から音声設定を読み込み"""
        import os

        # デバイスインデックスの読み込み
        if os.getenv("INPUT_DEVICE_INDEX"):
            try:
                self.audio.input_device_index = int(os.getenv("INPUT_DEVICE_INDEX"))
            except ValueError:
                pass

        if os.getenv("OUTPUT_DEVICE_INDEX"):
            try:
                self.audio.output_device_index = int(os.getenv("OUTPUT_DEVICE_INDEX"))
            except ValueError:
                pass

        # デバイス名の読み込み
        if os.getenv("INPUT_DEVICE_NAME"):
            self.audio.input_device_name = os.getenv("INPUT_DEVICE_NAME")

        if os.getenv("OUTPUT_DEVICE_NAME"):
            self.audio.output_device_name = os.getenv("OUTPUT_DEVICE_NAME")

    def _load_paths_config_from_env(self):
        """環境変数からパス設定を読み込み"""
        import os

        if os.getenv("MODEL_FILE_PATH"):
            self.paths.model_file = Path(os.getenv("MODEL_FILE_PATH"))

        if os.getenv("PORCUPINE_LANGUAGE_MODEL_PATH"):
            self.paths.porcupine_language_model = Path(os.getenv("PORCUPINE_LANGUAGE_MODEL_PATH"))

        if os.getenv("ASSETS_DIR"):
            self.paths.assets_dir = Path(os.getenv("ASSETS_DIR"))

        if os.getenv("CHAR_ASSETS_DIR"):
            self.paths.char_assets_dir = Path(os.getenv("CHAR_ASSETS_DIR"))
