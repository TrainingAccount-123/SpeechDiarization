import assemblyai as aai
from config import ASSEMBLY_AI_API

class AssemblyDiarization:

    def __init__(self):
        self.__api_key = ASSEMBLY_AI_API

    def generate_captions(self,filepath):
        try:
            aai.settings.api_key = self.__api_key

            transcriber = aai.Transcriber()

            config = aai.TranscriptionConfig(
                speech_models=["universal-3-pro"],
                language_detection=True,
                speaker_labels=True,
                speaker_options=aai.SpeakerOptions(
                    min_speakers_expected=3,
                    max_speakers_expected=5
                ),
            )

            transcript = transcriber.transcribe(filepath,config)

            def serialize_utterance(u):
                return {
                    "speaker": u.speaker,
                    "timestamp" : {
                        "start": u.start/1000,
                        "end": u.end/1000
                    },
                    "confidence": u.confidence,
                    "text": u.text,
                }
            
            return [serialize_utterance(u) for u in transcript.utterances]

        except Exception:
            raise
