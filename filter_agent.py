import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Load environment variables from the local .env file
load_dotenv()

# 2. Extract the API key securely
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "🚨 SYSTEM ERROR: GEMINI_API_KEY missing from environment. "
        "Please check that your .env file exists and contains: GEMINI_API_KEY=your_key"
    )

# 3. Initialize and configure the Gemini client
genai.configure(api_key=API_KEY)


model = genai.GenerativeModel('gemini-2.5-flash')
def isolate_target_text(raw_text: str, target_ticker: str) -> str:
    """
    Acts as the Synapse Text Isolation Agent.
    Parses noisy financial feeds to strip out competitor updates, macro clutter, 
    and returns only sentences directly relevant to the target asset.
    """
    print(f"🧠 [Cloud Agent] Filtering text noise for target: {target_ticker}...")
    
    prompt = f"""
    You are the Synapse Text Isolation Agent. 
    Target Company Ticker: {target_ticker}
    
    Task: Read the following financial news text. Extract and return ONLY the 
    sentences and data points that directly pertain to {target_ticker} or its 
    direct market environment. 
    
    Strict Rules:
    1. If a sentence is entirely about a competitor and does not impact the target, remove it.
    2. If the text does not contain any relevant information about the target, return an empty string.
    3. Do not add any conversational meta-commentary, introductory remarks, or filler. 
    Return ONLY the raw isolated paragraphs or sentences.
    
    Raw Text:
    {raw_text}
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip()
        
        # If the LLM filtered out all text as noise/spam
        if not cleaned_text:
            print(f"⚠️ [Cloud Agent] Content filtered out completely. No direct relevance to {target_ticker}.")
            return ""
            
        return cleaned_text
        
    except Exception as e:
        print(f"❌ [Cloud Agent] API execution failed: {e}. Executing core local fallback protocol.")
        # Fault Tolerance: Return the raw uncleaned text if internet drops or rate limits hit.
        # This keeps the local GPU pipeline alive and prevents app crashes.
        return raw_text