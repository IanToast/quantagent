from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes.fetch_price import fetch_price_node
from agent.nodes.fetch_news import fetch_news_node
from agent.nodes.fetch_sentiment_analysis import fetch_sentiment_analysis_node
from agent.nodes.fetch_research_report import fetch_research_report_node
from agent.nodes.fetch_metadata import fetch_metadata_node

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

    graph.add_edge("fetch_price", "synthesize")
    graph.add_edge("sentiment", "synthesize")

    graph.add_edge("synthesize", END)

    app = graph.compile()
    return app