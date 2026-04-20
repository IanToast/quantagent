import anthropic
import os
from datetime import datetime
from models.reports import ResearchReport
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def fetch_research_report_node(state):
    errors = state.get("errors") or []

    ticker = state["ticker"].upper()
    company_name = state.get("company_name") or "company name unknown"
    sector = state.get("sector") or "sector unknown"

    sentiment = state.get("sentiment")
    quant_signals = state.get("quant_signals")
    price_summary = state.get("price_summary")

    prompt = f"""You are a senior quantitative portfolio manager. Given sentiment, price, 
    and quantitative signals, produce a single actionable investment recommendation. 
    Your goal is weigh both quantitative signals AND qualitative signals together, 
    identifying the correct investment decision despite the uncertainty. 

    When quantitative signals and sentiment conflict with no clear edge, 
    default to Neutral. Prioritize avoiding false conviction over acting on 
    ambiguous signals.
    
    Your decision must be precise and actionable. A clear signal, 
    a one-line thesis, and specific risks and catalysts grounded 
    in the data provided.

    **Signal calibration**
    Strong Buy  - high conviction bullish, multiple signals aligned, clear catalyst
    Buy         - more positive than negative signals, reasonable upside
    Neutral     - mixed or conflicting signals, no clear directional edge
    Sell        - more negative than positive signals, meaningful downside risk
    Strong Sell - high conviction bearish, multiple risk flags, limited upside

    'calculations_limited' on either price or quant input indicates incomplete data. 
    Note this in 'signal_rationale' and discount affected signals
"""

    tools = [
        {
            "name": "synthesize_report",
            "description": "Create the research report for a stock",
            "input_schema": {
                "type": "object",
                "properties": {
                    "overall_signal": {
                        "type": "string",
                        "enum": ["strong buy", "buy", "neutral", "sell", "strong sell"],
                        "description": "Investment recommendation based on all available signals"
                    },
                    "one_line_summary": {
                        "type": "string",
                        "description": "Single punchy sentence capturing the core investment thesis"
                    },
                    "signal_rationale": {
                        "type": "string",
                        "description": "2-3 sentences expanding on the thesis, referencing specific signals"
                    },
                    "time_horizon": {
                        "type": "string",
                        "enum": ["short term", "medium term", "long term"],
                        "description": "Expected holding period for the thesis to play out"
                    },
                    "risks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific bearish factors that could cause the stock to underperform"
                    },
                    "catalysts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific bullish factors that could cause the stock to outperform"
                    },
                    "key_metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 most important quantitative signals that influenced the decision, explained in plain English"
                    },
                },
                "required": ["overall_signal", "one_line_summary", "signal_rationale", "time_horizon", "risks", "catalysts", "key_metrics"]
            }
        }
    ]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=prompt,
            tools=tools,
            tool_choice={"type": "any"},  # forces Claude to use a tool
            messages=[
                {
                    "role": "user", 
                    "content": f"""Please analyze the following information for {company_name} ({ticker}), a {sector} company, and produce an investment recommendation:

                    Price Summary:
                    {price_summary}

                    Quantitative Signals:
                    {quant_signals}

                    Sentiment Report:
                    {sentiment}"""
                }
            ]
        )
        tool_use_block = next(
            block for block in response.content 
            if block.type == "tool_use"
        )
        result = tool_use_block.input

        research_report = ResearchReport(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            generated_at=datetime.now(),
            current_price=price_summary.current_price,
            price_summary=price_summary,
            quant_signals=quant_signals,
            sentiment=sentiment,
            **result
        )
    except Exception as e:
        return {"errors": errors + [f"sentiment analysis failed: {e}"]}

    return {
        "research_report": research_report,
        "errors": errors
    }