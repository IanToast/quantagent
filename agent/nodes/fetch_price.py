import yfinance as yf
import numpy as np
import pandas as pd
from models.reports import PriceSummary, QuantSignals
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
    available_days = len(df)

    def percent_change(days):
        nonlocal calculations_limited
        if available_days < days:
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

    # Trend
    sma20 = df["Close"].tail(min(20, available_days)).mean()
    sma50 = df["Close"].tail(min(50, available_days)).mean()
    sma200 = df["Close"].tail(min(200, available_days)).mean()

    if available_days >= 15:
        delta = df["Close"].diff()
        gains = delta.clip(lower=0) # negative changes become 0
        losses = (-delta).clip(lower=0) # positive changes become 0
        avg_gain = gains.rolling(14).mean()
        avg_loss = losses.rolling(14).mean()
        rsi = round(float(np.where(avg_loss == 0, 100, 100 - (100 / (1 + avg_gain/avg_loss)))[-1]), 2)
    else:
        rsi = None
    
    # Momentum
    if available_days >= 30:
        ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
        macd_line = ema_12-ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        macd_line_val = round(float(macd_line.iloc[-1]), 2)
        macd_signal_val = round(float(signal_line.iloc[-1]), 2)
        macd_histogram_val = round(float(histogram.iloc[-1]), 2)
        recent = df["Close"].tail(min(available_days, 252))
        momentum_zscore = round(float((current_price - recent.mean())/recent.std()), 3)
    else:
        macd_line_val = macd_signal_val = macd_histogram_val = momentum_zscore = None
    

    # Volatility
    log_returns = np.log(df["Close"] / df["Close"].shift(1))
    realized_vol_20d = round(float(log_returns.tail(20).std() * np.sqrt(252)), 4)

    rolling_max = df["Close"].tail(min(252, available_days)).cummax()
    drawdown = (df["Close"].tail(min(252, available_days)) - rolling_max) / rolling_max * 100
    max_drawdown_1y = round(float(drawdown.min()), 2) # lowest negative value

    if available_days >= 60:
        annual_return = log_returns.tail(min(252, available_days)).mean() * 252
        annual_vol = log_returns.tail(min(252, available_days)).std() * np.sqrt(252)
        sharpe = round(float(annual_return / annual_vol), 3)

        try:
            df_spy, info_spy = fetch_price_from_yfinance("SPY")
        except Exception as e:
            return {"errors": errors + [f"fetch_price failed: {e}"]}
        spy_log_returns = np.log(df_spy["Close"] / df_spy["Close"].shift(1)).tail(60)
        log_returns_for_beta = log_returns.tail(60)
        aligned = pd.concat([log_returns_for_beta, spy_log_returns], axis=1).dropna()
        beta_60d = round(float(np.cov(aligned.iloc[:,0], aligned.iloc[:,1])[0,1] / np.var(aligned.iloc[:,1])), 2)
    else:
        sharpe = beta_60d = None

    quant_signals = QuantSignals(
        ticker=ticker,
        available_days=available_days,
        sma20=round(sma20, 2),
        sma50=round(sma50, 2),
        sma200=round(sma200, 2),
        price_vs_sma20=round((current_price - sma20)/sma20 * 100, 2),
        price_vs_sma50=round((current_price - sma50)/sma50 * 100, 2),
        price_vs_sma200=round((current_price - sma200)/sma200 * 100, 2),
        golden_cross=sma50>=sma200,
        death_cross=sma50<sma200,
        rsi_14=rsi,
        macd_line=macd_line_val,
        macd_signal=macd_signal_val,
        macd_histogram=macd_histogram_val,
        momentum_zscore=momentum_zscore,
        realized_vol_20d=realized_vol_20d,
        beta_60d=beta_60d,
        max_drawdown_1y=max_drawdown_1y,
        sharpe_ratio_1y=sharpe,
        calculations_limited=calculations_limited
    )

    company_name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "Unknown"

    return {
        "company_name": company_name,
        "price_summary": price_summary,
        "quant_signals": quant_signals,
        "sector": sector,
        "errors": errors
    }