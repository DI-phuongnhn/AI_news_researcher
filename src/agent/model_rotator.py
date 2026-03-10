"""
Advanced utility to handle Gemini API calls with multiple rotations.
This module provides a mechanism to cycle through multiple API keys and 
multiple Gemini models to maximize available quota in the Free Tier.
"""

from google import genai
import time
from src.config import Config

class SmartRotator:
    """
    Manages API key and model rotation to bypass rate limits.
    
    Attributes:
        api_keys (list): List of available Gemini API keys.
        models (list): List of Gemini models to use as fallbacks.
        clients (list): Pre-initialized genai.Client instances for each key.
        current_key_index (int): Pointer to the current key in use.
        current_model_index (int): Pointer to the current model in use.
    """
    
    def __init__(self):
        """Initializes the rotator with keys and models from Config."""
        self.api_keys = Config.GEMINI_API_KEYS
        self.models = Config.GEMINI_MODELS_FALLBACK
        
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEYS found in configuration.")
            
        # Pre-initialize clients for better performance during rotation
        self.clients = [genai.Client(api_key=key) for key in self.api_keys]
        
        self.current_key_index = 0
        self.current_model_index = 0

    def generate_content(self, prompt, attempt=0):
        """
        Attempts to generate content using the current key/model pair.
        Automatically rotates to the next key or model on failure.
        
        Args:
            prompt (str): The input text for the AI.
            attempt (int): Internal counter to prevent infinite retry loops.
            
        Returns:
            str: Generated text response or error message.
        """
        # Calculate total combinations to avoid infinite loops
        max_attempts = len(self.api_keys) * len(self.models)
        if attempt >= max_attempts:
            return "Error: All (API Key + Model) combinations exhausted their quota."

        current_model = self.models[self.current_model_index]
        client = self.clients[self.current_key_index]
        
        print(f"--- Calling API (Key Index: {self.current_key_index}, Model: {current_model}) ---")

        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e).upper()
            
            # Common quota/rate limit error signals
            quota_strings = ["429", "RESOURCE_EXHAUSTED", "QUOTA", "REMITTER_LIMIT", "RATE_LIMIT"]
            
            if any(qs in err_msg for qs in quota_strings):
                print(f"!!! QUOTA REACHED for Key {self.current_key_index} on {current_model}.")
                
                # ROTATION STRATEGY:
                # 1. Try next API Key for the SAME model (horizontal scaling)
                # 2. If all keys fail for this model, move to NEXT model and reset key to 0 (vertical scaling)
                self.current_key_index += 1
                if self.current_key_index >= len(self.api_keys):
                    print("!!! All keys exhausted for this model. Switching to NEXT MODEL...")
                    self.current_key_index = 0
                    self.current_model_index = (self.current_model_index + 1) % len(self.models)
                
                # Brief settle time to avoid rapid-fire failures
                time.sleep(2)
                return self.generate_content(prompt, attempt + 1)
            else:
                # Handle 404/Not Found for specific models that might be deprecated/restricted
                if "404" in err_msg or "NOT FOUND" in err_msg:
                    print(f"!!! Model {current_model} not available. Trying next model...")
                    self.current_key_index = 0 
                    self.current_model_index = (self.current_model_index + 1) % len(self.models)
                    return self.generate_content(prompt, attempt + 1)
                
                return f"Execution failed: {e}"

# Singleton instance to persist rotation state across module imports
_rotator_instance = None

def get_rotator():
    """
    Returns the global SmartRotator instance.
    Ensures that rotation state is shared across all parts of the application.
    """
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = SmartRotator()
    return _rotator_instance
