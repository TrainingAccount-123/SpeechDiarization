from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from config import UPLOAD_DIR

from loggers.logger import configure_logger
from services.routers.whisper_pyannote_router import router as whisper_pyannote_router
from services.routers.assemblyai_diarization_router import router as assemblyai_diarization_router
from services.routers.azure_diarization_router import router as azure_diarization_router
from services.routers.deepgram_diarization_router import router as deepgram_diarization_router
from services.routers.groq_summarization_router import router as groq_summarization_router

app = FastAPI(title="speech_diarization")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def load():
    configure_logger()

app.mount(
    "/audio_files",
    StaticFiles(directory=Path(UPLOAD_DIR) / "speakers"),
    name="audio"
)

app.include_router(whisper_pyannote_router)
app.include_router(assemblyai_diarization_router)
app.include_router(azure_diarization_router)
app.include_router(deepgram_diarization_router)
app.include_router(groq_summarization_router)

