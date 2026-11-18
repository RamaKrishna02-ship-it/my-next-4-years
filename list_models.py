
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API key not found in .env")
    raise SystemExit

client = genai.Client(api_key=api_key)

try:
    print("\nModels available to your API key:\n")

    for model in client.models.list():

        actions = model.supported_actions or []

        if "generateContent" in actions:
            print(model.name)

except Exception as error:
    print("Error listing models:")
    print(error)
