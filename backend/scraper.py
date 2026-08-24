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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import yfinance as yf

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
}

_orig_print = print
def safe_print(*args, **kwargs):
    try:
        _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args).encode("ascii", "replace").decode("ascii")
        _orig_print(text, **kwargs)

print = safe_print

def generate_baseline_telemetry_placeholder(ticker: str) -> dict:
    return {
        "headline": f"Market Baseline Telemetry for {ticker}",
        "full_text": f"Baseline market telemetry operational for {ticker}.",
        "date": datetime.now(timezone.utc).isoformat(),
        "link": "#",
        "is_dummy": True
    }

def get_region_config(ticker: str) -> dict:
    """Returns optimal localization parameters based on exchange suffixes."""
    t = ticker.upper()
    if t.endswith(".NS") or t.endswith(".BO"):
        return {"hl": "en-IN", "gl": "IN", "ceid": "IN:en", "region_tag": "India"}
    elif t.endswith(".L"):
        return {"hl": "en-GB", "gl": "GB", "ceid": "GB:en", "region_tag": "UK"}
    elif t.endswith(".TO"):
        return {"hl": "en-CA", "gl": "CA", "ceid": "CA:en", "region_tag": "Canada"}
    elif t.endswith(".DE"):
        return {"hl": "de-DE", "gl": "DE", "ceid": "DE:de", "region_tag": "Germany"}
    return {"hl": "en-US", "gl": "US", "ceid": "US:en", "region_tag": "US"}

def build_search_queries(ticker: str, region_cfg: dict) -> list[str]:
    """Generates a rich, prioritized matrix of search queries across company names and symbols."""
    clean_ticker = ticker.upper().strip()
    base_symbol = re.sub(r'[\^=].*$', '', clean_ticker)
    base_symbol = re.sub(r'\.[A-Z]{2,3}$', '', base_symbol).strip()
    
    long_name = ""
    short_name = ""
    sector = ""
    
    try:
        info = yf.Ticker(clean_ticker).info or {}
        long_name = info.get("longName", "")
        short_name = info.get("shortName", "")
        sector = info.get("sector", "")
    except Exception:
        pass

    queries = []
    
    # 1. Clean Company Long Name
    if long_name:
        clean_long = re.sub(r'(?i)\b(inc|ltd|corp|corporation|limited|plc|sa|ag|nv|holdings|co|company)\b\.?', '', long_name).strip()
        queries.append(f"{clean_long} stock")
        queries.append(f"{clean_long} news")
        queries.append(f"{clean_long} business")
        
    # 2. Short Name
    if short_name and short_name != long_name:
        clean_short = re.sub(r'(?i)\b(inc|ltd|corp|corporation|limited|plc|co|company)\b\.?', '', short_name).strip()
        if len(clean_short) > 2:
            queries.append(f"{clean_short} stock")
            queries.append(f"{clean_short} news")

    # 3. Base Ticker Combinations
    queries.append(f"{base_symbol} stock")
    queries.append(f"{base_symbol} news")
    queries.append(f"{base_symbol} market")
    
    # 4. Regional Fallback (if non-US)
    if region_cfg.get("region_tag") and region_cfg["region_tag"] != "US":
        queries.append(f"{clean_ticker} news")
        queries.append(f"{base_symbol} {region_cfg['region_tag']}")
        
    # 5. Sector-Level Context (qualified by company/symbol)
    if sector:
        target_name = clean_long if long_name else base_symbol
        queries.append(f"{target_name} {sector} news")
        
    # 6. Raw Symbol Fallback
    queries.append(clean_ticker)
    
    return list(dict.fromkeys([q.strip() for q in queries if q.strip()]))

def fetch_feed_items(query: str, region_cfg: dict) -> list[dict]:
    """Fetches and parses a single RSS query endpoint."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl={region_cfg['hl']}&gl={region_cfg['gl']}&ceid={region_cfg['ceid']}"
    
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=4.0)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                link = getattr(entry, "link", "").strip()
                title = getattr(entry, "title", "").strip()
                # Remove publication attribution (e.g., "- Economic Times")
                clean_title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                
                if link and clean_title:
                    pub_date = getattr(entry, "published", "")
                    if pub_date and hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                            date_str = dt.isoformat()
                        except Exception:
                            date_str = datetime.now(timezone.utc).isoformat()
                    else:
                        date_str = datetime.now(timezone.utc).isoformat()
                        
                    items.append({
                        "headline": clean_title,
                        "full_text": clean_title,
                        "link": link,
                        "date": date_str,
                        "is_dummy": False
                    })
    except Exception as e:
        pass
    return items

def fetch_news_for_ticker(
    ticker: str,
    min_articles: int = 3,
    max_articles: int = 5,
    timeout_seconds: float = 12.0
) -> list[dict]:
    clean_ticker = ticker.upper().strip()
    region_cfg = get_region_config(clean_ticker)
    queries = build_search_queries(clean_ticker, region_cfg)
    
    print(f"📡 [Scraper] Launching parallel ingestion for {clean_ticker} across {len(queries)} query streams...")

    collected = []
    seen_links = set()
    seen_titles = set()

    # Dispatch queries concurrently
    with ThreadPoolExecutor(max_workers=min(len(queries), 6)) as executor:
        future_to_query = {executor.submit(fetch_feed_items, q, region_cfg): q for q in queries}
        
        for future in as_completed(future_to_query):
            try:
                results = future.result()
                for art in results:
                    link = art["link"]
                    # Normalize title for deduplication
                    title_norm = re.sub(r'[^a-zA-Z0-9]', '', art["headline"]).lower()[:40]
                    
                    if link not in seen_links and title_norm not in seen_titles:
                        seen_links.add(link)
                        seen_titles.add(title_norm)
                        collected.append(art)
                        
                        if len(collected) >= max_articles:
                            print(f"✅ [Scraper] Successfully collected maximum {len(collected)} target articles.")
                            return collected
            except Exception:
                continue

    if len(collected) >= min_articles:
        print(f"✅ [Scraper] Ingested {len(collected)} high-conviction articles.")
        return collected

    if collected:
        print(f"⚠️ [Scraper] Ingested {len(collected)} articles (below optimal threshold).")
        return collected

    print(f"⚠️ [Scraper] 0 articles found across all parallel streams. Ingesting baseline telemetry placeholder.")
    return [generate_baseline_telemetry_placeholder(clean_ticker)]

# Backward-compatibility alias
fetch_stock_news = fetch_news_for_ticker