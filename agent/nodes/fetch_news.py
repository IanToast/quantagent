import feedparser
from models.reports import NewsItem
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
from email.utils import parsedate_to_datetime
import anthropic
import json
import os
import math
from dotenv import load_dotenv
load_dotenv()

haiku_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_FOR_LLM = 20
NUMBER_OF_FEEDS = 3

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

def filter_relevant_articles(news_items: list, ticker: str, company_name: str) -> list:
    if not news_items:
        return news_items

    headlines = "\n".join([
        f"{i+1}. {item.title}" + (f" — {item.summary[:150]}" if item.summary and "href" not in item.summary else "")
        for i, item in enumerate(news_items)
    ])

    prompt = f"""You are filtering news articles for a stock research tool.

Company: {company_name} ({ticker})

For each headline, output 1 if {company_name} is the PRIMARY subject of the article, or 0 if it is mentioned only incidentally, as a comparison, as an analyst/advisor, or as a secondary party.

The key question is: would someone interested in evaluating {company_name} find this article directly useful for understanding the company's outlook?

Headlines:
{headlines}

Output ONLY a JSON array of 0s and 1s, one per headline, in order. No explanation.
"""

    try:
        response = haiku_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "["}
            ]
        )
        raw = "[" + response.content[0].text.strip()
        scores = json.loads(raw)
        if len(scores) != len(news_items):
            print(f"[fetch_news] Haiku returned {len(scores)} scores for {len(news_items)} articles, using unfiltered")
            return news_items
        return [item for item, score in zip(news_items, scores) if score == 1]
    except Exception as e:
        print(f"[fetch_news] Haiku filter failed: {e}, returning unfiltered")
        return news_items  # fail gracefully, return everything

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
    seen_titles = set()

    for url in feeds:
        try:
            feed = fetch_news_from_feedparser(url, ticker)
        except Exception as e:
            errors.append(f"fetch_news failed {url}: {e}")
            continue   # try next feed instead of returning

        if "google" in url:
            source = "Google News"
            total_fetched_from_source = 20
        elif "seekingalpha" in url:
            source = "Seeking Alpha"
            total_fetched_from_source = 20
        else:
            source = "Yahoo Finance"
            total_fetched_from_source = 20
        
        for item in feed.entries[:total_fetched_from_source]:
            total_fetched += 1
            title = item.get("title") or ""
            
            if " - " in title:  # Remove " - source.com" suffix that Google News appends
                title = title.rsplit(" - ", 1)[0]
            
            # Skip duplicates
            normalized = title.lower().strip()[:50]
            if normalized in seen_titles:
                total_filtered += 1
                continue
            seen_titles.add(normalized)

            summary = item.get("summary") or ""
            if "href" in summary:
                summary = ""
            text = f"{title} {summary}".lower()

            if any([keyword in text for keyword in keywords]):
                news_item = NewsItem(
                    title=title,
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
    filtered_items = filter_relevant_articles(news_items, ticker, company_name)

    # Ensure source diversity in final selection
    google_items = [x for x in filtered_items if x.source == "Google News"][:math.ceil(MAX_FOR_LLM / NUMBER_OF_FEEDS)]
    yahoo_items = [x for x in filtered_items if x.source == "Yahoo Finance"][:math.floor(MAX_FOR_LLM / NUMBER_OF_FEEDS)]
    seeking_items = [x for x in filtered_items if x.source == "Seeking Alpha"][:math.ceil(MAX_FOR_LLM / NUMBER_OF_FEEDS)]

    # Combine and re-sort by date
    news_items = google_items + yahoo_items + seeking_items
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