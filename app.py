import re
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import pipeline
from orchestrator import get_financial_metrics, call_gemini_safe, call_gemini_safe_async

# Import local processing components
from scraper import fetch_stock_news
from aggregator import aggregate_quant_sentiment
from filter_agent import isolate_target_text  

# 1. Define the Lifespan Handler for VRAM Preservation
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Guarantees the transformer model weights load exactly once into VRAM.
    Stores the model pipeline in app.state to protect against Uvicorn reload loops.
    """
    MODEL_PATH = "./synapse_regression_model/checkpoint-183"  
    print(f"🧠 Mapping VRAM. Loading weights from {MODEL_PATH} onto Quadro P600 GPU...")
    
    try:
        # Load directly into CUDA device 0 and store it in app.state
        app.state.sentiment_pipeline = pipeline(
            "text-classification",
            model=MODEL_PATH,
            device=0
        )
        print("✅ Model loaded successfully on CUDA pipeline.")
    except Exception as e:
        print(f"⚠️ GPU acceleration setup failed. Falling back to CPU. Error: {e}")
        app.state.sentiment_pipeline = pipeline(
            "text-classification",
            model=MODEL_PATH,
            device=-1  # CPU Fallback
        )
    
    yield  # The app runs while this yields
    
    # Clean up model references on shutdown to free VRAM completely
    if hasattr(app.state, "sentiment_pipeline"):
        del app.state.sentiment_pipeline
        print("♻️ VRAM successfully flushed and freed.")

# 2. Initialize High-Performance Local API Engine with Lifespan
app = FastAPI(
    title="Synapse Local Sentiment Core",
    description="Local GPU-Accelerated Quant Underwriting Engine Pipeline",
    lifespan=lifespan
)

# Enable CORS parameters so local dummy UI layouts or Flutter apps can bridge safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Define Structured Input Validator schemas
class AnalysisPayload(BaseModel):
    ticker: str
    max_articles: int = 3

def split_text_into_sentences(text: str):
    """Simple regex utility to partition text body structures safely into sentences."""
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    return [s.strip() for s in sentences if len(s.strip()) > 6]

# 4. Expose Execution Routes
async def analyze_stream_generator(ticker_symbol: str, max_articles: int):
    """Generator function that yields JSON chunks for streaming response"""
    
    # Pull the single loaded model out of the app state securely
    sentiment_pipeline = app.state.sentiment_pipeline
    
    # Phase 1: Ingestion
    yield json.dumps({"phase": "ingestion", "message": "Scraping Yahoo Finance..."}) + "\n"
    
    raw_articles = fetch_stock_news(ticker_symbol, max_articles=max_articles)
    
    if not raw_articles:
        yield json.dumps({"phase": "error", "message": f"No transactional telemetry data available for ticker: {ticker_symbol}"}) + "\n"
        return
        
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
            
            article_result = {
                "date": article["date"],
                "headline": article["headline"],
                "link": article["link"],
                "weighted_average": quant_profile["final_average"],
                "critical_downside_event": {
                    "score": quant_profile["max_downside_signal"],
                    "text_context": sentences[max_down_idx]
                },
                "critical_upside_event": {
                    "score": quant_profile["max_upside_signal"],
                    "text_context": sentences[max_up_idx]
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
    
    # Phase 2: Agentic Debate - execute independent agents concurrently with jitter
    metrics = get_financial_metrics(ticker_symbol)
    
    # Prompt definitions for Fundamental, Technical, and Sentiment Analysts
    fundamental_prompt = f"""
    You are the Senior Fundamental Equity Analyst at a Tier-1 hedge fund.
    Target Ticker: {ticker_symbol}
    
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

    technical_prompt = f"""
    You are a Chartered Market Technician (CMT) focusing purely on price action and momentum.
    Target Ticker: {ticker_symbol}
    
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

    sentiment_prompt = f"""
    You are a Quantitative Sentiment Analyst. Your job is to read the market's psychological state.
    Target Ticker: {ticker_symbol}
    
    Raw GPU Pipeline Output (Sentiment Scores -1.0 to 1.0):
    {json.dumps(compiled_batch_metrics, indent=2)}
    
    Task: Decode the overarching narrative surrounding the stock.
    Rules:
    1. Look at the "weighted_average" scores. Is the baseline tone optimistic or deeply cautious?
    2. Look at the "critical_downside_event" triggers. What is the media's biggest fear regarding this stock right now?
    3. Look at the "critical_upside_event" triggers. What are the major bullish catalysts or positive milestones highlighted?
    
    Summarize the narrative and state whether public momentum is currently a tailwind or a headwind. Keep it under 4 sentences.
    """

    # Yield SSE JSON message for parallel debate execution
    yield json.dumps({"phase": "debate_parallel", "message": "Executing parallel agent analysis..."}) + "\n"

    # Helper coroutine to tag task outputs with their respective agent desks
    async def fetch_desk_argument(agent_key: str, prompt: str, delay_offset: float):
        text = await call_gemini_safe_async(prompt, delay_offset=delay_offset)
        return agent_key, text

    tasks = [
        asyncio.create_task(fetch_desk_argument("fundamental", fundamental_prompt, delay_offset=0.0)),
        asyncio.create_task(fetch_desk_argument("technical", technical_prompt, delay_offset=2.5)),
        asyncio.create_task(fetch_desk_argument("sentiment", sentiment_prompt, delay_offset=5.0)),
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
    # Agent 4: Risk Manager
    yield json.dumps({"phase": "debate_risk", "message": "CRO stress-testing transcript..."}) + "\n"
    risk_prompt = f"""
    You are the Chief Risk Officer (CRO). Your sole directive is capital preservation and identifying analytical blind spots.
    Target Ticker: {ticker_symbol}
    
    Review the arguments generated by your junior analysts:
    {debate_transcript}
    
    Task: Tear these arguments apart and look for contradictions.
    Rules:
    1. Find conflicts. (e.g., "The Technical desk is bullish, but the Fundamental desk noted extreme debt levels—this is a momentum trap.")
    2. Identify the absolute worst-case scenario that the other analysts are ignoring.
    3. Be ruthless, pessimistic, and highly skeptical.
    
    Deliver a devastating 4-sentence critique highlighting the biggest systemic risk of investing in this asset right now.
    """
    risk_argument = await call_gemini_safe_async(risk_prompt)
    yield json.dumps({
        "phase": "agent_result",
        "agent": "risk",
        "text": risk_argument
    }) + "\n"

    # Agent 5: Orchestrator
    yield json.dumps({"phase": "debate_synthesis", "message": "Orchestrator synthesizing capital allocation..."}) + "\n"
    orchestrator_prompt = f"""
    You are the Head Portfolio Manager. You must make the final capital allocation decision for {ticker_symbol}.
    
    Debate Transcript:
    {debate_transcript}
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
        final_response_text = await call_gemini_safe_async(orchestrator_prompt, is_json=True)
        orchestrator_decision = json.loads(final_response_text)
    except Exception as e:
        print(f"❌ [Orchestrator] Error parsing final JSON: {e}")
        orchestrator_decision = {
            "internal_reasoning_process": "Failed to synthesize debate due to rate limits or formatting error.",
            "decision": "HOLD",
            "confidence_score": 0,
            "executive_summary": "System error during multi-agent debate synthesis."
        }

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