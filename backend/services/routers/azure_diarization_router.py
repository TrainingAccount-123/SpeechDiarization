from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
import logging
import subprocess
import asyncio
from pydantic import BaseModel
from datetime import datetime

from services.utils.azure_speech_diarizaiton import ConversationTranscriber
from config import UPLOAD_DIR, MAX_AUDIO_DURATION_SECS

router = APIRouter(prefix="/azure_diarization", tags=["azure_captions"])

azure_dia_obj = ConversationTranscriber()

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(UPLOAD_DIR)

@router.post("/get_captions")
async def get_captions(file : UploadFile = File(...)):
    try:
        start = datetime.now()

        contents = await file.read()
        filepath = UPLOAD_DIR / file.filename
        with open(filepath,"wb") as f:
            f.write(contents)

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(filepath)
        ]

        duration = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        duration = float(duration.stdout.strip())

        if duration>MAX_AUDIO_DURATION_SECS:
            raise RuntimeError("Audio File cannot be more than 1 hour 45 minutes long")

        converted_filepath = filepath.with_name(filepath.stem + "_16k.wav")
        command = [
            "ffmpeg",
            "-y",
            "-i", str(filepath),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(converted_filepath)
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        filepath.unlink()

        conversion_time = datetime.now()
        logger.info(f"Conversion time {conversion_time-start}")

        if result.returncode != 0:
            raise RuntimeError(f"File Either does not contain audio or is corrupted {result.stderr}")
        
        else:
            converted_filepath = str(converted_filepath.resolve()).replace("\\","/")

            captions = azure_dia_obj.recognize_from_file(converted_filepath)
            logger.info(f"Ending Process. Total Time Taken : {datetime.now() - start}")

            return {"diarization" : captions}

    except RuntimeError as rte:
        raise HTTPException(status_code=422,detail=f"{rte}")

    except ValueError as ve:
        raise HTTPException(status_code=422,detail=f"{ve}")

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
        all_speakers = {d["speaker"] for d in diarization}
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
            if len(diarization)>3:
                if diarization.index(segment) in[0,1,2]:
                    continue
            speaker = segment["speaker"]
            if speaker in seen_speakers:
                continue

            start = float(segment["timestamp"]["start"])
            end = float(segment["timestamp"]["end"])
            duration = end - start

            if duration<7.5:
                continue
            else:
                seen_speakers.add(speaker)

                out_file = UPLOAD_DIR / "speakers" / f"{speaker}.flac"

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
        
        
        for segment in diarization:
            unvisited_speakers = all_speakers-seen_speakers
            if not unvisited_speakers:
                break
            if segment["speaker"] not in unvisited_speakers:
                continue
            else:
                out_file = UPLOAD_DIR / "speakers" / f"{speaker}.flac"

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", audio_file,
                    "-ss", str(float(segment["timestamp"]["start"])),
                    "-t", str(float(segment["timestamp"]["start"])),
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

    except Exception:
        raise HTTPException(status_code=500,detail="Failed to Fetch Audio Segments")
            

        