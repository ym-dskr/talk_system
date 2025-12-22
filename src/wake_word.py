"""
ウェイクワード検知エンジン

Picovoice Porcupineを使用して、カスタムウェイクワード「Kikai-kun（キカイくん）」を
検知します。日本語モデルを使用し、フォールバック機能を備えています。
"""

import pvporcupine
import struct
import platform
from config import PICOVOICE_ACCESS_KEY, MODEL_FILE_PATH


class WakeWordEngine:
    """
    Picovoice Porcupineベースのウェイクワード検知エンジン

    カスタムキーワードモデル（kikaikun_ja_raspberry-pi）と
    日本語言語モデルを使用してウェイクワードを検知します。

    モデルファイルが見つからない場合は標準キーワードにフォールバックします。

    音声入力要件:
        - サンプルレート: 16kHz
        - フレーム長: 512サンプル（process()に渡すデータサイズ）
        - フォーマット: int16（-32768 ~ 32767）

    Attributes:
        porcupine (pvporcupine.Porcupine): Porcupineエンジンインスタンス
    """
    def __init__(self):
        """
        WakeWordEngineを初期化

        Picovoiceエンジンを初期化し、カスタムキーワードモデルと
        日本語言語モデルを読み込みます。

        初期化フロー:
            1. PICOVOICE_ACCESS_KEYの検証
            2. カスタムキーワードモデル（.ppn）の読み込み
            3. 日本語言語モデル（.pv）の読み込み（存在する場合）
            4. 失敗時は標準キーワード（picovoice）にフォールバック

        Raises:
            ValueError: PICOVOICE_ACCESS_KEYが設定されていない場合
            Exception: カスタムモデルと標準キーワード両方の読み込みに失敗した場合
        """
        if not PICOVOICE_ACCESS_KEY:
            raise ValueError("PICOVOICE_ACCESS_KEY is not set")

        # Check if model file exists, otherwise fallback (or fail gracefully for dev)
        keyword_paths = [MODEL_FILE_PATH]

        try:
            # Check if Japanese model exists, otherwise warn
            from config import PORCUPINE_LANGUAGE_MODEL_PATH
            import os

            kwargs = {
                'access_key': PICOVOICE_ACCESS_KEY,
                'keyword_paths': keyword_paths
            }

            if os.path.exists(PORCUPINE_LANGUAGE_MODEL_PATH):
                kwargs['model_path'] = PORCUPINE_LANGUAGE_MODEL_PATH
            else:
                print(f"WARNING: Japanese model file not found at {PORCUPINE_LANGUAGE_MODEL_PATH}.")
                print("Wake word detection WILL FAIL if keyword is Japanese but model is English.")

            self.porcupine = pvporcupine.create(**kwargs)
        except Exception as e:
            print(f"Error loading custom model: {e}")
            print("Falling back to default 'porcupine' keyword for testing if available, or raising error.")
            # Fallback to standard keywords if custom fails (for development environments without the specific Pi model)
            try:
                self.porcupine = pvporcupine.create(
                    access_key=PICOVOICE_ACCESS_KEY,
                    keywords=['picovoice']  # Fallback
                )
            except:
                raise e

    def process(self, pcm):
        """
        音声データチャンクを処理してウェイクワードを検知

        Args:
            pcm (list[int]): 音声サンプルのリスト（int16, 長さはframe_lengthと一致必要）

        Returns:
            int: ウェイクワード検知時はキーワードインデックス（0以上）、
                 未検知時は-1

        Note:
            pcmの長さは必ずframe_length（通常512サンプル）と一致する必要があります
        """
        return self.porcupine.process(pcm)

    @property
    def frame_length(self):
        return self.porcupine.frame_length

    @property
    def sample_rate(self):
        return self.porcupine.sample_rate

    def delete(self):
        if self.porcupine:
            self.porcupine.delete()
