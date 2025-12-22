"""
設定ファイル - アプリケーション全体の設定を管理

環境変数（.envファイル）とデフォルト値を読み込み、
各モジュールから参照される定数を定義します。
"""

import os
from dotenv import load_dotenv

# 環境変数を.envファイルから読み込み
load_dotenv()

# ================================================================================
# APIキー
# ================================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

# ================================================================================
# ファイルパス
# ================================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# モデルファイル
MODEL_FILE_PATH = os.getenv("MODEL_FILE_PATH", os.path.join(BASE_DIR, "model", "kikaikun_ja_raspberry-pi_v4_0_0.ppn"))
PORCUPINE_LANGUAGE_MODEL_PATH = os.getenv("PORCUPINE_LANGUAGE_MODEL_PATH", os.path.join(BASE_DIR, "model", "porcupine_params_ja.pv"))

# アセットディレクトリ
ASSETS_DIR = os.getenv("ASSETS_DIR", os.path.join(BASE_DIR, "assets"))
CHAR_ASSETS_DIR = os.getenv("CHAR_ASSETS_DIR", os.path.join(ASSETS_DIR, "character"))  # Live2D風キャラクターレイヤー

# ================================================================================
# オーディオ設定
# ================================================================================
# サンプルレート
SAMPLE_RATE = 24000           # OpenAI Realtime API用（24kHz）
HARDWARE_SAMPLE_RATE = 48000  # ハードウェアサンプルレート（Raspberry Piデフォルト）

# チャンネル数
INPUT_CHANNELS = 1   # 入力：モノラル（マイク）
OUTPUT_CHANNELS = 2  # 出力：ステレオ（HDMI/USB通常はステレオ）

# バッファサイズ
CHUNK_SIZE = 1024    # 1回の読み書きで処理するフレーム数

# デバイスインデックス（.envから読み込み）
# Noneの場合、PyAudioがデフォルトデバイスを選択（Raspberry Piでは失敗することが多い）
INPUT_DEVICE_INDEX = int(os.getenv("INPUT_DEVICE_INDEX", -1)) if os.getenv("INPUT_DEVICE_INDEX") else None
OUTPUT_DEVICE_INDEX = int(os.getenv("OUTPUT_DEVICE_INDEX", -1)) if os.getenv("OUTPUT_DEVICE_INDEX") else None

# デバイス名（フォールバック検索用）
# インデックスがNoneの場合、名前で検索を試みる
INPUT_DEVICE_NAME = os.getenv("INPUT_DEVICE_NAME")
OUTPUT_DEVICE_NAME = os.getenv("OUTPUT_DEVICE_NAME")

# ================================================================================
# OpenAI Realtime API設定
# ================================================================================
REALTIME_MODEL = "gpt-4o-mini-realtime-preview"
REALTIME_URL = "wss://api.openai.com/v1/realtime"

# ================================================================================
# Tavily Search API設定
# ================================================================================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
