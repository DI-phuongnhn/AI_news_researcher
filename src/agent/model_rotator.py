from google import genai
import time
from src.config import Config

class SmartRotator:
    """
    Advanced utility to handle Gemini API calls with both API Key rotation
     AND Model rotation to maximize Free Tier quota.
    """
    def __init__(self):
        self.api_keys = Config.GEMINI_API_KEYS
        self.models = Config.GEMINI_MODELS_FALLBACK
        
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEYS found in configuration.")
            
        # Create clients for all keys
        self.clients = [genai.Client(api_key=key) for key in self.api_keys]
        
        self.current_key_index = 0
        self.current_model_index = 0

    def generate_content(self, prompt, attempt=0):
        # Calculate total combinations to avoid infinite loops
        max_attempts = len(self.api_keys) * len(self.models)
        if attempt >= max_attempts:
            return "Error: All (API Key + Model) combinations exhausted their quota."

        current_key = self.api_keys[self.current_key_index]
        model_name = self.models[self.current_model_index]
        client = self.clients[self.current_key_index]
        
        print(f"--- Calling API (Key Index: {self.current_key_index}, Model: {model_name}) ---")

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e).upper()
            quota_strings = ["429", "RESOURCE_EXHAUSTED", "QUOTA", "REMITTER_LIMIT", "RATE_LIMIT"]
            
            if any(qs in err_msg for qs in quota_strings):
                print(f"!!! QUOTA REACHED for Key {self.current_key_index} on {model_name}.")
                
                # ROTATION LOGIC:
                # 1. Try next API Key for the SAME model
                # 2. if all keys fail for this model, move to NEXT model and reset key to 0
                
                self.current_key_index += 1
                if self.current_key_index >= len(self.api_keys):
                    print("!!! All keys exhausted for this model. Switching to NEXT MODEL...")
                    self.current_key_index = 0
                    self.current_model_index = (self.current_model_index + 1) % len(self.models)
                
                # Settle time
                time.sleep(2)
                return self.generate_content(prompt, attempt + 1)
            else:
                # Handle 404/Not Found for specific models
                if "404" in err_msg or "NOT FOUND" in err_msg:
                    print(f"!!! Model {model_name} not available. Trying next model...")
                    self.current_key_index = 0 # Reset to first key for new model
                    self.current_model_index = (self.current_model_index + 1) % len(self.models)
                    return self.generate_content(prompt, attempt + 1)
                
                return f"Execution failed: {e}"

_rotator_instance = None

def get_rotator():
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = SmartRotator()
    return _rotator_instance
