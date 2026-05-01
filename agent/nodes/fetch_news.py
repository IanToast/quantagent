import feedparser
from models.reports import NewsItem
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
from email.utils import parsedate_to_datetime
TOTAL_FETCHED_FROM_SOURCE = 20
MAX_FOR_LLM = 20

# TODO: add timeout handling to prevent feedparser from hanging indefinitely

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def fetch_news_from_feedparser(url, ticker):
    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "Mozilla/5.0"}
        )
    except Exception as e:
        raise ConnectionError(f"{url} request failed: {e}")
    if feed.bozo and len(feed.entries)==0:
        raise ValueError(f"no data returned from {url} for {ticker}")
    return feed

def fetch_news_node(state):
    errors = state.get("errors") or []
    ticker = state["ticker"].upper()
    company_name = state.get("company_name") or ""
    query = f"{company_name} stock".replace(" ", "+")

    feeds = [
        f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
        f"https://finance.yahoo.com/rss/headline?s={ticker}",
        f"https://seekingalpha.com/api/sa/combined/{ticker}.xml",
    ]
    # TODO: find a better way to filter for company names.
    noise_words = {
        "corporation", "incorporated", "company", "holdings", 
        "group", "technologies", "systems", "inc", "ltd", 
        "co", "corp", "plc", "llc", "new", "platforms", "of", "the"
    }
    keywords = []
    if len(ticker) > 1:
        keywords.append(ticker.lower())
    keywords += list(set([
        w.lower().strip(".,")
        for w in company_name.split()
        if len(w) > 1 and w.lower().strip(".,") not in noise_words
    ]))
    keywords = list(set(keywords)) # remove duplicate words

    news_items = []
    total_fetched = 0
    total_filtered = 0

    for url in feeds:
        try:
            feed = fetch_news_from_feedparser(url, ticker)
        except Exception as e:
            errors.append(f"fetch_news failed {url}: {e}")
            continue   # try next feed instead of returning

        if "google" in url:
            source = "Google News"
        elif "seekingalpha" in url:
            source = "Seeking Alpha"
        else:
            source = "Yahoo Finance"
        
        for item in feed.entries[:TOTAL_FETCHED_FROM_SOURCE]:
            total_fetched += 1
            title = item.get("title") or ""
            
            if " - " in title:  # Remove " - source.com" suffix that Google News appends
                title = title.rsplit(" - ", 1)[0]

            summary = item.get("summary") or ""
            if "href" in summary:
                summary = ""
            text = f"{title} {summary}".lower()

            if any([keyword in text for keyword in keywords]):
                matched = [keyword for keyword in keywords if keyword in text]
                print(f"MATCHED {matched}: {title[:60]}")
                news_item = NewsItem(
                    title=item.get("title") or "",
                    source=source,
                    published=item.get("published") or None,
                    summary=item.get("summary") or None,
                    link=item.get("link") or None
                )
                news_items.append(news_item)
            else:
                total_filtered += 1
            # else:
                # print(f"Filtered out text {text}.")
                # print("-----")
                # print(keywords)
                # print("-----")
                # print([keyword for keyword in keywords if keyword in text])
    
    news_items.sort(
        key=lambda x: parsedate_to_datetime(x.published) if x.published else datetime.min,
        reverse=True
    )
    news_items = news_items[:MAX_FOR_LLM]

    return {
        "news_items": news_items,
        "news_filtered_count": total_filtered,
        "news_total_count": total_fetched,
        "errors": errors
    }