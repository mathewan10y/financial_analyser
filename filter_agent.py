import re
import yfinance as yf

# Common ticker to company name aliases cache
TICKER_ALIASES = {
    "AAPL": ["Apple", "iPhone", "Mac", "iPad"],
    "MSFT": ["Microsoft", "Azure", "Windows", "Office"],
    "NVDA": ["Nvidia", "NVIDIA", "GeForce", "Jensen Huang"],
    "TSLA": ["Tesla", "Elon Musk", "Cybertruck"],
    "GOOGL": ["Google", "Alphabet", "Waymo", "Android"],
    "GOOG": ["Google", "Alphabet", "Waymo", "Android"],
    "AMZN": ["Amazon", "AWS", "Prime"],
    "META": ["Meta", "Facebook", "Instagram", "WhatsApp", "Zuckerberg"],
    "AMD": ["AMD", "Advanced Micro Devices", "Radeon", "Ryzen"],
    "INTC": ["Intel", "Pat Gelsinger"],
    "NFLX": ["Netflix"],
    "JPM": ["JPMorgan", "JP Morgan", "Chase", "Jamie Dimon"],
    "BAC": ["Bank of America", "BofA"],
    "V": ["Visa"],
    "MA": ["Mastercard"],
    "DIS": ["Disney", "Disney+", "ESPN"],
    "WMT": ["Walmart"],
    "COIN": ["Coinbase"],
    "PLTR": ["Palantir", "Alex Karp"],
    "SPY": ["S&P 500", "S&P", "SPDR"],
    "QQQ": ["Nasdaq", "Invesco QQQ"],
    "IWM": ["Russell 2000", "Russell"]
}

_COMPANY_NAME_CACHE = {}

def get_company_keywords(ticker: str) -> list[str]:
    """Retrieves aliases and company names for a given ticker."""
    clean_ticker = ticker.upper().strip()
    if clean_ticker in _COMPANY_NAME_CACHE:
        return _COMPANY_NAME_CACHE[clean_ticker]
    
    keywords = [clean_ticker]
    if clean_ticker in TICKER_ALIASES:
        keywords.extend(TICKER_ALIASES[clean_ticker])
    else:
        # Fallback dynamic lookup via yfinance
        try:
            info = yf.Ticker(clean_ticker).info
            short_name = info.get("shortName")
            long_name = info.get("longName")
            if short_name:
                cleaned = re.sub(r'\b(Inc\.?|Corp\.?|Corporation|Ltd\.?|plc|LLC|Group|Holdings|Co\.?)\b', '', short_name, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 2:
                    keywords.append(cleaned)
            if long_name:
                cleaned = re.sub(r'\b(Inc\.?|Corp\.?|Corporation|Ltd\.?|plc|LLC|Group|Holdings|Co\.?)\b', '', long_name, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 2 and cleaned not in keywords:
                    keywords.append(cleaned)
        except Exception:
            pass

    _COMPANY_NAME_CACHE[clean_ticker] = keywords
    return keywords

def isolate_target_text(raw_text: str, target_ticker: str) -> str:
    """
    Deterministic Synapse Text Isolation Agent.
    Parses financial text and extracts only sentences/paragraphs that directly mention
    the target ticker or company name, preserving LLM quota.
    """
    if not raw_text or not target_ticker:
        return ""

    keywords = get_company_keywords(target_ticker)
    
    # Compile regex patterns matching keywords with word boundaries
    patterns = []
    for kw in keywords:
        escaped = re.escape(kw)
        patterns.append(rf'\${escaped}\b')
        patterns.append(rf'\b{escaped}\b')
    
    combined_regex = re.compile("|".join(patterns), re.IGNORECASE)
    
    # Partition raw text into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+', raw_text)
    
    relevant_sentences = []
    for sentence in sentences:
        s_clean = sentence.strip()
        if not s_clean:
            continue
        if combined_regex.search(s_clean):
            relevant_sentences.append(s_clean)
            
    if not relevant_sentences:
        return ""
        
    return " ".join(relevant_sentences)