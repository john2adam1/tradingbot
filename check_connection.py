import os
from google import genai
from dotenv import load_dotenv

def check():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Try with explicit models/ prefix
    model_id = "models/gemini-1.5-flash"
    
    print(f"\n---> Testing model: {model_id}")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Salom, sen ishlayapsanmi?"
        )
        print(f"[Success] Model {model_id} responded!")
    except Exception as e:
        print(f"[Fail] Model {model_id} error: {e}")

if __name__ == "__main__":
    check()
