import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import pipeline
from orchestrator import (
    get_financial_metrics,
    call_llm_with_fallback,
    call_llm_with_fallback_async,
    call_gemini_safe,
    call_gemini_safe_async,
    generate_emergency_local_verdict,
)

# Import local processing components
from scraper import fetch_stock_news, generate_baseline_telemetry_placeholder
from aggregator import aggregate_quant_sentiment
from filter_agent import isolate_target_text  

# 1. Define the Lifespan Handler for VRAM Preservation
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Guarantees the transformer model weights load exactly once into VRAM.
    Stores the model pipeline in app.state to protect against Uvicorn reload loops.
    """
    print("⏳ [VRAM Init] Loading FinBERT sentiment model into local GPU memory...")
    try:
        # Load directly onto the dedicated local GPU (device=0 for Quadro P600)
        app.state.sentiment_pipeline = pipeline(
            "sentiment-analysis", 
            model="ProsusAI/finbert", 
            device=0
        )
        print("✅ [VRAM Success] FinBERT successfully loaded into GPU memory (Device 0).")
    except Exception as e:
        print(f"⚠️ [VRAM Warning] GPU allocation failed: {e}. Falling back to CPU.")
        app.state.sentiment_pipeline = pipeline(
            "sentiment-analysis", 
            model="ProsusAI/finbert", 
            device=-1
        )
    yield
    # Cleanup on server shutdown if necessary
    print("🛑 [VRAM Cleanup] Unloading sentiment pipeline.")

# 2. Instantiate the FastAPI App with state lifespan
app = FastAPI(
    title="Synapse - Local Sentiment Edge + Dual Cloud Agent Pipeline",
    version="2.0.0",
    lifespan=lifespan
)

# 3. Add CORS Middleware to enable communication with Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# 4. Expose Execution Routes
async def analyze_stream_generator(ticker_symbol: str, max_articles: int = 5):
    """Generator function that yields JSON chunks for streaming response"""
    
    # Pull the single loaded model out of the app state securely
    sentiment_pipeline = app.state.sentiment_pipeline
    
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
                
            # Split the CLEANED text into sentences for the local GPU
            sentences = split_text_into_sentences(cleaned_text)
            
            if not sentences:
                yield json.dumps({"phase": "article_skipped", "article_index": idx, "reason": "No sentences extracted"}) + "\n"
                continue
            
            yield json.dumps({"phase": "gpu_processing", "article_index": idx, "sentence_count": len(sentences), "message": "Running GPU sentiment analysis..."}) + "\n"
                
            # Run calculations off our globally preserved pipeline state
            raw_outputs = sentiment_pipeline(sentences)
            
            # Parse model classification mappings into float structures
            sentence_scores = []
            for sent_idx, out in enumerate(raw_outputs):
                label = out.get("label")
                raw_val = out.get("score", 0.0)
                
                # Map labels to numeric float values
                if label == "POSITIVE" or label == "LABEL_1":
                    score = raw_val
                elif label == "NEGATIVE" or label == "LABEL_0":
                    score = -raw_val
                else:
                    score = raw_val
                    
                sentence_scores.append(score)
                
                # Yield intermediate sentence result
                yield json.dumps({
                    "phase": "sentence_processed",
                    "article_index": idx,
                    "sentence_index": sent_idx,
                    "sentence": sentences[sent_idx][:100] + "..." if len(sentences[sent_idx]) > 100 else sentences[sent_idx],
                    "score": score,
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
        
    # Step 2 Progressive Streaming: Yield GPU sentiment telemetry results immediately
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
    
    Raw GPU Pipeline Output (Sentiment Scores -1.0 to 1.0):
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
    You are the Chief Risk Officer (CRO). Your sole directive is capital preservation and identifying analytical blind spots.
    Target Ticker: {ticker_symbol}
    
    Review the arguments generated by your junior analysts:
    {debate_transcript}
    
    Task: Tear these arguments apart and look for contradictions.
    Rules:
    1. Find conflicts. (e.g., "The Technical desk is bullish, but the Fundamental desk noted extreme debt levels—this is a momentum trap.")
    2. If news sample size is low (N <= 2) or no external news was found ([NO EXTERNAL NEWS FOUND]), explicitly challenge any aggressive conclusions derived purely from isolated headlines, emphasizing reliance on balance sheet metrics and price trend confirmation.
    3. Identify the absolute worst-case scenario that the other analysts are ignoring.
    4. Be ruthless, pessimistic, and highly skeptical.
    
    Deliver a devastating 4-sentence critique highlighting the biggest systemic risk of investing in this asset right now.
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
    You are the Head Portfolio Manager. You must make the final capital allocation decision for {ticker_symbol}.
    
    Debate Transcript:
    {debate_transcript}
    4. CRO Risk Warning: {risk_argument}
    
    Task: Weigh the evidence, resolve the contradictions, and make a definitive ruling.
    
    Confidence Penalty Rule: 
    If the Sentiment Desk reports "[NO EXTERNAL NEWS FOUND]" or "[LOW SAMPLE SIZE WARNING]", you must reduce sentiment weighting by 50% and rely primarily on Fundamental and Technical desks. Cap your confidence score below 75 unless fundamentals strongly dictate otherwise.
    
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