from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes.fetch_price import fetch_price_node
from agent.nodes.fetch_news import fetch_news_node
from agent.nodes.fetch_sentiment_analysis import fetch_sentiment_analysis_node
from agent.nodes.fetch_research_report import fetch_research_report_node
from agent.nodes.fetch_metadata import fetch_metadata_node

# def start_node(state):
#         return {}  # does nothing, just fans out

# def should_synthesize(state):
#     has_price_summary = state.get("price_summary") is not None
#     has_quant_signals = state.get("quant_signals") is not None
#     has_sentiment_analysis = state.get("sentiment") is not None
#     if has_price_summary and has_quant_signals and has_sentiment_analysis:
#         return "synthesize"
#     return END

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_metadata", fetch_metadata_node)
    graph.add_node("fetch_price", fetch_price_node)
    graph.add_node("fetch_news", fetch_news_node)
    graph.add_node("sentiment", fetch_sentiment_analysis_node)
    graph.add_node("synthesize", fetch_research_report_node, defer=True)

    graph.add_edge(START, "fetch_metadata")
    graph.add_edge(START, "fetch_price")

    graph.add_edge("fetch_metadata", "fetch_news")
    graph.add_edge("fetch_news", "sentiment")

    # graph.add_conditional_edges("fetch_price", should_synthesize, {"synthesize": "synthesize", END: END})
    # graph.add_conditional_edges("sentiment", should_synthesize, {"synthesize": "synthesize", END: END})

    graph.add_edge("fetch_price", "synthesize")
    graph.add_edge("sentiment", "synthesize")

    graph.add_edge("synthesize", END)

    app = graph.compile()
    return app