import feedparser
from models.reports import NewsItem
from tenacity import retry, stop_after_attempt, wait_exponential
TOTAL_FETCHED = 60

# TODO: add timeout handling to prevent feedparser from hanging indefinitely

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def fetch_news_from_feedparser(ticker):
    try:
        feed = feedparser.parse(f"https://finance.yahoo.com/rss/headline?s={ticker}")
    except Exception as e:
        raise ConnectionError(f"yfinance request failed: {e}")
    if feed.bozo and len(feed.entries)==0:
        raise ValueError(f"no data returned for {ticker}")
    return feed

def fetch_news_node(state):
    errors = state.get("errors") or []
    ticker = state["ticker"].upper()
    company_name = state.get("company_name") or ""
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

    try:
        feed = fetch_news_from_feedparser(ticker)
    except Exception as e:
        return {"errors": errors + [f"fetch_news failed: {e}"]}
    
    news_items = []

    for item in feed.entries[:TOTAL_FETCHED]:
        text = f"{item.title} {item.summary}".lower()
        if any([keyword in text for keyword in keywords]):
            news_item = NewsItem(
                title=item.title,
                source="Yahoo Finance",
                published=item.published,
                summary=item.summary,
                link=item.link
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
        "news_filtered_count": TOTAL_FETCHED - len(news_items),
        "news_total_count": TOTAL_FETCHED,
        "errors": errors
    }