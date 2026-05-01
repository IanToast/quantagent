import anthropic
import os
from models.reports import SentimentReport
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def fetch_sentiment_analysis_node(state):
    errors = state.get("errors") or []
    news_items = state.get("news_items")
    company_name = state.get("company_name") or ""
    ticker = state["ticker"].upper()
    news_filtered_count = state.get("news_filtered_count")
    news_total_count = state.get("news_total_count")

    if not news_items:
        return {
            "sentiment": SentimentReport(
                overall="neutral",
                score=0.0,
                sentiment_trend="stable",
                themes=[],
                inflections=[],
                risk_flags=[],
                catalysts=[],
                latent_risks=[],
                headline_count=0
            ),
            "errors": errors
        }

    headlines_text = ""
    for i, item in enumerate(news_items, 1):
        headlines_text += f"{i}. [{item.published}] {item.title}\n"
        if item.summary and "href" not in item.summary: # filter out html from google summaries
            headlines_text += f"   {item.summary}\n\n"

    prompt = f"""You are a quantitative analyst specializing in equity research with 
    with expertise in narrative momentum and sentiment trend analysis.

    You will be given recent news headlines about a stock, each tagged with a 
    publication date. Your goal is not just to assess isolated sentiment, but to 
    identify **directional shifts and narrative momentum** across the timeline. 

    **Temporal Weighting & Trend Detection**
    - Apply exponential decay weighting: headlines from the last 7 days carry full 
    weight, 8-30 days carry 50% weight, 30+ days carry 20% weight.
    - Flag "narrative inflection points": moments where coverage tone meaningfully 
    shifted and what triggered that shift

    **Signal vs. Noise Filtering**
    - Prioritize: earnings/guidance, leadership changes, M&A, product launches, 
    regulatory decisions, legal outcomes, major contract wins/losses
    - Deprioritize: macroeconomic headlines unless they name this company specifically, 
    speculative opinion pieces, duplicate coverage of the same event
    - When multiple headlines cover the same event, treat them as ONE data point 
    (avoid sentiment inflation from echo coverage)
    - When headlines are contradictory (some bullish, some bearish),
    reflect this in sentiment_trend as "mixed" and explicitly note 
    the contradiction in inflections rather than simply averaging them into 
    a neutral score.

    **Score calibration**
    - 0.8 to 1.0: transformative positive news (major earnings beat, blockbuster product launch)
    - 0.4 to 0.8: clearly positive coverage with meaningful upside signals
    - -0.2 to 0.4: mixed or mildly positive, no strong directional signal
    - -0.4 to -0.2: mildly negative, some concerns but not alarming
    - -0.8 to -0.4: clearly negative, meaningful downside risks
    - -1.0 to -0.8: severe negative news (fraud, massive miss, existential threat

    **Risk Identification**
    - Flag any "latent risks": topics mentioned only once or twice that could 
    escalate based on pattern recognition from similar historical situations"""

    tools = [
        {
            "name": "record_sentiment",
            "description": "Record the sentiment analysis of news headlines for a stock",
            "input_schema": {
                "type": "object",
                "properties": {
                    "overall": {
                        "type": "string",
                        "enum": ["bullish", "neutral", "bearish"],
                        "description": "Overall sentiment of the headlines"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "How confident are you in this assessment given the volume and quality of avaliable news"
                    },
                    "score": {
                        "type": "number",
                        "description": "Sentiment score between -1.0 (very bearish) and 1.0 (very bullish)"
                    },
                    "sentiment_trend": {
                        "type": "string",
                        "enum": ["improving", "worsening", "stable", "mixed"],
                        "description": "Explicitly identify how the sentimet is changing over the timeline" 
                    },
                    "themes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "trajectory": {"type": "string", "enum": ["building", "peaking", "fading", "stable", "deteriorating"]},
                                "description": {"type": "string"}
                            },
                            "required": ["trajectory", "description"]
                        },
                        "description": "2-5 dominant themes from the headlines and their trajectory"
                    },
                    "inflections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Moments where coverage tone meaningfully shifted and what triggered it.  Return empty list if insufficient timeline to identify shifts."
                    },
                    "risk_flags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "description": {"type": "string"}
                            },
                            "required": ["severity", "description"]
                        },
                        "description": "One line description of specific risks or concerns with severity ratings"
                    },
                    "catalysts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "One line description of potential positive catalysts mentioned"
                    },
                    "latent_risks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "One line description of topics mentioned briefly that may escalate"
                    }
                },
                "required": ["overall", "confidence", "score", "sentiment_trend", "themes", "inflections", "risk_flags", "catalysts", "latent_risks"]
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
                    "content": f"Out of {news_total_count} articles retrieved mentioning {company_name} ({ticker}), {news_filtered_count} were filtered as irrelevant. Please analyze the remaining relevant articles (capped at {MAX_FOR_LLM}):\n\n{headlines_text}"
                }
            ]
        )
        tool_use_block = next(
            block for block in response.content 
            if block.type == "tool_use"
        )
        result = tool_use_block.input
        result["headline_count"] = len(news_items)
        sentiment = SentimentReport(**result)
    except Exception as e:
        return {"errors": errors + [f"sentiment analysis failed: {e}"]}

    return {
        "sentiment": sentiment,
        "errors": errors
    }