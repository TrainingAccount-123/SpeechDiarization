from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
from services.utils.ffmpeg_filters import FFmpegFilters
from pathlib import Path
import asyncio
import os
import json
import datetime
import logging
import torchaudio
import subprocess


logger = logging.getLogger(__name__)

class CaptionExtractions:

    def __init__(self):
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            token=os.getenv("HF_AUTH_TOKEN")
        )

        self.model = WhisperModel("base", device="cpu")
    
    def _get_asr(self,input_audio):
        try:
            start = datetime.datetime.now()
            segments, info = self.model.transcribe(input_audio,beam_size=2,best_of=2,language="en")
            
            asr_segments= [
                {
                    "timestamp" : {"start" : segment.start, "end": segment.end},
                    "text" : segment.text
                    }
                    for segment in segments
            ]

            logger.info(f"ASR Time taken {datetime.datetime.now() - start}")

            return asr_segments
        
        except Exception:
            raise

    def _get_diarization(self, input_audio):
        try:
            start = datetime.datetime.now()
            command = FFmpegFilters.audio_speedup(input_audio)
            new_fp = command[-1]
            try:
                subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
            except Exception:
                raise
            waveform, sample_rate = torchaudio.load(new_fp)
            diarization = self.pipeline({
                "waveform" : waveform,
                "sample_rate" : sample_rate
            })
            diarized = []

            for turn,speaker in diarization.speaker_diarization:
                diarized.append(
                    {
                        "timestamp" : {
                            "start" : turn.start*1.2,
                            "end" : turn.end*1.2
                        },
                        "speaker" : speaker
                    }
                )

            logger.info(f"Diarization Time Taken {datetime.datetime.now()-start}")

            Path(new_fp).unlink()

            return diarized

        except Exception:
            raise


    async def get_diarized_captions(self, input_audio, start_time):
        try:
            asr_task = asyncio.to_thread(self._get_asr, input_audio)
            dia_task = asyncio.to_thread(self._get_diarization, input_audio)
            asr_segments, diarized_segments = await asyncio.gather(asr_task, dia_task)

            if not asr_segments:
                raise ValueError("No speech detected in provided file")

            if not diarized_segments:
                raise ValueError("No diarization detected in provided file")

            asr_segments.sort(key=lambda x: x["timestamp"]["start"])
            diarized_segments.sort(key=lambda x: x["timestamp"]["start"])

            with open("saver.json", "w") as f:
                json.dump(diarized_segments, f)

            aligned_segments = []
            asr_idx = 0  

            for dia in diarized_segments:
                dia_start = dia["timestamp"]["start"]
                dia_end = dia["timestamp"]["end"]
                speaker = dia["speaker"]

                texts = []

                while asr_idx < len(asr_segments):
                    asr = asr_segments[asr_idx]
                    asr_start = asr["timestamp"]["start"]
                    asr_end = asr["timestamp"]["end"]
\
                    if asr_end <= dia_start:
                        asr_idx += 1
                        continue

                    if asr_start >= dia_end:
                        break

                    texts.append(asr["text"].strip())
                    asr_idx += 1

                if texts:
                    aligned_segments.append({
                        "start": dia_start,
                        "end": dia_end,
                        "text": " ".join(texts),
                        "speaker": speaker
                    })

            merged = [aligned_segments[0]] if aligned_segments else []
            for current in aligned_segments[1:]:
                previous = merged[-1]
                same_speaker = current["speaker"] == previous["speaker"]
                gap = current["start"] - previous["end"]

                if same_speaker and gap <= 0.4:
                    previous["end"] = current["end"]
                    previous["text"] += " " + current["text"]
                else:
                    merged.append(current)

            captions = [
                {
                    "timestamp": {"start": seg["start"], "end": seg["end"]},
                    "text": seg["text"],
                    "speaker": seg["speaker"]
                }
                for seg in merged
            ]

            logger.info(f"Ending Process. Total Time Taken {datetime.datetime.now() - start_time}")
            return captions

        except ValueError:
            raise

        except Exception:
            raise