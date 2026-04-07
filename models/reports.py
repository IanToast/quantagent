from pydantic import BaseModel
from typing import Optional

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