import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('ddr_generator/.env')

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key found: {api_key[:20]}...")

genai.configure(api_key=api_key)

print("\nAvailable models that support generateContent:")
print("=" * 60)

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✓ {model.name}")
            print(f"  Display: {model.display_name}")
            print()
except Exception as e:
    print(f"Error: {e}")
