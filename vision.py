import os
import mimetypes
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. 📂 Load the .env file
load_dotenv() 

# 2. 🔐 Securely fetch the API key
api_key = os.getenv("GEMINI_API_KEY")

# 3. 🧠 Initialize the Client
if not api_key:
    # This will stop the app early if the key is missing from .env
    raise ValueError("❌ MISSION CRITICAL: GEMINI_API_KEY not found in .env file!")

client = genai.Client(api_key=api_key)

def analyze_media(file_path: str):
    """The Universal Specialist: Sees images and watches videos."""
    try:
        # Detect the type (image/jpeg, video/mp4, etc.)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Adaptive instructions based on media type
        if "video" in mime_type:
            prompt = "Watch this video and provide 5-8 descriptive tags."
        else:
            prompt = "Analyze this image and provide 5-8 descriptive tags."
        
        prompt += " Return ONLY tags separated by commas. No sentences."

        # Read file as bytes
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # 🚀 THE AI REQUEST (Indentation fixed here)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', 
            contents=[
                prompt,
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type or "image/jpeg")
            ]
        )
        
        return response.text.strip()

    except Exception as e:
        # This will show the real error in your terminal for debugging
        print(f"DEBUG: Vision Specialist Error - {e}")
        return "Vault, Media, Uncategorized"
