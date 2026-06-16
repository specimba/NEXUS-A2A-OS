"""Relay Serving — FastAPI dashboard on port 7355."""

from __future__ import annotations
from typing import Optional
from fastapi import FastAPI, Query
from nexus_os.relay.bridge_client import ModelRelayBridge
from nexus_os.relay.intent_classifier import PromptIntentClassifier

app = FastAPI(title="Nexus Model Relay Dashboard")
relay = ModelRelayBridge()
classifier = PromptIntentClassifier()


@app.get("/health")
async def health():
    refresh = relay.get_refresh_status()
    up_count = len(relay.get_models_up())
    return {
        "status": "ok",
        "service": "nexus-model-relay",
        "port": 7355,
        "models_total": refresh["models_count"],
        "models_up": up_count,
        "last_refresh": refresh["last_refresh"],
        "next_refresh_in": refresh["next_refresh_in"],
    }


@app.get("/api/v1/models")
async def get_models():
    return {"models": list(relay.models.values()), "count": len(relay.models)}


@app.get("/models/up")
async def get_models_up():
    return {"models": relay.get_models_up(), "count": len(relay.get_models_up())}


@app.get("/models/ranked/{dimension}")
async def get_ranked(dimension: str = "overall", top_k: int = Query(default=10, le=50)):
    return {"models": relay.get_ranked_by(dimension, top_k), "dimension": dimension}


@app.get("/models/best/{intent}")
async def get_best_for_intent(intent: str = "code", top_k: int = Query(default=5, le=20)):
    return {"models": relay.get_best_for_intent(intent, top_k), "intent": intent}


@app.get("/fastest")
async def get_fastest(top_k: int = Query(default=5, le=20)):
    return {"models": relay.get_fastest_online(top_k)}


@app.get("/highest-scored")
async def get_highest_scored(dimension: str = "overall", top_k: int = Query(default=5, le=20)):
    return {"models": relay.get_highest_scored(dimension, top_k), "dimension": dimension}


@app.post("/api/v1/best")
async def best_for_prompt(prompt: str, top_k: int = Query(default=3, le=10)):
    result = classifier.classify(prompt)
    best = relay.get_best_for_intent(result.intent.value, top_k)
    return {
        "prompt": prompt,
        "classified_intent": result.intent.value,
        "confidence": result.confidence,
        "models": best,
    }


@app.get("/refresh")
async def refresh():
    relay.refresh()
    return {"status": "refreshed", "models_count": len(relay.models)}


@app.get("/intent-classify")
async def intent_classify(prompt: str = Query(default="hello")):
    result = classifier.classify(prompt)
    return {
        "prompt": prompt,
        "intent": result.intent.value,
        "confidence": result.confidence,
        "keywords_found": result.keywords_found,
    }
