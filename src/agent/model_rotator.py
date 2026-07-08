"""
AI Model Rotation and Quota Management.

This module provides a mechanism to cycle through multiple Google Gemini 
API keys and model variants to maximize the efficiency of the Free Tier 
quotas (RPM/TPM limits).
"""

import os
from datetime import datetime
from src.config import Config

# Module-level singleton instance for shared model rotation.
_rotator_instance = None

class ModelRotator:
    """
    Stateful manager for rotating API credentials and AI models.
    
    This class tracks usage across multiple keys to avoid '429 Too Many Requests'
    errors which are common in high-volume research pipelines.
    """
    
    def __init__(self):
        # Load keys from Config, which extracts them from environment variables.
        self.api_keys = Config.GEMINI_API_KEYS
        self.models = Config.GEMINI_MODELS_FALLBACK
        self.current_key_index = 0
        self.current_model_index = 0
        self._active_rotator = None
        
        # --- Block: Safety Validation ---
        if not self.api_keys:
            print("  Warning: No GEMINI_API_KEYS found in configuration.")

    def get_model(self):
        """
        Initializes and returns a Gemini model instance.
        
        Uses the 'google-generativeai' library to create a GenerativeModel 
        object configured with the current rotatable API key.
        """
        import google.generativeai as genai
        
        key = self.api_keys[self.current_key_index]
        model_name = self.models[self.current_model_index]
        
        # Configure the global SDK with the selected key.
        genai.configure(api_key=key)
        
        # Log the rotation status for debugging quota issues.
        print(f"  Rotator: Initializing {model_name} (Key #{self.current_key_index + 1})")
        
        return genai.GenerativeModel(model_name)

    def rotate(self, reason: str = "quota"):
        """
        Switches to the next available API key or model.
        
        Args:
            reason: The trigger for rotation (default is 'quota' for 429 errors).
        """
        # --- Block: Key-First Rotation Strategy ---
        # We prioritize rotating through keys for a single model first,
        # as different keys often have separate RPM buckets.
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        # If we have cycled through all keys, we switch to a different model variant.
        if self.current_key_index == 0:
            self.current_model_index = (self.current_model_index + 1) % len(self.models)
            
        print(f"  Rotator: Switched due to {reason}. Now using Key #{self.current_key_index + 1}")

def _ensure_rotator_instance():
    """Lazily creates the shared ModelRotator singleton."""
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = ModelRotator()
    return _rotator_instance

def get_rotator():
    """
    Singleton-style getter for the active ModelRotator.

    Ensures that multiple components share the same rotation state
    within a single execution run.
    """
    return _ensure_rotator_instance().get_model()

def get_current_api_key():
    """
    Returns the API key currently selected by the shared rotator.

    Used by callers that need to make raw REST calls (bypassing the
    GenerativeModel wrapper), such as Google Search-grounded queries.
    """
    instance = _ensure_rotator_instance()
    if not instance.api_keys:
        return None
    return instance.api_keys[instance.current_key_index]

def trigger_rotation(reason="API Limit"):
    """External trigger to force a rotation in the shared instance."""
    global _rotator_instance
    if _rotator_instance is not None:
        _rotator_instance.rotate(reason)

def generate_content(prompt: str, max_attempts: int = None) -> str:
    """
    Generates content via the shared rotator, automatically rotating to the
    next API key/model combination on failure (e.g. 429 quota errors) and
    retrying — instead of surfacing the first failure to the caller, which
    is what happened previously since nothing ever called rotate()/
    trigger_rotation() on error.

    Args:
        prompt: The prompt to send to Gemini.
        max_attempts: Cap on retry attempts. Defaults to one attempt per
            available (key, model) combination, so every credential/model
            pairing gets tried before giving up.

    Returns:
        The generated text (already unwrapped from the response object).

    Raises:
        RuntimeError: If every combination is exhausted without success.
    """
    instance = _ensure_rotator_instance()
    if not instance.api_keys:
        raise RuntimeError("No GEMINI_API_KEYS configured.")

    if max_attempts is None:
        max_attempts = len(instance.api_keys) * len(instance.models)

    last_error = None
    for _ in range(max_attempts):
        model = instance.get_model()
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = e
            reason = "quota (429)" if "429" in str(e) else f"error ({e})"
            instance.rotate(reason)

    raise RuntimeError(f"Gemini generation failed after {max_attempts} attempts across all keys/models: {last_error}")
