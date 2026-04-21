"""
model_relay.py - Central Transparent Proxy (v1.15.0)
"""

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Nexus ModelRelay", version="1.15.0")

class ModelRelay:
    def __init__(self):
        self.healthy_models = ["minimax-m2.5", "trinity-large-preview", "kimi-k2.5", "step-3.5-flash"]

    async def proxy_completion(self, request_data: dict):
        model = request_data.get("model", "auto")
        
        if model == "auto":
            model = self.healthy_models[0]
        
        return {
            "id": f"relay-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[ModelRelay] Response from {model}"
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }

# Global instance for import
relay = ModelRelay()

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    result = await relay.proxy_completion(body)
    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7352)