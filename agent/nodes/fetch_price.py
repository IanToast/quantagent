import yfinance as yf
from models.reports import PriceSummary 
from tenacity import retry, stop_after_attempt, wait_exponential

# TODO: add timeout handling to prevent yfinance from hanging indefinitely
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def fetch_price_from_yfinance(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="2y")
    except Exception as e:
        raise ConnectionError(f"yfinance request failed: {e}")
    
    if df is None or df.empty:
        raise ValueError(f"no data returned for {ticker}")
    
    return df, t.info

def fetch_price_node(state):
    errors = state.get("errors") or []
    ticker = state["ticker"].upper()

    try:
        df, info = fetch_price_from_yfinance(ticker)
    except Exception as e:
        return {"errors": errors + [f"fetch_price failed: {e}"]}

    calculations_limited = False
    current_price = float(df["Close"].iloc[-1])

    def percent_change(days):
        nonlocal calculations_limited
        if len(df) < days:
            past = float(df["Close"].iloc[0])
            calculations_limited = True
        else:
            past = float(df["Close"].iloc[-days])
        return round((current_price - past) / past * 100, 2)
    
    price_summary = PriceSummary(
        ticker=ticker,
        current_price=round(current_price, 2),
        price_change_1d_pct=percent_change(2),
        price_change_1m_pct=percent_change(21),
        price_change_3m_pct=percent_change(63),
        price_change_6m_pct=percent_change(126),
        price_change_1y_pct=percent_change(252),
        week_52_high=round(df["Close"].tail(252).max(), 2),
        week_52_low=round(df["Close"].tail(252).min(), 2),
        avg_volume_20d=round(df["Volume"].tail(20).mean(), 0),
        calculations_limited=calculations_limited
    )

    company_name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "Unknown"

    return {
        "price_data": df,
        "price_summary": price_summary,
        "company_name":company_name,
        "sector": sector,
        "errors": errors
    }

