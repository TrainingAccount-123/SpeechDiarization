from fastapi import APIRouter, HTTPException, UploadFile, File
import subprocess
from pathlib import Path
import logging
from datetime import datetime
import asyncio
from pydantic import BaseModel


import json

from services.utils.deepgram_diarization import DeepgramDiarizations
from config import UPLOAD_DIR

router = APIRouter(prefix="/deepgram", tags=["deepgram"])

logger = logging.getLogger(__name__)

deepgram_dia_obj = DeepgramDiarizations()

UPLOAD_DIR = Path(UPLOAD_DIR)

@router.post("/get_captions")
async def get_captions(file : UploadFile = File(...)):
    try:
        start_time = datetime.now()
        logger.info("Starting Process")

        contents = await file.read()
        filepath = UPLOAD_DIR / file.filename
        with open(filepath,"wb") as f:
            f.write(contents)

        converted_filepath = filepath.with_name(filepath.stem + "_16k.flac")

        command = [
            "ffmpeg",
            "-y",
            "-i", str(filepath),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "flac",
            str(converted_filepath)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg file conversion failed. File Either does not contain audio or is corrupted {result.stderr}")
        
        else:
            logger.info(f"File Conversion completed in {datetime.now() - start_time}")

            captions = await deepgram_dia_obj.get_captions(str(filepath))

            with open("saver.json","w") as f:
                json.dump(captions,f)

            filepath.unlink()

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

    except RuntimeError as rte:
        raise HTTPException(status_code=500, detail=f"{rte}")

    except Exception:
        raise HTTPException(status_code=500,detail="Unexpected Error Occurred")