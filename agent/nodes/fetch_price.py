import yfinance as yf
from models.reports import PriceSummary 


def fetch_price_node(state):
    ticker = state["ticker"].upper()

    t = yf.Ticker(ticker)
    df = t.history(period="2y")
    info = t.info
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
        "sector": sector
    }

