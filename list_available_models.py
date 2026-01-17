import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("Fetching available models from Google Generative AI API...\n")

try:
    models = genai.list_models()
    
    print("=" * 80)
    print("AVAILABLE MODELS FOR CONTENT GENERATION:")
    print("=" * 80)
    
    for model in models:
        # Filter for models that support generateContent
        if 'generateContent' in model.supported_generation_methods:
            print(f"\nModel Name: {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description}")
            print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")
            print(f"  Input Token Limit: {model.input_token_limit}")
            print(f"  Output Token Limit: {model.output_token_limit}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
