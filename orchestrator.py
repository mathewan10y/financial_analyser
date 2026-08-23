import os
import time
import random
import asyncio
import json
import yfinance as yf
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# Load API key and configure Gemini via official google.genai SDK
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("🚨 GEMINI_API_KEY missing from .env file!")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"

# Global concurrency control to prevent sudden API bursts
RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(2)

def call_gemini_safe(prompt: str, is_json: bool = False, max_retries: int = 4) -> str:
    """Synchronous bulletproof wrapper that catches rate limits with exponential backoff and automatically retries."""
    config = types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
            return response.text
        except APIError as e:
            if getattr(e, 'code', None) == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                sleep_duration = 12 + (2 ** attempt) + random.uniform(1.0, 4.0)
                print(f"⏳ [API Rate Limit 429] Pausing for {sleep_duration:.2f}s (Retry {attempt + 1}/{max_retries})...")
                time.sleep(sleep_duration)
            else:
                print(f"❌ [API Error] {e}")
                if attempt == max_retries - 1:
                    return "Data unavailable due to system error."
                time.sleep(5)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                sleep_duration = 12 + (2 ** attempt) + random.uniform(1.0, 4.0)
                print(f"⏳ [API Rate Limit Hit] Pausing for {sleep_duration:.2f}s (Retry {attempt + 1}/{max_retries})...")
                time.sleep(sleep_duration)
            else:
                print(f"❌ [API Error] {e}")
                if attempt == max_retries - 1:
                    return "Data unavailable due to system error."
                time.sleep(5)
            
    return "Data unavailable due to persistent rate limiting."

async def call_gemini_safe_async(prompt: str, is_json: bool = False, max_retries: int = 4, delay_offset: float = 0.0) -> str:
    """Asynchronous wrapper with staggered jitter, concurrency semaphore control, and randomized exponential backoff."""
    if delay_offset > 0:
        await asyncio.sleep(delay_offset)

    config = types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
    for attempt in range(max_retries):
        try:
            async with RATE_LIMIT_SEMAPHORE:
                response = await client.aio.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=config
                )
                return response.text
        except APIError as e:
            if getattr(e, 'code', None) == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                sleep_duration = 12 + (2 ** attempt) + random.uniform(1.0, 4.0)
                print(f"⏳ [API Rate Limit 429] Pausing for {sleep_duration:.2f}s (Retry {attempt + 1}/{max_retries})...")
                await asyncio.sleep(sleep_duration)
            else:
                print(f"❌ [API Error] {e}")
                if attempt == max_retries - 1:
                    return "Data unavailable due to system error."
                await asyncio.sleep(5)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                sleep_duration = 12 + (2 ** attempt) + random.uniform(1.0, 4.0)
                print(f"⏳ [API Rate Limit Hit] Pausing for {sleep_duration:.2f}s (Retry {attempt + 1}/{max_retries})...")
                await asyncio.sleep(sleep_duration)
            else:
                print(f"❌ [API Error] {e}")
                if attempt == max_retries - 1:
                    return "Data unavailable due to system error."
                await asyncio.sleep(5)
            
    return "Data unavailable due to persistent rate limiting."

def get_financial_metrics(ticker_symbol: str) -> dict:
    """Fetches hard financial and technical data to prevent AI hallucination."""
    print(f"📊 [Data Layer] Fetching fundamental/technical metrics for {ticker_symbol}...")
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        return {
            "current_price": info.get("currentPrice", "N/A"),
            "fifty_day_ma": info.get("fiftyDayAverage", "N/A"),
            "two_hundred_day_ma": info.get("twoHundredDayAverage", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A")
        }
    except Exception as e:
        print(f"⚠️ [Data Layer] Could not fetch financial metrics: {e}")
        return {}

def run_agentic_debate(ticker: str, sentiment_json: list) -> dict:
    """Executes the 5-Agent debate sequence and returns a final JSON decision."""
    metrics = get_financial_metrics(ticker)
    
    print(f"🤖 [Agent 1] Generating Fundamental Analysis...")
    fundamental_prompt = f"""
    You are the Senior Fundamental Equity Analyst at a Tier-1 hedge fund.
    Target Ticker: {ticker}
    
    Current Extracted Metrics:
    - Trailing P/E Ratio: {metrics.get('pe_ratio')}
    - Forward P/E Ratio: {metrics.get('forward_pe')}
    - Debt-to-Equity Ratio: {metrics.get('debt_to_equity')}
    - Profit Margin: {metrics.get('profit_margin')}
    
    Task: Evaluate the baseline financial health and valuation of this asset.
    Rules:
    1. Compare Trailing P/E to Forward P/E to assess growth expectations.
    2. Explicitly evaluate the Debt-to-Equity ratio. Is the balance sheet a ticking time bomb?
    3. Determine if the stock is a "Value Trap" (cheap but dying) or a "Growth Compounder".
    
    Provide your analysis in a structured, 4-sentence argument focusing strictly on balance sheet safety and intrinsic valuation.
    """
    fundamental_argument = call_gemini_safe(fundamental_prompt)

    print(f"🤖 [Agent 2] Generating Technical Analysis...")
    technical_prompt = f"""
    You are a Chartered Market Technician (CMT) focusing purely on price action and momentum.
    Target Ticker: {ticker}
    
    Current Market Data:
    - Current Price: {metrics.get('current_price')}
    - 50-Day Moving Average: {metrics.get('fifty_day_ma')}
    - 200-Day Moving Average: {metrics.get('two_hundred_day_ma')}
    
    Task: Evaluate the structural trend of the asset.
    Rules:
    1. Analyze the relationship between the Current Price and the Moving Averages.
    2. Check for Golden Crosses (50 > 200) or Death Crosses (50 < 200).
    3. Determine if the stock is overextended, breaking out, or in a structural downtrend.
    
    Provide your analysis in a 3-sentence argument. Ignore the underlying business; focus ONLY on the chart data provided.
    """
    technical_argument = call_gemini_safe(technical_prompt)

    print(f"🤖 [Agent 3] Generating Sentiment Analysis...")
    sentiment_prompt = f"""
    You are a Quantitative Sentiment Analyst. Your job is to read the market's psychological state.
    Target Ticker: {ticker}
    
    Raw GPU Pipeline Output (Sentiment Scores -1.0 to 1.0):
    {json.dumps(sentiment_json, indent=2)}
    
    Task: Decode the overarching narrative surrounding the stock.
    Rules:
    1. Look at the "weighted_average" scores. Is the baseline tone optimistic or deeply cautious?
    2. Look at the "critical_downside_event" triggers. What is the media's biggest fear regarding this stock right now?
    3. Look at the "critical_upside_event" triggers. What are the major bullish catalysts or positive milestones highlighted?
    
    Summarize the narrative and state whether public momentum is currently a tailwind or a headwind. Keep it under 4 sentences.
    """
    sentiment_argument = call_gemini_safe(sentiment_prompt)

    print(f"🤖 [Agent 4] Devil's Advocate / Risk Manager critique...")
    risk_prompt = f"""
    You are the Chief Risk Officer (CRO). Your sole directive is capital preservation and identifying analytical blind spots.
    Target Ticker: {ticker}
    
    Review the arguments generated by your junior analysts:
    [FUNDAMENTAL DESK]: {fundamental_argument}
    [TECHNICAL DESK]: {technical_argument}
    [SENTIMENT DESK]: {sentiment_argument}
    
    Task: Tear these arguments apart and look for contradictions.
    Rules:
    1. Find conflicts. (e.g., "The Technical desk is bullish, but the Fundamental desk noted extreme debt levels—this is a momentum trap.")
    2. Identify the absolute worst-case scenario that the other analysts are ignoring.
    3. Be ruthless, pessimistic, and highly skeptical.
    
    Deliver a devastating 4-sentence critique highlighting the biggest systemic risk of investing in this asset right now.
    """
    risk_argument = call_gemini_safe(risk_prompt)

    print(f"⚖️ [Agent 5] Orchestrator making final ruling...")
    orchestrator_prompt = f"""
    You are the Head Portfolio Manager. You must make the final capital allocation decision for {ticker}.
    
    Debate Transcript:
    1. Fundamental View: {fundamental_argument}
    2. Technical View: {technical_argument}
    3. Sentiment View: {sentiment_argument}
    4. CRO Risk Warning: {risk_argument}
    
    Task: Weigh the evidence, resolve the contradictions, and make a definitive ruling.
    
    You MUST respond with a valid JSON object using EXACTLY this schema:
    {{
        "internal_reasoning_process": "<A step-by-step logical breakdown of how you resolved the conflicting arguments>",
        "decision": "BUY" or "HOLD" or "SELL",
        "confidence_score": <An integer between 1 and 100 representing your conviction>,
        "executive_summary": "<A strict, 2-sentence final justification for the Portfolio Committee>"
    }}
    Do not include markdown blocks like ```json. Return ONLY the raw JSON string.
    """
    
    try:
        final_response_text = call_gemini_safe(orchestrator_prompt, is_json=True)
        return json.loads(final_response_text)
    except Exception as e:
        print(f"❌ [Orchestrator] Error parsing final JSON: {e}")
        return {
            "internal_reasoning_process": "Failed to synthesize debate due to rate limits or formatting error.",
            "decision": "HOLD",
            "confidence_score": 0,
            "executive_summary": "System error during multi-agent debate synthesis."
        }