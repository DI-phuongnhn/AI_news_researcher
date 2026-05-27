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

def get_rotator():
    """
    Singleton-style getter for the active ModelRotator.
    
    Ensures that multiple components share the same rotation state 
    within a single execution run.
    """
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = ModelRotator()
    return _rotator_instance.get_model()

def trigger_rotation(reason="API Limit"):
    """External trigger to force a rotation in the shared instance."""
    global _rotator_instance
    if _rotator_instance is not None:
        _rotator_instance.rotate(reason)
