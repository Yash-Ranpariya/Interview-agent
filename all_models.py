import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
print("--- ALL MODELS ---")
try:
    models = list(genai.list_models())
    for m in models:
        print(f"Name: {m.name}")
except Exception as e:
    print(f"Error: {e}")
