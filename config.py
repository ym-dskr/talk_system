import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE_PATH = os.path.join(BASE_DIR, "model", "kikaikun_ja_raspberry-pi_v4_0_0.ppn")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CHAR_OPEN_IMG = os.path.join(ASSETS_DIR, "char_open.png")
CHAR_CLOSED_IMG = os.path.join(ASSETS_DIR, "char_closed.png")
CHAR_ASSETS_DIR = os.path.join(ASSETS_DIR, "character")

# Audio Settings
SAMPLE_RATE = 24000  # OpenAI Realtime API default
HARDWARE_SAMPLE_RATE = 48000 # Raspberry Pi default (HDMI/USB usually 48k)
INPUT_CHANNELS = 1
OUTPUT_CHANNELS = 2 # HDMI typically requires Stereo
CHUNK_SIZE = 1024
# Device Indices (Set via .env or manual override)
# Defaulting to None allows PyAudio to choose, but often fails on Raspberry Pi
INPUT_DEVICE_INDEX = int(os.getenv("INPUT_DEVICE_INDEX", -1)) if os.getenv("INPUT_DEVICE_INDEX") else None
OUTPUT_DEVICE_INDEX = int(os.getenv("OUTPUT_DEVICE_INDEX", -1)) if os.getenv("OUTPUT_DEVICE_INDEX") else None

# Device Names (for fallback lookup)
INPUT_DEVICE_NAME = os.getenv("INPUT_DEVICE_NAME")
OUTPUT_DEVICE_NAME = os.getenv("OUTPUT_DEVICE_NAME")

# Porcupine Language Model
# Japanese model file is required if the keyword is Japanese.
PORCUPINE_LANGUAGE_MODEL_PATH = os.path.join(BASE_DIR, "model", "porcupine_params_ja.pv")

# Realtime API
REALTIME_MODEL = "gpt-4o-mini-realtime-preview"
REALTIME_URL = "wss://api.openai.com/v1/realtime"
