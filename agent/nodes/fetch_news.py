import feedparser
from models.reports import NewsItem
from tenacity import retry, stop_after_attempt, wait_exponential
TOTAL_FETCHED = 30

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

    feeds = [
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

    for url in feeds:
        try:
            feed = fetch_news_from_feedparser(url, ticker)
        except Exception as e:
            return {"errors": errors + [f"fetch_news failed: {e}"]}

        for item in feed.entries[:TOTAL_FETCHED]:
            title = item.get("title") or ""
            summary = item.get("summary") or ""
            text = f"{title} {summary}".lower()
            if any([keyword in text for keyword in keywords]):
                news_item = NewsItem(
                    title=item.get("title") or "",
                    source="Seeking Alpha" if "seekingalpha" in url else "Yahoo Finance",
                    published=item.get("published") or None,
                    summary=item.get("summary") or None,
                    link=item.get("link") or None
                )
                news_items.append(news_item)
            # else:
                # print(f"Filtered out text {text}.")
                # print("-----")
                # print(keywords)
                # print("-----")
                # print([keyword for keyword in keywords if keyword in text])
           
    return {
        "news_items": news_items,
        "news_filtered_count": TOTAL_FETCHED * 2 - len(news_items),
        "news_total_count": TOTAL_FETCHED * 2,
        "errors": errors
    }