from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
from pydantic import BaseModel
import asyncio
import subprocess
from services.utils.assembly_diarization import AssemblyDiarization
from datetime import datetime
import logging
from services.utils.ffmpeg_filters import FFmpegFilters

router = APIRouter(prefix="/captions", tags=["captions"])

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./files")

aai_dia_obj = AssemblyDiarization()

@router.post("/assemblyai")
async def get_assemblyai_transcripts(file : UploadFile = File(...)):
    try:
        logger.info("Starting with assembly AI")
        start = datetime.now()

        contents = await file.read()
        filepath = UPLOAD_DIR / file.filename
        with open(filepath,"wb") as f:
            f.write(contents)

        converted_filepath = filepath.with_name(filepath.stem + "_16k.mp3")
        command = await FFmpegFilters.mp3_conversion_filter(filepath, converted_filepath)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        conversion_time = datetime.now()
        logger.info(f"Conversion time {conversion_time-start}")

        if result.returncode != 0:
            raise RuntimeError("FFmpeg file conversion failed. File Either does not contain audio or is corrupted")
        
        else:
            filepath = str(filepath)
            captions = aai_dia_obj.generate_captions(filepath)
            Path(filepath).unlink()
            
            logger.info(f"Ending Process. Total Time Taken : {datetime.now() - start}")

            return {"diarization" : captions}

    except RuntimeError as rte:
        raise HTTPException(status_code=422,detail=f"{rte}")    

    except Exception:
        raise HTTPException(status_code=500,detail="Unexpected Error Occurred")


class GetSegmentsInput(BaseModel):
    audio_file: str
    diarization : list


@router.post("/get_audio_segments")
async def extract_first_speaker_segments(payload : GetSegmentsInput):
    try:
        audio_file = payload.audio_file
        diarization = payload.diarization
        seen_speakers = set()
        tasks = []
        results = {}

        speakers_dir = UPLOAD_DIR / "speakers"

        for p in speakers_dir.iterdir():
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink()
                elif p.is_dir():
                    for sub in p.rglob("*"):
                        if sub.is_file() or sub.is_symlink():
                            sub.unlink()
                    p.rmdir()
            except PermissionError:
                p.unlink(missing_ok=True)

        async def _run_ffmpeg(cmd):
            return await asyncio.to_thread(
                subprocess.run,
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        for segment in diarization:
            speaker = segment["speaker"]
            if speaker in seen_speakers:
                continue

            start = float(segment["timestamp"]["start"])
            end = float(segment["timestamp"]["end"])
            duration = end - start

            seen_speakers.add(speaker)

            out_file = UPLOAD_DIR / "speakers" / f"{speaker}.mp3"

            cmd = [
                "ffmpeg",
                "-y",
                "-i", audio_file,
                "-ss", str(start),
                "-t", str(duration),
                "-c", "copy",
                str(out_file)
            ]

            tasks.append(
                {
                    "speaker": speaker,
                    "file": (out_file),
                    "task": _run_ffmpeg(cmd)
                }
            )

        ffmpeg_results = await asyncio.gather(*(t["task"] for t in tasks))

        for meta, proc in zip(tasks, ffmpeg_results):
            if proc.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed for {meta['speaker']}: {proc.stderr}"
                )
            fname = str(meta["file"].name)
            results[meta["speaker"]] = f"http://localhost:8000/audio_files/{fname}"

        Path(audio_file).unlink()
        return results
    except RuntimeError as rte:
        raise HTTPException(status_code=500, detail=f"{rte}")

    except Exception:
        raise HTTPException(status_code=500,detail="Unexpected Error Occurred")

