import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
from orchestrator import run_agentic_debate

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
@app.post("/api/v1/analyze")
async def analyze_asset_sentiment(payload: AnalysisPayload):
    ticker_symbol = payload.ticker.upper().strip()
    
    # Pull the single loaded model out of the app state securely
    sentiment_pipeline = app.state.sentiment_pipeline
    
    # Execute Ingestion Layer
    raw_articles = fetch_stock_news(ticker_symbol, max_articles=payload.max_articles)
    
    if not raw_articles:
        raise HTTPException(status_code=444, detail=f"No transactional telemetry data available for ticker: {ticker_symbol}")
        
    compiled_batch_metrics = []
    
    # Process batch articles sequentially
    for article in raw_articles:
        try:
            # --- CLOUD LLM ISOLATION AGENT ---
            cleaned_text = isolate_target_text(article["full_text"], ticker_symbol)
            
            # If the agent determined the article was 100% spam/noise, skip it
            if not cleaned_text:
                continue
                
            # Split the CLEANED text into sentences for the local GPU
            sentences = split_text_into_sentences(cleaned_text)
            
            if not sentences:
                continue
                
            # Run calculations off our globally preserved pipeline state
            raw_outputs = sentiment_pipeline(sentences)
            
            # Parse model classification mappings into float structures
            sentence_scores = []
            for out in raw_outputs:
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
                
            if not sentence_scores:
                continue

            # Find the exact indices using the original unrounded list elements
            raw_min_score = min(sentence_scores)
            raw_max_score = max(sentence_scores)
            max_down_idx = sentence_scores.index(raw_min_score)
            max_up_idx = sentence_scores.index(raw_max_score)
            
            # Run advanced multi-factor quantitative prioritization math
            quant_profile = aggregate_quant_sentiment(sentence_scores, is_headline_first=True)
            
            compiled_batch_metrics.append({
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
            })
        except Exception as item_error:
            # Skip any single corrupt article without breaking the entire API call
            print(f"⚠️ Skipping an anomalous article due to error: {item_error}")
            continue
            
    orchestrator_decision = run_agentic_debate(ticker_symbol, compiled_batch_metrics)
        
    return {
        "status": "success",
        "ticker": ticker_symbol,
        "payload_length": len(compiled_batch_metrics),
        "dataset": compiled_batch_metrics,
        "final_verdict": orchestrator_decision
    }

if __name__ == "__main__":
    import uvicorn
    # Automatically execute local server loop if script run directly
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)