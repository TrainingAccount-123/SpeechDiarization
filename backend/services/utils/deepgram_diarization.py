from deepgram import DeepgramClient
from pathlib import Path
import logging
import json
from config import DEEPGRAM_API_KEY
from datetime import datetime

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./files").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class DeepgramDiarizations:

    async def _process_returns_with_confidence(self,words_list):
        try:
            captions = []
            text = ""
            speaker = 9999
            start = 0.0
            end = 0.0
            confidence = 0.0

            for i,item in enumerate(words_list):
                text += f" {item.punctuated_word}"
                if i == 0:
                    confidence = item.speaker_confidence
                    start = item.start
                    speaker = item.speaker
                if confidence == item.confidence:
                    continue
                elif ((confidence/2)-0.025)<item.speaker_confidence and item.speaker_confidence<((confidence/2)+0.025):
                    #this heuristic calculates that if the speaker is given a different label by the model, what is the chance that the speaker is actually the same as the previous based on the speakr confidence scores provided by deepgram nova 3
                    pass
                elif item.speaker == speaker:
                    #same speaker so we continue the text here too, we dont want to append to the captions yet
                    pass
                else:
                    end = words_list[i-1].end
                    captions.append({
                        "timestamp" : {
                            "start" : start,
                            "end" : end
                        },
                        "speaker" : speaker,
                        "text" : text[:-(len(item.punctuated_word)+1)]
                    })
                    start = item.start
                    text = f"{item.punctuated_word}"
                    speaker = item.speaker

            return captions
        except Exception:
            raise

    async def _process_returns(self,words_list):
        try:
            captions = []

            words = []

            text = ""
            speaker = 999
            start = 0.0
            end = 0.0

            punctuation_symbols_list = [".","?","!","\"","'","`"]
                
            for i,item in enumerate(words_list):

                words.append({
                    "word" : item.punctuated_word,
                    "speaker" : item.speaker,
                    "confidence" : item.speaker_confidence
                })
                text += f" {item.punctuated_word}"
                if i == 0:
                    start = item.start
                    speaker = item.speaker
                elif i == len(words_list) -2:
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
                    if (words_list[i+1].speaker != speaker and words_list[i+2].speaker != speaker 
                        # and not ((item.speaker_confidence/2)-0.025 <= words_list[i+1].speaker_confidence <= (item.speaker_confidence/2)+0.025)
                        ):
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

            with open("saver2.json","w") as f:
                json.dump(words,f)
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
                    punctuate=True
                    
                )
            
            print("Deepgram capitons got")

            captions = await self._process_returns(response.results.channels[0].alternatives[0].words)
            
            logger.info(f"Total Time Taken To Complete {datetime.now()-start_time}")

            return captions

        except Exception:
            raise
