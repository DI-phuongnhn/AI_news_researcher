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
            quota_strings = ["429", "RESOURCE_EXHAUSTED", "QUOTA", "REMITTER_LIMIT", "RATE_LIMIT"]
            
            if any(qs in err_msg for qs in quota_strings):
                print(f"!!! QUOTA REACHED for {model_name}. Attempting rotation...")
                self.current_index = (self.current_index + 1) % len(self.models)
                # Wait 5 seconds to let things settle
                time.sleep(5)
                return self.generate_content(prompt, retry_count + 1)
            else:
                print(f"!!! NON-QUOTA ERROR with {model_name}: {e}")
                # If it's a 404 or something, maybe also try next model?
                if "404" in err_msg or "NOT FOUND" in err_msg:
                    print(f"Model {model_name} not found. Trying next...")
                    self.current_index = (self.current_index + 1) % len(self.models)
                    return self.generate_content(prompt, retry_count + 1)
                
                return f"Model {model_name} failed: {e}"

def get_rotator():
    return ModelRotator(Config.GEMINI_API_KEY)
