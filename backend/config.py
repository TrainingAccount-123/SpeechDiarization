import os

ASSEMBLY_AI_API = os.getenv("ASSEMBLYAI_API_KEY")
UPLOAD_DIR = "./files"
MAX_AUDIO_DURATION_SECS = 6240
GROQ_API_KEY = os.getenv("GROQ_API_KEY_1")
OPENAI_API_KEY = os.getenv("NEW_OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.core42.ai/v1"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_KEY")

ALLOWED_MIME_TYPES = {
    # Audio
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/flac", "audio/ogg", "audio/aac", "audio/mp4",
    "audio/webm", "audio/x-m4a",
    # Video
    "video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo",
    "video/webm", "video/x-matroska", "video/x-ms-wmv"
}