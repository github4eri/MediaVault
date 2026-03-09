try:
    import google.generativeai as genai
    from PIL import Image
    from dotenv import load_dotenv
    print("✅ All systems GO! Your 'Eyes' are installed.")
except ImportError as e:
    print(f"❌ Still missing something: {e}")