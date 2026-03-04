import os
import time
import azure.cognitiveservices.speech as speechsdk
import logging

logger = logging.getLogger(__name__)

class ConversationTranscriber:
    def __init__(self):
        self._transcriptions = []
        self._cancel_on_error = False

    def _conversation_transcriber_recognition_canceled_cb(self, evt: speechsdk.SessionEventArgs):
        try:
            logger.info('Canceled event')
        except Exception:
            raise

    def _conversation_transcriber_session_stopped_cb(self, evt: speechsdk.SessionEventArgs):
        try:
            logger.info('SessionStopped event')
        except Exception:
            raise        

    def _conversation_transcriber_transcribed_cb(self, evt: speechsdk.SpeechRecognitionEventArgs):
        try:
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                start_sec = evt.result.offset / 10_000_000
                end_sec = (evt.result.offset + evt.result.duration) / 10_000_000
                self._transcriptions.append({
                    "timestamp" : {
                        "start" : start_sec,
                        "end" : end_sec
                    },
                    "speaker" : evt.result.speaker_id,
                    "text" : evt.result.text
                })
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                self._cancel_on_error = True
        except Exception:
            raise

    def _conversation_transcriber_session_started_cb(self, evt: speechsdk.SessionEventArgs):
        try:
            logger.info('SessionStarted event')
        except Exception:
            raise

    def recognize_from_file(self, filename):
        try:
            self._transcriptions.clear()
            self._cancel_on_error = False
            speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), endpoint=os.environ.get('ENDPOINT'))
            speech_config.speech_recognition_language="en-US"
            speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, value='true')
            if os.path.isfile(filename):
                audio_config = speechsdk.audio.AudioConfig(filename=filename)
            else:
                raise ValueError("Invalid Filename Given")
            conversation_transcriber = speechsdk.transcription.ConversationTranscriber(speech_config=speech_config, audio_config=audio_config)

            transcribing_stop = False

            def _stop_cb(evt: speechsdk.SessionEventArgs):
                logger.info('CLOSING on {}'.format(evt))
                nonlocal transcribing_stop
                transcribing_stop = True

            # Connect callbacks to the events fired by the conversation transcriber
            conversation_transcriber.transcribed.connect(self._conversation_transcriber_transcribed_cb)
            conversation_transcriber.session_started.connect(self._conversation_transcriber_session_started_cb)
            conversation_transcriber.session_stopped.connect(self._conversation_transcriber_session_stopped_cb)
            conversation_transcriber.canceled.connect(self._conversation_transcriber_recognition_canceled_cb)
            # stop transcribing on either session stopped or canceled events
            conversation_transcriber.session_stopped.connect(_stop_cb)
            conversation_transcriber.canceled.connect(_stop_cb)

            conversation_transcriber.start_transcribing_async()

            # Waits for completion.
            while not transcribing_stop:
                if self._cancel_on_error:
                    break
                time.sleep(.5)

            conversation_transcriber.stop_transcribing_async()

            if not self._cancel_on_error:
                return self._transcriptions
            else:
                raise ValueError('Speech could not be TRANSCRIBED')
        
        except ValueError:
            raise

        except Exception:
            raise




