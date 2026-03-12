from fastapi import APIRouter, HTTPException, UploadFile, File
from services.utils.whisper_pyannote_diarization import CaptionExtractions
from services.utils.ffmpeg_filters import FFmpegFilters
import subprocess

from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["captions_test"])

captions_obj = CaptionExtractions()

UPLOAD_DIR = Path("./files")

@router.get("/get_captions")
async def get_captions(file: UploadFile = File(...)):
    try:
        logger.info("Starting Process")
        start = datetime.now()

        contents = await file.read()
        filepath = UPLOAD_DIR / file.filename
        with open(filepath,"wb") as f:
            f.write(contents)

        read_time = datetime.now()
        logger.info(f"File Read Time {read_time-start}")

        converted_filepath = filepath.with_name(filepath.stem + "_16k.mp3")
        command = await FFmpegFilters.mp3_conversion_filter(filepath, converted_filepath)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        conversion_time = datetime.now()
        logger.info(f"Conversion time {conversion_time-read_time}")

        if result.returncode != 0:
            raise RuntimeError("FFmpeg file conversion failed. File Either does not contain audio or is corrupted")
        else:
            filepath.unlink()

        captions = await captions_obj.get_diarized_captions(converted_filepath,start)

        return captions

    except RuntimeError as rte:
        raise HTTPException(status_code=500,detail=f"{rte}")

    except ValueError as ve:
        raise HTTPException(status_code=422,detail=f"{ve}")

    except Exception:
        raise HTTPException(status_code=500,detail="Unexpected Error Occurred")



