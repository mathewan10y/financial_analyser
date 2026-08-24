import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import time
import requests
import feedparser
import re
import urllib.parse
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
}

_orig_print = print
def safe_print(*args, **kwargs):
    """Safely prints messages even on Windows terminals with non-UTF8 encodings."""
    try:
        _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args).encode("ascii", "replace").decode("ascii")
        _orig_print(text, **kwargs)

print = safe_print

def generate_baseline_telemetry_placeholder(ticker: str) -> dict:
    """Generates standard baseline telemetry placeholder tagged with is_dummy: True."""
    return {
        "headline": f"Market Baseline Telemetry for {ticker}",
        "full_text": f"Baseline market telemetry operational for {ticker}.",
        "date": datetime.now(timezone.utc).isoformat(),
        "link": "#",
        "is_dummy": True
    }

def fetch_news_for_ticker(
    ticker: str,
    min_articles: int = 3,
    max_articles: int = 5,
    timeout_seconds: float = 12.0
) -> list[dict]:
    clean_ticker = ticker.upper().strip()
    collected = []
    seen_links = set()
    start_time = time.time()
    
    base_symbol = re.sub(r'[\^=].*$', '', clean_ticker)
    base_symbol = re.sub(r'\.[A-Z]{2,3}$', '', base_symbol)
    
    # 1. Expand the query cascade with longName
    queries = [
        f"{clean_ticker} stock news",
        f"{base_symbol} stock market analysis"
    ]
    
    try:
        import yfinance as yf
        info = yf.Ticker(clean_ticker).info or {}
        long_name = info.get("longName", "")
        short_name = info.get("shortName", "")
        
        # Use full company name if available (e.g., "Tata Consultancy Services news")
        if long_name:
            clean_long = re.sub(r'(?i)\b(inc|ltd|corp|corporation|limited)\b\.?', '', long_name).strip()
            queries.insert(0, f"{clean_long} stock news")
            queries.insert(1, f"{clean_long} financial performance")
        elif short_name:
            queries.insert(0, f"{short_name} market news")
    except Exception:
        pass

    queries = list(dict.fromkeys(queries))

    print(f"📡 [Scraper] Ingesting news for {clean_ticker} across {len(queries)} query cascades...")

    for search_query in queries:
        if time.time() - start_time > timeout_seconds and len(collected) >= 1:
            break
            
        encoded_query = urllib.parse.quote(search_query)
        
        # 2. REMOVE the US-only lock to allow global indexing
        google_rss_url = f"https://news.google.com/rss/search?q={encoded_query}"
        
        try:
            resp = requests.get(google_rss_url, headers=HEADERS, timeout=5.0)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    link = getattr(entry, "link", "").strip()
                    title = getattr(entry, "title", "").strip()
                    title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                    
                    if link and title and link not in seen_links:
                        seen_links.add(link)
                        
                        pub_date = getattr(entry, "published", "")
                        if pub_date and hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                                date_str = dt.isoformat()
                            except Exception:
                                date_str = datetime.now(timezone.utc).isoformat()
                        else:
                            date_str = datetime.now(timezone.utc).isoformat()
                            
                        collected.append({
                            "headline": title,
                            "full_text": title,
                            "link": link,
                            "date": date_str,
                            "is_dummy": False
                        })
                        
                        if len(collected) >= max_articles:
                            return collected
            else:
                print(f"⚠️ [Scraper] RSS returned HTTP {resp.status_code} for '{search_query}'")
        except Exception as e:
            print(f"⚠️ [Scraper] Exception querying '{search_query}': {e}")
            
        if len(collected) >= min_articles:
            return collected

    if not collected:
        print(f"⚠️ [Scraper] 0 articles found. Ingesting baseline telemetry placeholder.")
        return [generate_baseline_telemetry_placeholder(clean_ticker)]
        
    return collected

# Backward-compatibility alias
fetch_stock_news = fetch_news_for_ticker