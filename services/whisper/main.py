"""
Whisper Speech-to-Text Service
faster-whisper 1.1+ with robust ffmpeg conversion
"""
import os
import tempfile
import subprocess
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper STT", version="1.0.0")

MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
logger.info(f"Loading Whisper model: {MODEL_SIZE}")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
logger.info("Whisper model ready")


def convert_to_wav(input_path: str) -> str:
    """
    Convert any browser audio format to 16kHz mono WAV.
    Uses ffmpeg with format probing — does not rely on file extension.
    """
    output_path = input_path + ".wav"

    cmd = [
        "ffmpeg", "-y",
        "-err_detect", "ignore_err",   # ignore minor stream errors
        "-i", input_path,
        "-vn",                          # drop video stream if present
        "-acodec", "pcm_s16le",         # uncompressed PCM — Whisper optimal
        "-ar", "16000",                 # 16kHz sample rate
        "-ac", "1",                     # mono
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(output_path):
        logger.error(f"ffmpeg stdout: {result.stdout[-500:]}")
        logger.error(f"ffmpeg stderr: {result.stderr[-500:]}")
        raise RuntimeError(
            f"Audio conversion failed. ffmpeg could not read the file. "
            f"Last error: {result.stderr.splitlines()[-1] if result.stderr else 'unknown'}"
        )

    size = os.path.getsize(output_path)
    if size < 1000:
        raise RuntimeError(f"Converted WAV is too small ({size} bytes) — audio may be empty")

    logger.info(f"Converted to WAV: {size} bytes")
    return output_path


@app.get("/health")
async def health():
    return {"status": "ok", "model": f"faster-whisper-{MODEL_SIZE}"}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Transcribe an audio file to text."""
    filename = audio.filename or "audio.bin"
    content  = await audio.read()

    if len(content) < 100:
        raise HTTPException(status_code=400, detail="Audio file is empty or too small")

    logger.info(f"Received audio: {filename}, size: {len(content)} bytes")

    # Save with original extension so ffmpeg gets a hint, but we also
    # use -err_detect ignore_err so it doesn't give up on minor issues
    suffix = os.path.splitext(filename)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    wav_path = None
    try:
        wav_path = convert_to_wav(tmp_path)

        segments, info = model.transcribe(wav_path, beam_size=5)
        transcript = " ".join(s.text for s in segments).strip()

        logger.info(f"Transcript [{info.language} {info.language_probability:.2f}]: '{transcript[:80]}'")

        return {
            "transcript": transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
        }

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for path in [tmp_path, wav_path]:
            if path and os.path.exists(path):
                os.unlink(path)
