
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

client = genai.Client(api_key=api_key)

print("Testing Gemini model:", model)

try:
    response = client.models.generate_content(
        model=model,
        contents="Explain how AI works in three simple sentences."
    )

    print("\nGemini connection successful!")
    print(response.text)

except Exception as error:
    print("\nGemini connection failed:")
    print(error)

