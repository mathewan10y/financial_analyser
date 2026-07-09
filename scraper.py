import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import html

def fetch_stock_news(ticker: str, max_articles: int = 5):
    """
    Fetches the latest news for a given ticker using the official Google News RSS feed.
    Completely bulletproof because it parses structured XML rather than scraping HTML pages.
    """
    print(f"📡 Pulling official RSS feed for: {ticker} stock...")
    
    # URL encode the query safely using standard libraries
    query = urllib.parse.quote(f"{ticker} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        # Pretend to be a standard browser to avoid basic bot blocks
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        # Parse the XML data structure
        root = ET.fromstring(xml_data)
        
        articles = []
        # Find all <item> tags inside the XML channel
        for item in root.findall('.//item')[:max_articles]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            
            # Clean up any HTML entities (like &amp; or &quot;) left in the XML strings
            headline = html.unescape(title).strip()
            summary = html.unescape(description).strip()
            
            # Simple text cleaning to strip out residual HTML tags if present in the summary
            if "<" in summary:
                import re
                summary = re.sub(r'<[^>]+>', '', summary)
                
            full_text = f"{headline}. {summary}" if summary else headline
            
            # Convert RSS timestamp format (e.g., "Thu, 18 Jun 2026 07:00:00 GMT") into ISO strings
            try:
                parsed_time = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = parsed_time.isoformat() + "Z"
            except Exception:
                formatted_date = datetime.utcnow().isoformat() + "Z"
                
            articles.append({
                "headline": headline,
                "date": formatted_date,
                "full_text": full_text,
                "link": link
            })
            
        print(f"✅ Successfully ingested {len(articles)} articles from RSS stream.")
        return articles
        
    except Exception as e:
        print(f"❌ Error during RSS data ingestion lifecycle: {e}")
        return []