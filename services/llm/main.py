"""
LLM Service — proxies requests to OpenRouter API
Accepts history as a JSON string to avoid n8n array serialization issues.
"""
import os
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Service", version="1.0.0")

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL          = os.getenv("LLM_MODEL", "openrouter/free")


class ChatRequest(BaseModel):
    transcript:   str
    history_json: str = "[]"   # history passed as JSON string — avoids n8n array issues
    context:      str = ""
    system_prompt: str = ""


@app.get("/health")
async def health():
    return {
        "status":      "ok",
        "model":       MODEL,
        "api_key_set": bool(OPENROUTER_KEY)
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if not OPENROUTER_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    # Parse history from JSON string
    try:
        history = json.loads(req.history_json) if req.history_json else []
    except Exception:
        history = []

    # Build system prompt
    base_prompt = req.system_prompt or (
        "You are a helpful AI support agent for NorthStar Bank. "
        "Answer the user's question using ONLY the context provided below. "
        "If the answer is not in the context, say: I don't have that information — "
        "please contact support directly. "
        "Keep all answers under 3 sentences."
    )
    system_content = base_prompt + "\n\nKNOWLEDGE BASE CONTEXT:\n" + req.context

    # Build full messages array
    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.transcript})

    logger.info(f"Calling OpenRouter API: {len(messages)} messages, model={MODEL}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "http://localhost:3000",
                },
                json={
                    "model":       MODEL,
                    "messages":    messages,
                    "max_tokens":  300,
                    "temperature": 0.3,
                }
            )
            response.raise_for_status()
            data  = response.json()
            reply = data["choices"][0]["message"]["content"]
            logger.info(f"Reply: {reply[:80]}")
            return {"reply": reply, "model": MODEL}

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter API error: {e.response.text}")
        raise HTTPException(status_code=502, detail=f"OpenRouter API error: {e.response.text}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
