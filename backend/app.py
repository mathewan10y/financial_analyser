import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
import re
import json
import time
import socket
import asyncio
import traceback
import requests

# ---------------------------------------------------------------------------
# DNS FALLBACK PATCH
# Render's network cannot resolve api-inference.huggingface.co via local DNS.
# This patch retries any failed getaddrinfo call via Google DNS-over-HTTPS,
# which is reachable on all networks. No extra dependencies required.
# ---------------------------------------------------------------------------
_ORIG_GETADDRINFO = socket.getaddrinfo
_DOH_FALLBACK_HOSTS = {"api-inference.huggingface.co"}

def _getaddrinfo_with_doh_fallback(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)
    except socket.gaierror:
        if host in _DOH_FALLBACK_HOSTS:
            try:
                import urllib.request
                doh_req = urllib.request.Request(
                    f"https://dns.google/resolve?name={host}&type=A",
                    headers={"accept": "application/dns-json"}
                )
                with urllib.request.urlopen(doh_req, timeout=5) as r:
                    data = json.loads(r.read())
                    answers = data.get("Answer", [])
                    if answers:
                        ip = answers[0]["data"]
                        print(f"\ud83d\udce1 [DoH] Resolved {host} -> {ip} via dns.google")
                        return [
                            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)),
                            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", (ip, port)),
                        ]
            except Exception as doh_err:
                print(f"\u26a0\ufe0f [DoH fallback failed] {doh_err}")
        raise

socket.getaddrinfo = _getaddrinfo_with_doh_fallback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Synapse Quantitative Intelligence API",
    description="Multi-agent financial sentiment analysis and market intelligence engine."
)

# ---------------------------------------------------------
# CORS CONFIGURATION (Permits AWS Amplify & Localhost)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# HYBRID MODEL INFERENCE ADAPTER
# ---------------------------------------------------------
MODEL_ID = os.getenv("HF_MODEL_ID", "mathewan10y/synapse-financial-sentiment")
USE_SERVERLESS = os.getenv("USE_SERVERLESS", "false").lower() in ("true", "1", "yes")

_local_model = None
_local_tokenizer = None
_hf_client = None
_device = "cpu"

if USE_SERVERLESS:
    print(f"☁️ [Mode] Cloud Serverless Inference active: {MODEL_ID}")
else:
    print(f"💻 [Mode] Local Model Execution requested: {MODEL_ID}")
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"⚙️ [Hardware] Target compute device: {_device}")
        
        _local_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        _local_model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
        _local_model.to(_device)
        _local_model.eval()
        print("✅ [Model Loader] Local model loaded successfully.")
    except Exception as e:
        print(f"⚠️ [Model Loader] Local PyTorch load failed: {e}")
        print("🔄 [Model Loader] Will use Hugging Face Serverless API instead.")
        USE_SERVERLESS = True  # module-level update so the function sees it


def analyze_headline_sentiment(text: str) -> dict:
    """
    Evaluates text polarity. Supports both local transformer evaluation 
    and Hugging Face Serverless Inference API.
    Returns: dict mapping sentiment labels to normalized probability scores.
    """
    if not text or not text.strip():
        return {"neutral": 1.0, "positive": 0.0, "negative": 0.0, "score": 0.0}

    # Prefer the HF API whenever a token is available (covers both USE_SERVERLESS=true
    # AND the fallback path where local model loading failed at startup).
    hf_token = os.getenv("HF_TOKEN", "")
    if USE_SERVERLESS or (hf_token and _local_model is None):
        # router.huggingface.co resolves correctly on Render and most networks.
        # api-inference.huggingface.co is used as a secondary fallback.
        PRIMARY_URL  = f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}"
        FALLBACK_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json",
            "x-use-cache": "false",
        }
        params = {"wait_for_model": "true"}

        def _call_hf_api(input_text: str) -> float:
            """POST to HF Inference API and extract the raw regression score.
            Tries the classic Inference API first (supports all Hub models).
            Falls back to the Inference Router if the classic API is unavailable.
            The DoH patch above ensures api-inference.huggingface.co resolves
            even when Render's local DNS doesn't have it.
            """
            last_exc = None
            for url in (FALLBACK_URL, PRIMARY_URL):  # classic API first, router as backup
                try:
                    resp = requests.post(
                        url,
                        headers=headers,
                        params=params,
                        json={"inputs": input_text},
                        timeout=30,
                    )
                    print(f"\ud83d\udd0d [HF Status] {resp.status_code} | url={url.split('/')[2]} | body: {resp.text[:200]}")
                    if resp.status_code in (400, 422, 503) and "not supported" in resp.text.lower():
                        # This provider doesn't support the model — try the next URL
                        last_exc = RuntimeError(f"Provider rejected model: {resp.text[:100]}")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break  # success
                except requests.exceptions.ConnectionError as ce:
                    print(f"\u26a0\ufe0f [HF DNS fail] {url.split('/')[2]}: {ce}")
                    last_exc = ce
                    continue
            else:
                raise last_exc if last_exc else RuntimeError("All HF endpoints failed")

            raw = 0.0

            # [[{"label": "LABEL_0", "score": X}]]
            # For problem_type="regression", HF returns the raw logit directly (no sigmoid).
            # X is the model's raw continuous prediction, typically in [-1, +1].
            if (
                isinstance(data, list) and len(data) > 0
                and isinstance(data[0], list) and len(data[0]) > 0
                and isinstance(data[0][0], dict)
            ):
                raw = float(data[0][0].get("score", 0.0))

            # [{"label": ..., "score": X}]
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                raw = float(data[0].get("score", 0.0))

            # [[-0.353]]  nested raw float
            elif (
                isinstance(data, list) and len(data) > 0
                and isinstance(data[0], list) and len(data[0]) > 0
                and isinstance(data[0][0], (float, int))
            ):
                raw = float(data[0][0])

            # [-0.353]  flat raw float
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], (float, int)):
                raw = float(data[0])

            # {"score": X} or {"error": "..."}
            elif isinstance(data, dict):
                if "error" in data:
                    raise RuntimeError(f"HF API error: {data['error']}")
                raw = float(data.get("score", 0.0))

            return max(-1.0, min(1.0, raw))

        try:
            raw_score = _call_hf_api(text)
        except Exception as e:
            print(f"\u26a0\ufe0f [Inference Exception]: {repr(e)}")
            traceback.print_exc()
            return {"neutral": 1.0, "positive": 0.0, "negative": 0.0, "score": 0.0}

        pos_val = max(0.0, raw_score)
        neg_val = max(0.0, -raw_score)
        neu_val = max(0.0, 1.0 - abs(raw_score))
        return {"positive": pos_val, "negative": neg_val, "neutral": neu_val, "score": raw_score}

    # 2. Local PyTorch Route
    if _local_model is not None and _local_tokenizer is not None:
        try:
            import torch
            inputs = _local_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(_device) for k, v in inputs.items()}
            with torch.no_grad():
                # Extract the single continuous float (-1.0 to 1.0)
                raw_score = _local_model(**inputs).logits.squeeze().item()

            pos_val = raw_score if raw_score > 0 else 0.0
            neg_val = abs(raw_score) if raw_score < 0 else 0.0
            neu_val = max(0.0, 1.0 - abs(raw_score))

            return {
                "positive": pos_val,
                "negative": neg_val,
                "neutral": neu_val,
                "score": raw_score
            }
        except Exception as e:
            print(f"⚠️ [Local Inference Error] {e}")
            return {"neutral": 0.5, "positive": 0.25, "negative": 0.25, "score": 0.0}

    return {"neutral": 1.0, "positive": 0.0, "negative": 0.0, "score": 0.0}

# ---------------------------------------------------------
# SYSTEM HEALTH & COLD START WAKE-UP
# ---------------------------------------------------------
@app.get("/health")
async def health_check():
    """Endpoint for frontend cold-start probing and uptime monitoring."""
    return {
        "status": "healthy",
        "service": "synapse-backend",
        "mode": "serverless" if USE_SERVERLESS else "local"
    }


@app.get("/debug-hf")
def debug_hf():
    """Returns the raw HF API response for a fixed test sentence.
    Use this endpoint to verify inference is working on the deployment.
    Hit: GET /debug-hf
    """
    test_sentence = "Earnings beat expectations significantly, stock surges to all-time high."
    hf_token = os.getenv("HF_TOKEN", "")
    PRIMARY_URL  = f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}"
    FALLBACK_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
        "x-use-cache": "false",
    }
    for url in (PRIMARY_URL, FALLBACK_URL):
        try:
            resp = requests.post(url, headers=headers, params={"wait_for_model": "true"},
                                 json={"inputs": test_sentence}, timeout=30)
            return {
                "url": url,
                "status": resp.status_code,
                "raw_body": resp.json(),
                "parsed_score": analyze_headline_sentiment(test_sentence),
                "hf_token_set": bool(hf_token),
                "use_serverless": USE_SERVERLESS,
                "model_id": MODEL_ID,
            }
        except requests.exceptions.ConnectionError:
            continue
    return {"error": "Both HF endpoints unreachable", "hf_token_set": bool(hf_token)}


# Import local processing components
from scraper import fetch_stock_news, generate_baseline_telemetry_placeholder
from aggregator import aggregate_quant_sentiment
from filter_agent import isolate_target_text  
from orchestrator import (
    get_financial_metrics,
    call_llm_with_fallback_async,
    generate_emergency_local_verdict,
)

# Define request schema
class StockRequest(BaseModel):
    ticker: str
    max_articles: int = 5

AnalysisPayload = StockRequest

def split_text_into_sentences(text: str) -> list[str]:
    """Splits a block of text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]

# ---------------------------------------------------------
# EXECUTION STREAMING ROUTE
# ---------------------------------------------------------
async def analyze_stream_generator(ticker_symbol: str, max_articles: int = 5):
    """Generator function that yields JSON chunks for streaming response"""
    
    # Phase 1: Ingestion & Scraping - Emit immediate scraping phase
    yield json.dumps({"phase": "scraping", "message": "Fetching global market news and telemetry..."}) + "\n"
    
    try:
        raw_articles = fetch_stock_news(ticker_symbol, max_articles=max_articles, timeout_seconds=12.0)
    except Exception as e:
        print(f"⚠️ [Ingestion Exception] Failed to fetch news for {ticker_symbol}: {e}")
        raw_articles = []

    # Article fetch safeguard: inject fallback placeholder if feed is empty or fails
    if not raw_articles:
        print(f"ℹ️ No external articles scraped for {ticker_symbol}. Injecting baseline telemetry placeholder.")
        raw_articles = [generate_baseline_telemetry_placeholder(ticker_symbol)]

    # Step 1 Progressive Streaming: Yield ingested articles immediately
    yield json.dumps({"phase": "articles_ingested", "articles": raw_articles}) + "\n"
        
    yield json.dumps({"phase": "filtering", "message": "Isolating target text..."}) + "\n"
    
    compiled_batch_metrics = []
    
    # Process batch articles sequentially and yield incrementally
    for idx, article in enumerate(raw_articles):
        try:
            yield json.dumps({"phase": "processing_article", "article_index": idx, "headline": article["headline"], "message": f"Processing article {idx + 1}/{len(raw_articles)}..."}) + "\n"
            
            # --- CLOUD LLM ISOLATION AGENT ---
            cleaned_text = isolate_target_text(article["full_text"], ticker_symbol)
            
            # If the agent determined the article was 100% spam/noise, skip it
            if not cleaned_text:
                yield json.dumps({"phase": "article_skipped", "article_index": idx, "reason": "Filtered as noise"}) + "\n"
                continue
                
            # Split the CLEANED text into sentences for sentiment extraction
            sentences = split_text_into_sentences(cleaned_text)
            
            if not sentences:
                yield json.dumps({"phase": "article_skipped", "article_index": idx, "reason": "No sentences extracted"}) + "\n"
                continue
            
            yield json.dumps({"phase": "gpu_processing", "article_index": idx, "sentence_count": len(sentences), "message": "Running sentiment analysis..."}) + "\n"
                
            sentence_scores = []
            for sent_idx, sentence in enumerate(sentences):
                score_map = analyze_headline_sentiment(sentence)
                # Prefer the direct signed float from the regression model;
                # fall back to (positive - negative) for classifier-style dicts.
                if "score" in score_map:
                    net_score = float(score_map["score"])
                else:
                    pos = float(score_map.get("positive", score_map.get("label_2", 0.0)))
                    neg = float(score_map.get("negative", score_map.get("label_0", 0.0)))
                    net_score = pos - neg
                sentence_scores.append(net_score)
                
                yield json.dumps({
                    "phase": "sentence_processed",
                    "article_index": idx,
                    "sentence_index": sent_idx,
                    "sentence": sentence[:100] + "..." if len(sentence) > 100 else sentence,
                    "score": round(net_score, 4),
                    "total_sentences": len(sentences)
                }) + "\n"
                
            if not sentence_scores:
                yield json.dumps({"phase": "article_skipped", "article_index": idx, "reason": "No valid sentiment scores"}) + "\n"
                continue

            # Find the exact indices using the original unrounded list elements
            raw_min_score = min(sentence_scores)
            raw_max_score = max(sentence_scores)
            max_down_idx = sentence_scores.index(raw_min_score)
            max_up_idx = sentence_scores.index(raw_max_score)
            
            # Run advanced multi-factor quantitative prioritization math
            quant_profile = aggregate_quant_sentiment(sentence_scores, is_headline_first=True)
            
            upside_text = sentences[max_up_idx]
            upside_score = quant_profile["max_upside_signal"]
            downside_text = sentences[max_down_idx]
            downside_score = quant_profile["max_downside_signal"]

            # Trigger Deduplication in Telemetry Pipeline: ensure distinct triggers even when sentence count is low
            if upside_text == downside_text:
                if upside_score >= 0:
                    downside_text = "No significant catalyst detected."
                    downside_score = 0.0
                else:
                    upside_text = "No significant catalyst detected."
                    upside_score = 0.0

            article_result = {
                "date": article["date"],
                "headline": article["headline"],
                "link": article["link"],
                "is_dummy": article.get("is_dummy", False),
                "weighted_average": quant_profile["final_average"],
                "critical_downside_event": {
                    "score": downside_score,
                    "text_context": downside_text
                },
                "critical_upside_event": {
                    "score": upside_score,
                    "text_context": upside_text
                }
            }
            compiled_batch_metrics.append(article_result)
            
            # Yield the completed article immediately
            yield json.dumps({
                "phase": "article_complete",
                "article_index": idx,
                "article": article_result
            }) + "\n"
        except Exception as item_error:
            # Skip any single corrupt article without breaking the entire API call
            print(f"⚠️ Skipping an anomalous article due to error: {item_error}")
            yield json.dumps({"phase": "article_error", "article_index": idx, "error": str(item_error)}) + "\n"
            continue

    # Safeguard: if all articles filtered out, inject a baseline quant telemetry record
    if not compiled_batch_metrics:
        compiled_batch_metrics.append(generate_baseline_telemetry_placeholder(ticker_symbol))
        
    # Step 2 Progressive Streaming: Yield sentiment telemetry results immediately
    yield json.dumps({"phase": "sentiment_telemetry", "telemetry": compiled_batch_metrics}) + "\n"
    
    # Phase 2: Agentic Debate - execute independent agents concurrently across Gemini & Groq
    metrics = get_financial_metrics(ticker_symbol)
    
    # Prompt definitions for Fundamental, Technical, and Sentiment Analysts
    fundamental_prompt = f"""
    You are the Senior Fundamental Equity Analyst at a Tier-1 hedge fund.
    Target Ticker: {ticker_symbol}
    
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

    technical_prompt = f"""
    You are a Chartered Market Technician (CMT) focusing purely on price action and momentum.
    Target Ticker: {ticker_symbol}
    
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

    sentiment_prompt = f"""
    You are a Quantitative Sentiment Analyst. Your job is to read the market's psychological state.
    Target Ticker: {ticker_symbol}
    
    Raw Quantitative Pipeline Output (Sentiment Scores -1.0 to 1.0):
    {json.dumps(compiled_batch_metrics, indent=2)}
    
    Article Sample Size: {len(compiled_batch_metrics)} articles ingested.
    
    Task: Decode the overarching narrative surrounding the stock.
    Rules:
    1. Article Dataset Validation:
       - Check if the dataset contains `"is_dummy": true`. 
       - IF DUMMY: Begin your response EXACTLY with: "[NO EXTERNAL NEWS FOUND: ZERO-ARTICLE TELEMETRY MODE]". State that no recent external narratives are available and sentiment is strictly neutral (0.0). Do NOT analyze the placeholder text.
       - IF REAL NEWS (N >= 3): Provide standard narrative analysis.
       - IF REAL NEWS (N = 1 or 2): Begin response with "[LOW SAMPLE SIZE WARNING: N={len(compiled_batch_metrics)}]". Treat the score as highly volatile.
    2. Look at the "weighted_average" scores. Is the baseline tone optimistic or deeply cautious?
    3. Look at the "critical_downside_event" triggers. What is the media's biggest fear regarding this stock right now?
    4. Look at the "critical_upside_event" triggers. What are the major bullish catalysts or positive milestones highlighted?
    
    Summarize the narrative and state whether public momentum is currently a tailwind or a headwind. Keep it under 4 sentences.
    """

    # Yield SSE JSON message for parallel debate execution
    yield json.dumps({"phase": "debate_parallel", "message": "Executing parallel multi-provider agent analysis..."}) + "\n"

    # Helper coroutine to tag task outputs with their respective agent desks & multi-provider routing
    async def fetch_desk_argument(agent_key: str, prompt: str, delay_offset: float, preferred_provider: str):
        text = await call_llm_with_fallback_async(prompt, delay_offset=delay_offset, preferred_provider=preferred_provider)
        return agent_key, text

    tasks = [
        asyncio.create_task(fetch_desk_argument("fundamental", fundamental_prompt, delay_offset=0.0, preferred_provider="groq")),
        asyncio.create_task(fetch_desk_argument("technical", technical_prompt, delay_offset=1.5, preferred_provider="gemini")),
        asyncio.create_task(fetch_desk_argument("sentiment", sentiment_prompt, delay_offset=1.0, preferred_provider="groq")),
    ]

    agent_arguments = {}
    for completed_coro in asyncio.as_completed(tasks):
        agent_key, result_text = await completed_coro
        agent_arguments[agent_key] = result_text
        yield json.dumps({
            "phase": "agent_result",
            "agent": agent_key,
            "text": result_text
        }) + "\n"

    # Step 3: Nexus Node - Compile into single debate_transcript variable
    debate_transcript = f"""[FUNDAMENTAL DESK]: {agent_arguments.get('fundamental', '')}
[TECHNICAL DESK]: {agent_arguments.get('technical', '')}
[SENTIMENT DESK]: {agent_arguments.get('sentiment', '')}"""

    # Step 4: Sequential Risk and Orchestration
    # Agent 4: Risk Manager (Routed via Groq)
    yield json.dumps({"phase": "debate_risk", "message": "CRO stress-testing transcript..."}) + "\n"
    risk_prompt = f"""
    You are the Chief Risk Officer (CRO) on a quantitative investment committee.
    Your task is to stress-test the investment thesis and identify real downside risks.
    Target Ticker: {ticker_symbol}

    Verified Financial & Technical Metrics:
    - Trailing P/E Ratio: {metrics.get('pe_ratio')}
    - Forward P/E Ratio: {metrics.get('forward_pe')}
    - Debt-to-Equity: {metrics.get('debt_to_equity')}
    - Profit Margin: {metrics.get('profit_margin')}
    - Current Price: {metrics.get('current_price')}
    - 50-Day Moving Average: {metrics.get('fifty_day_ma')}
    - 200-Day Moving Average: {metrics.get('two_hundred_day_ma')}
    - Pre-computed Trend Status: {metrics.get('ma_trend_status')}
    - News Sample Size (N): {len(compiled_batch_metrics)}

    Review the arguments generated by your junior analysts:
    {debate_transcript}

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
    risk_argument = await call_llm_with_fallback_async(risk_prompt, preferred_provider="groq")
    yield json.dumps({
        "phase": "agent_result",
        "agent": "risk",
        "text": risk_argument
    }) + "\n"

    # Agent 5: Orchestrator (Routed via Gemini with Groq fallback)
    yield json.dumps({"phase": "debate_synthesis", "message": "Orchestrator synthesizing capital allocation..."}) + "\n"
    orchestrator_prompt = f"""
    You are the Lead Quantitative Orchestrator. Synthesize the findings of the 4 autonomous desks:
    1. Fundamental Desk
    2. Technical Desk
    3. Sentiment Desk
    4. Chief Risk Officer (CRO)
    Target Ticker: {ticker_symbol}

    Verified Asset Metrics:
    - Trailing P/E: {metrics.get('pe_ratio')}, Forward P/E: {metrics.get('forward_pe')}
    - Debt-to-Equity: {metrics.get('debt_to_equity')}, Profit Margin: {metrics.get('profit_margin')}
    - Price: {metrics.get('current_price')}, 50 MA: {metrics.get('fifty_day_ma')}, 200 MA: {metrics.get('two_hundred_day_ma')}
    - Pre-computed Trend: {metrics.get('ma_trend_status')}
    - News Sample Size (N): {len(compiled_batch_metrics)}

    Debate Transcript:
    {debate_transcript}
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
        final_response_text = await call_llm_with_fallback_async(orchestrator_prompt, is_json=True, preferred_provider="gemini")
        orchestrator_decision = json.loads(final_response_text)
    except Exception as e:
        print(f"❌ [Orchestrator] Error parsing final JSON: {e}")
        orchestrator_decision = generate_emergency_local_verdict(ticker_symbol, metrics, compiled_batch_metrics)

    yield json.dumps({
        "phase": "agent_result",
        "agent": "orchestrator",
        "text": orchestrator_decision.get("executive_summary", "")
    }) + "\n"
    
    # Phase 3: Complete - yield final payload
    yield json.dumps({
        "phase": "complete",
        "payload": {
            "status": "success",
            "ticker": ticker_symbol,
            "payload_length": len(compiled_batch_metrics),
            "dataset": compiled_batch_metrics,
            "final_verdict": orchestrator_decision
        }
    }) + "\n"

# ---------------------------------------------------------
# CURATED ASSET UNIVERSE & TICKER SEARCH
# ---------------------------------------------------------
GLOBAL_ASSET_UNIVERSE = [
    # US Mega-caps & Tech
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "AMD", "name": "Advanced Micro Devices, Inc."},
    {"symbol": "AVGO", "name": "Broadcom Inc."},
    {"symbol": "PLTR", "name": "Palantir Technologies Inc."},
    {"symbol": "NFLX", "name": "Netflix, Inc."},
    {"symbol": "INTC", "name": "Intel Corporation"},
    {"symbol": "QCOM", "name": "Qualcomm Incorporated"},
    {"symbol": "CRM", "name": "Salesforce, Inc."},
    {"symbol": "ORCL", "name": "Oracle Corporation"},
    {"symbol": "ADBE", "name": "Adobe Inc."},
    {"symbol": "COIN", "name": "Coinbase Global, Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "BAC", "name": "Bank of America Corporation"},
    {"symbol": "GS", "name": "The Goldman Sachs Group, Inc."},
    {"symbol": "WMT", "name": "Walmart Inc."},
    {"symbol": "DIS", "name": "The Walt Disney Company"},
    # Indian Bluechips (NSE / BSE)
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Ltd."},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Ltd."},
    {"symbol": "INFY.NS", "name": "Infosys Ltd."},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd."},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Ltd."},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Ltd."},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd."},
    {"symbol": "WIPRO.NS", "name": "Wipro Ltd."},
    {"symbol": "ITC.NS", "name": "ITC Ltd."},
    {"symbol": "LT.NS", "name": "Larsen & Toubro Ltd."},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Ltd."},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Ltd."},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Ltd."},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Ltd."},
    # Commodities & Futures
    {"symbol": "GC=F", "name": "Gold Futures"},
    {"symbol": "SI=F", "name": "Silver Futures"},
    {"symbol": "CL=F", "name": "Crude Oil Futures"},
    {"symbol": "NG=F", "name": "Natural Gas Futures"},
    {"symbol": "HG=F", "name": "Copper Futures"},
    # Crypto
    {"symbol": "BTC-USD", "name": "Bitcoin USD"},
    {"symbol": "ETH-USD", "name": "Ethereum USD"},
    {"symbol": "SOL-USD", "name": "Solana USD"},
    {"symbol": "XRP-USD", "name": "XRP USD"},
    {"symbol": "DOGE-USD", "name": "Dogecoin USD"},
    {"symbol": "ADA-USD", "name": "Cardano USD"},
    # Forex
    {"symbol": "EURUSD=X", "name": "EUR / USD Currency Pair"},
    {"symbol": "GBPUSD=X", "name": "GBP / USD Currency Pair"},
    {"symbol": "USDJPY=X", "name": "USD / JPY Currency Pair"},
    {"symbol": "USDINR=X", "name": "USD / INR Currency Pair"},
    {"symbol": "AUDUSD=X", "name": "AUD / USD Currency Pair"},
    # Major Indices
    {"symbol": "^GSPC", "name": "S&P 500 Index"},
    {"symbol": "^DJI", "name": "Dow Jones Industrial Average"},
    {"symbol": "^IXIC", "name": "NASDAQ Composite"},
    {"symbol": "^NSEI", "name": "NIFTY 50 Index"},
    {"symbol": "^BSESN", "name": "BSE SENSEX Index"},
]

@app.get("/api/v1/search")
async def search_tickers(q: str = ""):
    import urllib.parse
    import requests
    query = q.strip().upper()
    if not query:
        return {"quotes": GLOBAL_ASSET_UNIVERSE[:8]}
    
    results = []
    seen_symbols = set()
    
    # 1. First search in local curated asset universe for instant matching
    for asset in GLOBAL_ASSET_UNIVERSE:
        if query in asset["symbol"].upper() or query.lower() in asset["name"].lower():
            if asset["symbol"] not in seen_symbols:
                seen_symbols.add(asset["symbol"])
                results.append(asset)

    # 2. Query Yahoo Finance search API for live global tickers
    try:
        encoded = urllib.parse.quote_plus(q)
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={encoded}&quotesCount=10&newsCount=0"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            for quote in data.get("quotes", []):
                sym = quote.get("symbol")
                name = quote.get("longname") or quote.get("shortname") or sym
                if sym and sym not in seen_symbols:
                    seen_symbols.add(sym)
                    results.append({"symbol": sym, "name": name})
    except Exception as e:
        print(f"⚠️ [Search API Error] {e}")

    # Fallback if nothing matched: add the query itself as a custom ticker option
    if not results:
        results.append({"symbol": query, "name": f"Custom Symbol ({query})"})

    return {"quotes": results[:10]}

@app.post("/api/v1/analyze")
async def analyze_asset_sentiment(payload: AnalysisPayload):
    return StreamingResponse(
        analyze_stream_generator(payload.ticker.upper().strip(), payload.max_articles),
        media_type="application/x-ndjson"
    )

if __name__ == "__main__":
    import uvicorn
    # Automatically execute local server loop if script run directly
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)