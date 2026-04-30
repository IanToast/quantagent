from agent.graph import build_graph

app = build_graph()
result = app.invoke({"ticker": "JPM", "errors": []})

# print(result)
print(result.get("errors"))
print(result.keys())
print("="*50)
print(result["research_report"])
