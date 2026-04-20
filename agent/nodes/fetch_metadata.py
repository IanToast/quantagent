import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def fetch_info_from_yfinance(ticker):
    t = yf.Ticker(ticker)
    info = t.info
    if not info:
        raise ValueError(f"no info returned for {ticker}")
    return info

def fetch_metadata_node(state):
    errors = state.get("errors") or []
    ticker = state["ticker"].upper()

    try:
        info = fetch_info_from_yfinance(ticker)
    except Exception as e:
        return {"errors": errors + [f"fetch_metadata failed: {e}"]}

    return {
        "company_name": info.get("shortName") or info.get("longName") or ticker,
        "sector": info.get("sector") or "Unknown sector",
        "analyst_target_mean": info.get("targetMeanPrice"),
        "analyst_target_high": info.get("targetHighPrice"),
        "analyst_target_low": info.get("targetLowPrice"),
        "errors": errors
    }