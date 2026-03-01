import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel(model_name="gemini-1.5-flash-8b")
    response = model.generate_content("Hello")
    print("SUCCESS: ", response.text)
except Exception as e:
    print(f"FAILED: {e}")
