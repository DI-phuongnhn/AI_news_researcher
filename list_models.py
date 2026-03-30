import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS", "").split(",")[0]
genai.configure(api_key=api_key)

print("Available Models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
