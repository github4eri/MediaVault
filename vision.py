import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_image(image_path: str):
    """
    The Analyst: Uses the modern Gemini Client to generate tags.
    """
    try:
        # 📸 2. Open the image
        img = Image.open(image_path)
        
        # 🤖 3. Call the Gemini 1.5 Flash model
        # Note: 'models.generate_content' is the syntax for the new genai Client
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=["Provide a comma-separated list of 5-10 descriptive tags for this image.", img]
        )
        
        # 🧼 4. Return the text (cleanly)
        return response.text.strip()

    except Exception as e:
        print(f"DEBUG: AI Specialist Error - {e}")
        return "AI-Analysis-Unavailable"