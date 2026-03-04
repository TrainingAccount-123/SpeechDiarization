from deepgram import DeepgramClient
from pathlib import Path
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_KEY")

UPLOAD_DIR = Path("./files").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class DeepgramDiarizations:

    async def _process_returns(self,words_list):
        try:
            captions = []

            text = ""
            speaker = 999
            start = 0.0
            end = 0.0

            punctuation_symbols_list = [".","?","!","\"","'","`"]
                
            for i,item in enumerate(words_list):
                text += f" {item.punctuated_word}"
                if i == 0:
                    start = item.start
                    speaker = item.speaker
                elif i == len(words_list) -1:
                    end = item.end
                    captions.append({
                        "timestamp" : {
                            "start" : start,
                            "end" : end
                        },
                        "speaker" : str(speaker),
                        "text" : text
                    })
                    break
                if item.punctuated_word[-1] in punctuation_symbols_list or words_list[i+1].start - item.end>2:
                    if words_list[i+1].speaker != speaker:
                        end = item.end
                        captions.append({
                            "timestamp" : {
                                "start" : start,
                                "end" : end
                            },
                            "speaker" : str(speaker),
                            "text" : text
                        })
                        start = words_list[i+1].start
                        speaker = words_list[i+1].speaker
                        text = ""
                    else:
                        continue
            return captions
        except Exception:
            raise
    
    async def get_captions(self,filepath):
        try:
            logger.info("Starting with Deepgram Nova 3")
            start_time = datetime.now()

            deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)

            with open(filepath,"rb") as f:
                response = deepgram.listen.v1.media.transcribe_file(
                    request=f,
                    model="nova-3",
                    language="en-IN",
                    smart_format=True,
                    diarize=True,
                    punctuate=True,
                    
                )

            captions = await self._process_returns(response.results.channels[0].alternatives[0].words)
            
            logger.info(f"Total Time Taken To Complete {datetime.now()-start_time}")

            return captions

        except Exception:
            raise
