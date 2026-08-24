import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
import time
import random
import asyncio
import json
import yfinance as yf
from google import genai
from google.genai import types
from google.genai.errors import APIError
from groq import Groq, AsyncGroq
from dotenv import load_dotenv

# Load API keys from environment
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "openai/gpt-oss-20b"

# Initialize Gemini client if key is configured
gemini_client = None
if GOOGLE_API_KEY and not GOOGLE_API_KEY.startswith("your_"):
    try:
        gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
        print("✅ [Client Init] Google Gemini SDK client active.")
    except Exception as e:
        print(f"⚠️ [Client Init] Could not initialize Gemini client: {e}")

# Initialize Groq clients if key is configured
groq_client = None
groq_async_client = None
if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"):
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_async_client = AsyncGroq(api_key=GROQ_API_KEY)
        print("✅ [Client Init] Groq SDK client active.")
    except Exception as e:
        print(f"⚠️ [Client Init] Could not initialize Groq client: {e}")

# Global concurrency control
RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(2)

def generate_emergency_local_verdict(ticker: str, metrics: dict, sentiment_json: list) -> dict:
    """
    Constructs a deterministic rule-based verdict when cloud AI endpoints are unreachable.
    Evaluates P/E, Debt-to-Equity, Moving Averages, and Local GPU sentiment scores.
    """
    scores = []
    if isinstance(sentiment_json, list):
        for item in sentiment_json:
            if isinstance(item, dict) and "weighted_average" in item:
                try:
                    scores.append(float(item["weighted_average"]))
                except (ValueError, TypeError):
                    pass
    
    avg_sentiment = sum(scores) / len(scores) if scores else 0.0
    
    pe_str = str(metrics.get("pe_ratio", ""))
    de_str = str(metrics.get("debt_to_equity", ""))
    trend_str = str(metrics.get("ma_trend_status", ""))

    is_golden_cross = "Golden Cross" in trend_str
    is_death_cross = "Death Cross" in trend_str
    is_high_debt = "150%" in de_str or "1.5x" in de_str
    is_loss_making = "Loss-making" in pe_str
    
    if avg_sentiment > 0.15 and is_golden_cross and not is_high_debt and not is_loss_making:
        decision = "BUY"
        confidence = 75
        reason = f"Bullish technical momentum ({trend_str}) combined with positive local news sentiment (+{avg_sentiment:.2f}) and conservative leverage."
    elif avg_sentiment < -0.15 or is_death_cross or is_high_debt or is_loss_making:
        decision = "SELL"
        confidence = 70
        reason = f"Negative local news sentiment ({avg_sentiment:.2f}) or bearish structural trend ({trend_str}) indicates elevated downside risk."
    else:
        decision = "HOLD"
        confidence = 60
        reason = f"Neutral local sentiment ({avg_sentiment:.2f}) and mixed financial telemetry recommend a patient capital allocation stance."

    disclaimer = "Note: Cloud AI endpoints are currently unreachable. This evaluation is generated via emergency local rule-based fallback, strictly synthesized from available technical metrics and local article sentiment scores only."

    return {
        "internal_reasoning_process": f"Emergency Local Rule Engine: {reason}",
        "decision": decision,
        "confidence_score": confidence,
        "executive_summary": f"Target: {ticker} | Metric Status: {trend_str}. {disclaimer}"
    }

def call_gemini_provider(prompt: str, is_json: bool = False) -> str:
    """Calls Google Gemini synchronously."""
    if not gemini_client:
        raise RuntimeError("Google Gemini client is not initialized or API key is missing.")
    config = types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config
    )
    return response.text or ""

async def call_gemini_provider_async(prompt: str, is_json: bool = False) -> str:
    """Calls Google Gemini asynchronously."""
    if not gemini_client:
        raise RuntimeError("Google Gemini client is not initialized or API key is missing.")
    config = types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config
    )
    return response.text or ""

def call_groq_provider(prompt: str, is_json: bool = False) -> str:
    """Calls Groq synchronously."""
    if not groq_client:
        raise RuntimeError("Groq client is not initialized or API key is missing.")
    kwargs = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    if is_json:
        kwargs["response_format"] = {"type": "json_object"}
    response = groq_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""

async def call_groq_provider_async(prompt: str, is_json: bool = False) -> str:
    """Calls Groq asynchronously."""
    if not groq_async_client:
        raise RuntimeError("Groq async client is not initialized or API key is missing.")
    kwargs = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    if is_json:
        kwargs["response_format"] = {"type": "json_object"}
    response = await groq_async_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""

def call_llm_with_fallback(
    prompt: str,
    is_json: bool = False,
    preferred_provider: str = "gemini",
    max_retries: int = 3
) -> str:
    """
    Synchronously dispatches an LLM prompt to the preferred provider, with automatic cross-cloud
    zero-delay failover on rate limits (Gemini <-> Groq), and emergency local mode.
    """
    providers = ["groq", "gemini"] if preferred_provider.lower() == "groq" else ["gemini", "groq"]

    for provider in providers:
        for attempt in range(max_retries):
            try:
                if provider == "gemini":
                    return call_gemini_provider(prompt, is_json=is_json)
                else:
                    return call_groq_provider(prompt, is_json=is_json)
            except Exception as e:
                err_str = str(e).upper()
                is_rate_limit = any(term in err_str for term in ["429", "RESOURCE_EXHAUSTED", "RATE_LIMIT", "RATELIMIT", "QUOTA"])

                if is_rate_limit:
                    print(f"⚡ [{provider.upper()} Rate Limit / Quota Hit] Zero-delay instant failover to alternative provider...")
                    break  # Immediately break out of retry loop to try the next provider without sleeping
                else:
                    print(f"⚠️ [{provider.upper()} Error (Attempt {attempt+1}/{max_retries})] {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2.0)
                    else:
                        print(f"🔄 [{provider.upper()} Exhausted] Failing over to alternative cloud provider...")
                        break

    # Emergency fallback if both cloud providers fail
    print("🚨 [All Cloud Providers Failed] Generating Emergency Local Fallback text.")
    disclaimer = "Note: Cloud AI endpoints are currently unreachable. This evaluation is generated via emergency local rule-based fallback, strictly synthesized from available technical metrics and local article sentiment scores only."
    if is_json:
        return json.dumps({
            "internal_reasoning_process": "Cloud endpoints unreachable. Deterministic fallback synthesized available financial ratios and local GPU sentiment scores.",
            "decision": "HOLD",
            "confidence_score": 50,
            "executive_summary": disclaimer
        })
    return f"Analysis unavailable from cloud endpoints. {disclaimer}"

async def call_llm_with_fallback_async(
    prompt: str,
    is_json: bool = False,
    preferred_provider: str = "gemini",
    delay_offset: float = 0.0,
    max_retries: int = 3
) -> str:
    """
    Asynchronously dispatches an LLM prompt with delay jitter, concurrency semaphore control,
    zero-delay cross-cloud failover on rate limits (Gemini <-> Groq), and emergency local mode.
    """
    if delay_offset > 0:
        await asyncio.sleep(delay_offset)

    providers = ["groq", "gemini"] if preferred_provider.lower() == "groq" else ["gemini", "groq"]

    for provider in providers:
        for attempt in range(max_retries):
            try:
                async with RATE_LIMIT_SEMAPHORE:
                    if provider == "gemini":
                        return await call_gemini_provider_async(prompt, is_json=is_json)
                    else:
                        return await call_groq_provider_async(prompt, is_json=is_json)
            except Exception as e:
                err_str = str(e).upper()
                is_rate_limit = any(term in err_str for term in ["429", "RESOURCE_EXHAUSTED", "RATE_LIMIT", "RATELIMIT", "QUOTA"])

                if is_rate_limit:
                    print(f"⚡ [{provider.upper()} Rate Limit / Quota Hit] Zero-delay instant failover to alternative provider...")
                    break  # Immediately break out to next provider
                else:
                    print(f"⚠️ [{provider.upper()} Error (Attempt {attempt+1}/{max_retries})] {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0)
                    else:
                        print(f"🔄 [{provider.upper()} Exhausted] Failing over to alternative cloud provider...")
                        break

    # Emergency fallback if both cloud providers fail
    print("🚨 [All Cloud Providers Failed] Generating Emergency Local Fallback text.")
    disclaimer = "Note: Cloud AI endpoints are currently unreachable. This evaluation is generated via emergency local rule-based fallback, strictly synthesized from available technical metrics and local article sentiment scores only."
    if is_json:
        return json.dumps({
            "internal_reasoning_process": "Cloud endpoints unreachable. Deterministic fallback synthesized available financial ratios and local GPU sentiment scores.",
            "decision": "HOLD",
            "confidence_score": 50,
            "executive_summary": disclaimer
        })
    return f"Analysis unavailable from cloud endpoints. {disclaimer}"

# Backward-compatibility aliases
def call_gemini_safe(prompt: str, is_json: bool = False, max_retries: int = 3) -> str:
    return call_llm_with_fallback(prompt, is_json=is_json, preferred_provider="gemini", max_retries=max_retries)

async def call_gemini_safe_async(prompt: str, is_json: bool = False, max_retries: int = 3, delay_offset: float = 0.0) -> str:
    return await call_llm_with_fallback_async(prompt, is_json=is_json, preferred_provider="gemini", delay_offset=delay_offset, max_retries=max_retries)

def get_financial_metrics(ticker_symbol: str) -> dict:
    """Fetches hard financial and technical data with normalized units to prevent AI hallucination."""
    print(f"📊 [Data Layer] Fetching fundamental/technical metrics for {ticker_symbol}...")
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info or {}
        
        # 1. Currency
        currency = info.get("currency", "USD") or "USD"

        # 2. Current Price
        current_price_raw = info.get("currentPrice") or info.get("regularMarketPrice")
        if isinstance(current_price_raw, (int, float)):
            current_price = f"{float(current_price_raw):.2f} {currency}"
        else:
            current_price = "N/A"

        # 3. Moving Averages
        fifty_raw = info.get("fiftyDayAverage")
        two_hundred_raw = info.get("twoHundredDayAverage")
        
        if isinstance(fifty_raw, (int, float)):
            fifty_day_ma = f"{float(fifty_raw):.2f} {currency}"
        else:
            fifty_day_ma = "N/A"

        if isinstance(two_hundred_raw, (int, float)):
            two_hundred_day_ma = f"{float(two_hundred_raw):.2f} {currency}"
        else:
            two_hundred_day_ma = "N/A"

        # 4. Moving Average Cross & Trend Status
        if isinstance(fifty_raw, (int, float)) and isinstance(two_hundred_raw, (int, float)):
            if fifty_raw > two_hundred_raw:
                ma_trend_status = "Golden Cross (50MA > 200MA - Bullish Structural Trend)"
            else:
                ma_trend_status = "Death Cross (50MA < 200MA - Bearish Structural Trend)"
        else:
            ma_trend_status = "N/A (Insufficient historical moving average data)"

        # 5. Valuation Multiples (P/E)
        trailing_pe_raw = info.get("trailingPE")
        if isinstance(trailing_pe_raw, (int, float)) and trailing_pe_raw > 0:
            pe_ratio = f"{float(trailing_pe_raw):.2f}x"
        else:
            pe_ratio = "N/A (Loss-making or unreported)"

        forward_pe_raw = info.get("forwardPE")
        if isinstance(forward_pe_raw, (int, float)) and forward_pe_raw > 0:
            forward_pe = f"{float(forward_pe_raw):.2f}x"
        else:
            forward_pe = "N/A (Loss-making or unreported)"

        # 6. Debt-to-Equity (yfinance returns D/E as a percentage e.g. 10.211 = 10.211% = 0.102x)
        de_raw = info.get("debtToEquity")
        if isinstance(de_raw, (int, float)):
            de_pct = float(de_raw)
            de_ratio = de_pct / 100.0
            debt_to_equity = f"{de_pct:.2f}% (Ratio: {de_ratio:.3f}x Debt/Equity) (Note: < 50% / < 0.5x is conservative/healthy; > 150% / > 1.5x is leveraged)"
        else:
            debt_to_equity = "N/A (Debt-free or unreported)"

        # 7. Profit Margin (yfinance returns profitMargins as decimal e.g. 0.24 = 24%)
        pm_raw = info.get("profitMargins")
        if isinstance(pm_raw, (int, float)):
            profit_margin = f"{float(pm_raw) * 100.0:.2f}%"
        else:
            profit_margin = "N/A"

        return {
            "current_price": current_price,
            "fifty_day_ma": fifty_day_ma,
            "two_hundred_day_ma": two_hundred_day_ma,
            "ma_trend_status": ma_trend_status,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "debt_to_equity": debt_to_equity,
            "profit_margin": profit_margin,
        }
    except Exception as e:
        print(f"⚠️ [Data Layer] Could not fetch financial metrics: {e}")
        return {
            "current_price": "N/A",
            "fifty_day_ma": "N/A",
            "two_hundred_day_ma": "N/A",
            "ma_trend_status": "N/A",
            "pe_ratio": "N/A",
            "forward_pe": "N/A",
            "debt_to_equity": "N/A",
            "profit_margin": "N/A",
        }

def run_agentic_debate(ticker: str, sentiment_json: list) -> dict:
    """Executes the 5-Agent debate sequence with multi-provider routing and returns a final JSON decision."""
    metrics = get_financial_metrics(ticker)
    
    print(f"🤖 [Agent 1] Generating Fundamental Analysis (Groq)...")
    fundamental_prompt = f"""
    You are the Senior Fundamental Equity Analyst at a Tier-1 hedge fund.
    Target Ticker: {ticker}
    
    Current Extracted Financial Metrics:
    - Trailing P/E Ratio: {metrics.get('pe_ratio')}
    - Forward P/E Ratio: {metrics.get('forward_pe')}
    - Debt-to-Equity: {metrics.get('debt_to_equity')}
    - Profit Margin: {metrics.get('profit_margin')}
    
    Task: Evaluate the baseline financial health, solvency, and valuation of this asset.
    Rules:
    1. Rule on Debt-to-Equity: The Debt-to-Equity metric is provided as a percentage and ratio. A ratio below 1.0x (100%) represents a healthy, conservative balance sheet (e.g. 10% / 0.10x is virtually debt-free). Do NOT interpret percentage values (e.g., 10%) as raw multiples (e.g., 10x). Only flag debt risk if the ratio exceeds 1.5x (150%).
    2. Rule on Profit Margins: Profit margins are presented as percentages. Evaluate margins relative to industry standards.
    3. Compare Trailing P/E to Forward P/E to assess earnings trajectory and growth expectations.
    4. Determine if the stock is a "Value Trap", "Overextended", or a "High-Quality Compounder".
    
    Provide your analysis in a structured, 4-sentence argument focusing strictly on balance sheet safety and intrinsic valuation.
    """
    fundamental_argument = call_llm_with_fallback(fundamental_prompt, preferred_provider="groq")

    print(f"🤖 [Agent 2] Generating Technical Analysis (Gemini)...")
    technical_prompt = f"""
    You are a Chartered Market Technician (CMT) focusing purely on price action and momentum.
    Target Ticker: {ticker}
    
    Current Market Technical Data:
    - Current Price: {metrics.get('current_price')}
    - 50-Day Moving Average: {metrics.get('fifty_day_ma')}
    - 200-Day Moving Average: {metrics.get('two_hundred_day_ma')}
    - Pre-computed Trend Status: {metrics.get('ma_trend_status')}
    
    Task: Evaluate the structural trend and momentum of the asset.
    Rules:
    1. Analyze the relationship between the Current Price and the Moving Averages.
    2. Reference the pre-computed Trend Status ({metrics.get('ma_trend_status')}). Do NOT hallucinate false crosses.
    3. Determine if the stock is overextended, breaking out, consolidating, or in a structural downtrend.
    
    Provide your analysis in a 3-sentence argument. Ignore the underlying business; focus ONLY on the chart and trend data provided.
    """
    technical_argument = call_llm_with_fallback(technical_prompt, preferred_provider="gemini")

    print(f"🤖 [Agent 3] Generating Sentiment Analysis (Groq)...")
    sentiment_prompt = f"""
    You are a Quantitative Sentiment Analyst. Your job is to read the market's psychological state.
    Target Ticker: {ticker}
    
    Raw GPU Pipeline Output (Sentiment Scores -1.0 to 1.0):
    {json.dumps(sentiment_json, indent=2)}
    
    Article Sample Size: {len(sentiment_json)} articles ingested.
    
    Task: Decode the overarching narrative surrounding the stock.
    Rules:
    1. Article Dataset Validation:
       - Check if the dataset contains `"is_dummy": true`. 
       - IF DUMMY: Begin your response EXACTLY with: "[NO EXTERNAL NEWS FOUND: ZERO-ARTICLE TELEMETRY MODE]". State that no recent external narratives are available and sentiment is strictly neutral (0.0). Do NOT analyze the placeholder text.
       - IF REAL NEWS (N >= 3): Provide standard narrative analysis.
       - IF REAL NEWS (N = 1 or 2): Begin response with "[LOW SAMPLE SIZE WARNING: N={len(sentiment_json)}]". Treat the score as highly volatile.
    2. Look at the "weighted_average" scores. Is the baseline tone optimistic or deeply cautious?
    3. Look at the "critical_downside_event" triggers. What is the media's biggest fear regarding this stock right now?
    4. Look at the "critical_upside_event" triggers. What are the major bullish catalysts or positive milestones highlighted?
    
    Summarize the narrative and state whether public momentum is currently a tailwind or a headwind. Keep it under 4 sentences.
    """
    sentiment_argument = call_llm_with_fallback(sentiment_prompt, preferred_provider="groq")

    print(f"🤖 [Agent 4] Devil's Advocate / Risk Manager critique (Groq)...")
    risk_prompt = f"""
    You are the Chief Risk Officer (CRO) on a quantitative investment committee.
    Your task is to stress-test the investment thesis and identify real downside risks.
    Target Ticker: {ticker}

    Verified Financial & Technical Metrics:
    - Trailing P/E Ratio: {metrics.get('pe_ratio')}
    - Forward P/E Ratio: {metrics.get('forward_pe')}
    - Debt-to-Equity: {metrics.get('debt_to_equity')}
    - Profit Margin: {metrics.get('profit_margin')}
    - Current Price: {metrics.get('current_price')}
    - 50-Day Moving Average: {metrics.get('fifty_day_ma')}
    - 200-Day Moving Average: {metrics.get('two_hundred_day_ma')}
    - Pre-computed Trend Status: {metrics.get('ma_trend_status')}
    - News Sample Size (N): {len(sentiment_json)}

    Review the arguments generated by your junior analysts:
    [FUNDAMENTAL DESK]: {fundamental_argument}
    [TECHNICAL DESK]: {technical_argument}
    [SENTIMENT DESK]: {sentiment_argument}

    STRICT METRIC TRUTHFULNESS & ANTI-FABRICATION RULES:
    1. Grounding In Hard Data: You MUST respect the exact fundamental and technical numbers provided:
       - If Debt-to-Equity is below 1.5x (or near zero), you are strictly FORBIDDEN from claiming the balance sheet is overleveraged, fragile, or burdened by debt.
       - If Profit Margins or P/E ratios are healthy, do not invent fictitious accounting or margin weaknesses.
    2. Valid Categories of Risk to Critique:
       - Technical Vulnerabilities: Structural death cross, trading below the 200-day MA, or failed resistance levels.
       - External & Macro Pressures: Industry-wide demand contractions, geopolitical headwinds, or currency volatility.
       - Sentiment & News Tailwinds/Headwinds: Specific negative events extracted from the ingested news items.
       - Low Sample Uncertainty: If article count N <= 2 or no external news was found ([NO EXTERNAL NEWS FOUND]), flag the lack of external narrative conviction.
    3. Deliver a concise, mathematically honest risk critique without generating unsubstantiated panic. Keep it under 4 sentences.
    """
    risk_argument = call_llm_with_fallback(risk_prompt, preferred_provider="groq")

    print(f"⚖️ [Agent 5] Orchestrator making final ruling (Gemini/Groq)...")
    orchestrator_prompt = f"""
    You are the Lead Quantitative Orchestrator. Synthesize the findings of the 4 autonomous desks:
    1. Fundamental Desk
    2. Technical Desk
    3. Sentiment Desk
    4. Chief Risk Officer (CRO)
    Target Ticker: {ticker}

    Verified Asset Metrics:
    - Trailing P/E: {metrics.get('pe_ratio')}, Forward P/E: {metrics.get('forward_pe')}
    - Debt-to-Equity: {metrics.get('debt_to_equity')}, Profit Margin: {metrics.get('profit_margin')}
    - Price: {metrics.get('current_price')}, 50 MA: {metrics.get('fifty_day_ma')}, 200 MA: {metrics.get('two_hundred_day_ma')}
    - Pre-computed Trend: {metrics.get('ma_trend_status')}
    - News Sample Size (N): {len(sentiment_json)}

    Debate Transcript:
    1. Fundamental View: {fundamental_argument}
    2. Technical View: {technical_argument}
    3. Sentiment View: {sentiment_argument}
    4. CRO Risk Warning: {risk_argument}

    CONFLICT RESOLUTION RULES:
    - Adjudicate Disagreements Rationally: If the Fundamental Desk proves pristine balance sheet health (e.g. low leverage, strong margins) and the CRO attempts to assert ungrounded financial weakness, REJECT the CRO's claim and prioritize the hard numerical data.
    - Balanced Conviction:
      - If Fundamentals are strong, Technicals are bearish/neutral, and Sentiment is neutral/low-sample: Default to a disciplined HOLD or cautious allocation with confidence calibrated strictly between 50-70.
      - If all 3 pillars (Fundamentals, Technicals, Sentiment) align bullishly: Issue a BUY with conviction (70-85+).
      - Only issue a SELL if technical breakdown is severe AND accompanied by deteriorating fundamentals or severe negative news catalysts.
    - Confidence Penalty Rule: If the Sentiment Desk reports "[NO EXTERNAL NEWS FOUND]" or "[LOW SAMPLE SIZE WARNING]" (N <= 2), reduce sentiment weighting by 50% and rely primarily on Fundamental and Technical desks.
    - Resolution Breakdown: In `internal_reasoning_process`, provide a step-by-step numbered breakdown explaining exactly how data conflicts between desks were resolved, referencing specific metrics (e.g. 200-day MA, D/E ratio, quantified sentiment score).

    You MUST respond with a valid JSON object using EXACTLY this schema:
    {{
        "internal_reasoning_process": "<A step-by-step numbered logical breakdown of how you resolved conflicting arguments referencing specific metrics>",
        "decision": "BUY" or "HOLD" or "SELL",
        "confidence_score": <An integer between 1 and 100 representing your conviction>,
        "executive_summary": "<A strict, 2-sentence final justification for the Portfolio Committee>"
    }}
    Do not include markdown blocks like ```json. Return ONLY the raw JSON string.
    """
    
    try:
        final_response_text = call_llm_with_fallback(orchestrator_prompt, is_json=True, preferred_provider="gemini")
        return json.loads(final_response_text)
    except Exception as e:
        print(f"❌ [Orchestrator] Error parsing final JSON: {e}")
        return generate_emergency_local_verdict(ticker, metrics, sentiment_json)