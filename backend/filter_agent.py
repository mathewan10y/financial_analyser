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
    "IWM": ["Russell 2000", "Russell"],
    "TCS": ["TCS", "Tata Consultancy", "Tata Consultancy Services", "Tata"],
    "INFY": ["Infosys", "Narayan Murthy", "Salil Parekh"],
    "RELIANCE": ["Reliance", "Mukesh Ambani", "Jio", "RIL"],
    "HDFCBANK": ["HDFC", "HDFC Bank"],
    "ICICIBANK": ["ICICI", "ICICI Bank"],
    "SBIN": ["SBI", "State Bank of India"],
    "WIPRO": ["Wipro"],
}

_COMPANY_NAME_CACHE = {}

def get_company_keywords(ticker: str) -> list[str]:
    """Retrieves aliases and company names for a given ticker."""
    clean_ticker = ticker.upper().strip()
    if clean_ticker in _COMPANY_NAME_CACHE:
        return _COMPANY_NAME_CACHE[clean_ticker]
    
    base_symbol = re.sub(r'[\^=].*$', '', clean_ticker)
    base_symbol = re.sub(r'\.[A-Z]{2,3}$', '', base_symbol).strip()

    keywords = set()
    keywords.add(clean_ticker)
    if base_symbol:
        keywords.add(base_symbol)
        
    for sym in [clean_ticker, base_symbol]:
        if sym in TICKER_ALIASES:
            keywords.update(TICKER_ALIASES[sym])

    # Dynamic lookup via yfinance
    try:
        info = yf.Ticker(clean_ticker).info or {}
        short_name = info.get("shortName", "")
        long_name = info.get("longName", "")
        
        for name in [short_name, long_name]:
            if name:
                keywords.add(name.strip())
                # Strip legal entity suffixes
                cleaned = re.sub(r'(?i)\b(inc|ltd|corp|corporation|limited|plc|llc|group|holdings|co|company|serv|services|lt)\b\.?', '', name).strip()
                if cleaned and len(cleaned) > 2:
                    keywords.add(cleaned)
                    # Add primary word tokens if distinctive (length > 3)
                    words = [w.strip() for w in re.split(r'[\s,\-]+', cleaned) if len(w.strip()) > 3]
                    for w in words:
                        keywords.add(w)
    except Exception:
        pass

    result = [k for k in keywords if len(k) >= 2]
    _COMPANY_NAME_CACHE[clean_ticker] = result
    return result

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
    
    combined_regex = re.compile("|".join(patterns), re.IGNORECASE) if patterns else None
    
    # Partition raw text into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+', raw_text)
    
    relevant_sentences = []
    for sentence in sentences:
        s_clean = sentence.strip()
        if not s_clean:
            continue
        if combined_regex and combined_regex.search(s_clean):
            relevant_sentences.append(s_clean)
            
    if not relevant_sentences:
        # Fallback: if raw_text is short (such as a targeted RSS headline/snippet), preserve it
        if len(raw_text.strip()) <= 300:
            return raw_text.strip()
        return ""
        
    return " ".join(relevant_sentences)