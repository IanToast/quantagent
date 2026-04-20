from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

class PriceSummary(BaseModel):
    ticker: str
    current_price: float
    price_change_1d_pct: float
    price_change_1m_pct: float
    price_change_3m_pct: float
    price_change_6m_pct: float
    price_change_1y_pct: float
    week_52_high: float
    week_52_low: float
    avg_volume_20d: float
    calculations_limited: bool

class NewsItem(BaseModel):
    title: str
    source: str
    published: Optional[str]
    summary: Optional[str]
    link: Optional[str]

class QuantSignals(BaseModel):
    ticker: str
    available_days: int
    sma20: float
    sma50: float
    sma200: float
    price_vs_sma20: float
    price_vs_sma50: float
    price_vs_sma200: float
    golden_cross: bool
    death_cross: bool
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    momentum_zscore: Optional[float] = None
    realized_vol_20d: float
    beta_60d: Optional[float] = None
    max_drawdown_1y: float
    sharpe_ratio_1y: Optional[float] = None
    calculations_limited: bool

class Theme(BaseModel):
    trajectory: Literal["building", "peaking", "fading", "stable"]
    description: str

class RiskFlag(BaseModel):
    severity: Literal["low", "medium", "high"]
    description: str

class SentimentReport(BaseModel):
    overall: Literal["bullish", "neutral", "bearish"]
    confidence: Literal["low", "medium", "high"]
    score: float = Field(ge=-1.0, le=1.0)
    sentiment_trend: Literal["improving", "deteriorating", "stable", "mixed"]
    themes: list[Theme]
    inflections: list[str]
    risk_flags: list[RiskFlag]
    catalysts: list[str]
    latent_risks: list[str]
    headline_count: int

class ResearchReport(BaseModel):
    ticker: str
    company_name: str
    sector: str
    generated_at: datetime
    current_price: float

    # Synthesis
    overall_signal: Literal["strong buy", "buy", "neutral", "sell", "strong sell"]
    one_line_summary: str 
    signal_rationale: str # expands on summary
    time_horizon: Literal["short term", "medium term", "long term"]
    risks: list[str]
    catalysts: list[str]
    key_metrics: list[str] 

    # passed through from state (TODO)
    # analyst_target_mean: Optional[float]
    # analyst_target_high: Optional[float]
    # analyst_target_low: Optional[float]

    price_summary: PriceSummary
    quant_signals: QuantSignals
    sentiment: SentimentReport