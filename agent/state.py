from typing import TypedDict, Annotated
import operator
from models.reports import PriceSummary, QuantSignals, SentimentReport, ResearchReport, NewsItem

class AgentState(TypedDict, total=False):
    ticker: str
    company_name: str
    sector: str
    news_filtered_count: int
    news_total_count: int
    analyst_target_mean: float
    analyst_target_high: float
    analyst_target_low: float

    price_summary: PriceSummary
    quant_signals: QuantSignals
    news_items: list[NewsItem]
    sentiment: SentimentReport
    research_report: ResearchReport

    errors: Annotated[list, operator.add] # merge lists instead of overwriting