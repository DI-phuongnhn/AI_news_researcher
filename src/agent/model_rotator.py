from google import genai
import time
from src.config import Config

class ModelRotator:
    """
    Utility to handle Gemini API calls with automatic model rotation 
    when 429 Resource Exhausted errors occur.
    """
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.models = Config.GEMINI_MODELS_FALLBACK
        self.current_index = 0

    def generate_content(self, prompt, retry_count=0):
        if retry_count >= len(self.models):
            return "Error: All available models exhausted their quota for today."

        model_name = self.models[self.current_index]
        print(f"Using model: {model_name} (Attempt {retry_count + 1})")

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e).upper()
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print(f"Quota exhausted for {model_name}. Rotating to next model...")
                self.current_index = (self.current_index + 1) % len(self.models)
                # Wait a bit before retrying with next model
                time.sleep(2)
                return self.generate_content(prompt, retry_count + 1)
            else:
                print(f"Error with {model_name}: {e}")
                return f"Error: {e}"

def get_rotator():
    return ModelRotator(Config.GEMINI_API_KEY)
