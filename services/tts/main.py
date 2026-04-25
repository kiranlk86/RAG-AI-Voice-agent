"""
Text-to-Speech Service using edge-tts 7.2.8+
No model download, no API key, 400+ voices
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TTS Service", version="1.0.0")

# Curated voice presets for demos
VOICE_PRESETS = {
    "female-us":  "en-US-AriaNeural",
    "male-us":    "en-US-GuyNeural",
    "female-uk":  "en-GB-SoniaNeural",
    "male-uk":    "en-GB-RyanNeural",
    "female-au":  "en-AU-NatashaNeural",
    "male-au":    "en-AU-WilliamNeural",
    "female-ca":  "en-CA-ClaraNeural",
}


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"    # "+20%" = faster, "-10%" = slower
    volume: str = "+0%"  # "+10%" = louder
    pitch: str = "+0Hz"  # "+50Hz" = higher pitch


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "edge-tts", "version": "7.2.8+"}


@app.get("/voices")
async def list_voices():
    return {"presets": VOICE_PRESETS}


@app.post("/synthesize")
async def synthesize(req: TTSRequest):
    """Convert text to speech, return MP3 audio stream."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice,
            rate=req.rate,
            volume=req.volume,
            pitch=req.pitch,
        )
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)

        if buf.getbuffer().nbytes == 0:
            raise HTTPException(status_code=500, detail="TTS produced no audio")

        logger.info(f"Synthesized {len(req.text)} chars with voice {req.voice}")
        return StreamingResponse(buf, media_type="audio/mpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
