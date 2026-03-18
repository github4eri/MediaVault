import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_tags(image_path):
    """Takes a path, returns comma-separated tags."""
    try:
        img = Image.open(image_path)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["List 3 to 5 simple comma-separated tags.", img]
        )
        return response.text.strip().lower() if response.text else "no-tags"
    except Exception as e:
        print(f"VISION ERROR: {e}")
        return "ai-error"