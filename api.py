import os
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
load_dotenv()

from agent.graph import build_graph

app = FastAPI(title="QuantAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

MY_API_KEY = os.getenv("MY_API_KEY")

graph = build_graph()

@app.get("/report")
async def get_report(
    ticker: str,
    x_api_key: str = Header(None)
):
    # Auth check
    if not MY_API_KEY or x_api_key != MY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    
    # Run pipeline
    result = graph.invoke({"ticker": ticker, "errors": []})

    # Check for failure
    if not result.get("research_report"):
        errors = result.get("errors", ["Unknown error"])
        logger.error(f"Pipeline failed for {ticker}: {errors}")  # internal only
        raise HTTPException(
            status_code=500, 
            detail="Report generation failed. Please try again later."  # generic external message
        )
    return result["research_report"].model_dump(mode="json")

@app.get("/health")
async def health():
    return {"status": "ok"}