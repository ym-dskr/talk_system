"""
設定ファイル - アプリケーション全体の設定を管理

Phase 2.1で型安全なpydanticベースの設定管理に移行しました。
このファイルは後方互換性のために、既存のコードが引き続き動作するよう
定数としてエクスポートしています。

新しいコードでは、src.config_models.AppConfig を使用することを推奨します。
"""

import os
from dotenv import load_dotenv

# 環境変数を.envファイルから読み込み
load_dotenv()

# ================================================================================
# 新しい型安全な設定管理（Phase 2.1+）
# ================================================================================
try:
    from src.config_models import AppConfig

    # グローバル設定インスタンスを作成
    # 環境変数がない場合のためにダミー値を提供
    _app_config = AppConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        picovoice_access_key=os.getenv("PICOVOICE_ACCESS_KEY", "")
    )
except Exception:
    # フォールバック: pydanticが利用できない場合
    _app_config = None

# ================================================================================
# 後方互換性のための定数エクスポート
# ================================================================================

# APIキー
if _app_config:
    OPENAI_API_KEY = _app_config.openai_api_key
    PICOVOICE_ACCESS_KEY = _app_config.picovoice_access_key
    TAVILY_API_KEY = _app_config.tavily_api_key
else:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ファイルパス
if _app_config:
    BASE_DIR = str(_app_config.paths.base_dir)
    MODEL_FILE_PATH = str(_app_config.paths.model_file)
    PORCUPINE_LANGUAGE_MODEL_PATH = str(_app_config.paths.porcupine_language_model)
    ASSETS_DIR = str(_app_config.paths.assets_dir)
    CHAR_ASSETS_DIR = str(_app_config.paths.char_assets_dir)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MODEL_FILE_PATH = os.getenv("MODEL_FILE_PATH", os.path.join(BASE_DIR, "model", "kikaikun_ja_raspberry-pi_v4_0_0.ppn"))
    PORCUPINE_LANGUAGE_MODEL_PATH = os.getenv("PORCUPINE_LANGUAGE_MODEL_PATH", os.path.join(BASE_DIR, "model", "porcupine_params_ja.pv"))
    ASSETS_DIR = os.getenv("ASSETS_DIR", os.path.join(BASE_DIR, "assets"))
    CHAR_ASSETS_DIR = os.getenv("CHAR_ASSETS_DIR", os.path.join(ASSETS_DIR, "character"))

# オーディオ設定
if _app_config:
    SAMPLE_RATE = _app_config.audio.sample_rate
    HARDWARE_SAMPLE_RATE = _app_config.audio.hardware_sample_rate
    INPUT_CHANNELS = _app_config.audio.input_channels
    OUTPUT_CHANNELS = _app_config.audio.output_channels
    CHUNK_SIZE = _app_config.audio.chunk_size
    INPUT_DEVICE_INDEX = _app_config.audio.input_device_index
    OUTPUT_DEVICE_INDEX = _app_config.audio.output_device_index
    INPUT_DEVICE_NAME = _app_config.audio.input_device_name
    OUTPUT_DEVICE_NAME = _app_config.audio.output_device_name
else:
    SAMPLE_RATE = 24000
    HARDWARE_SAMPLE_RATE = 48000
    INPUT_CHANNELS = 1
    OUTPUT_CHANNELS = 2
    CHUNK_SIZE = 1024
    INPUT_DEVICE_INDEX = int(os.getenv("INPUT_DEVICE_INDEX", -1)) if os.getenv("INPUT_DEVICE_INDEX") else None
    OUTPUT_DEVICE_INDEX = int(os.getenv("OUTPUT_DEVICE_INDEX", -1)) if os.getenv("OUTPUT_DEVICE_INDEX") else None
    INPUT_DEVICE_NAME = os.getenv("INPUT_DEVICE_NAME")
    OUTPUT_DEVICE_NAME = os.getenv("OUTPUT_DEVICE_NAME")

# OpenAI Realtime API設定
if _app_config:
    REALTIME_MODEL = _app_config.realtime.model
    REALTIME_URL = _app_config.realtime.url
else:
    REALTIME_MODEL = "gpt-4o-mini-realtime-preview"
    REALTIME_URL = "wss://api.openai.com/v1/realtime"
