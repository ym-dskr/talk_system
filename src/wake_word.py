import pvporcupine
import struct
import platform
from config import PICOVOICE_ACCESS_KEY, MODEL_FILE_PATH

class WakeWordEngine:
    def __init__(self):
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
                    keywords=['picovoice'] # Fallback
                )
            except:
                raise e

    def process(self, pcm):
        """
        Process a chunk of audio data.
        :param pcm: list of integers (audio samples)
        :return: keyword_index if detected, -1 otherwise
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
