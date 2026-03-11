import yaml
import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL
import tiktoken
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenAISUmmaryGeneration:

    def __init__(self):
        try:
            self.client = OpenAI(
                base_url=OPENAI_BASE_URL,
                default_headers={"api-key": "<API_KEY>"},
                api_key=OPENAI_API_KEY,
            )
        except Exception:
            raise

    async def _format_transcript(self,captions: list[dict]) -> str:
        try:
            lines  = ""
            for entry in captions:
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("text", "")
                lines = lines + f"{speaker}: {text}"
            return lines
        except Exception:
            raise

    async def _load_prompt(self) -> str:
        try:
            path = "services/utils/prompts/prompts.yaml"
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            return data["meeting_summary"]["gpt_4_1"]["role"] + "\n" + data["meeting_summary"]["gpt_4_1"]["rules"]
        except Exception:
            raise

    def _count_tokens(self, text: str, model: str = "gpt-4.1") -> int:
        try:
            enc = tiktoken.encoding_for_model(model)
            return len(enc.encode(text))
        except Exception:
            raise

    async def summarize_meeting(self, transcript: list[dict]) -> dict:
        logger.info("starting summarization".title())
        start = datetime.now()
        try:
            system_prompt = await self._load_prompt()
            transcript_str = await self._format_transcript(transcript)

            prompt_token_count = self._count_tokens(system_prompt)
            transcript_token_count = self._count_tokens(transcript_str)
            total_token_count = prompt_token_count + transcript_token_count

            logger.info(f"Used {total_token_count} input tokens.")

            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript_str}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "meeting_summary",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "A 2-paragraph summary of the meeting"
                                },
                                "action_items": {
                                    "type": "array",
                                    "description": "List of pending action items",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["summary", "action_items"],
                            "additionalProperties": False
                        }
                    }
                }
            )

            logger.info(f"Ending Summarization. Total Time Taken {datetime.now()-start}")
            return json.loads(response.choices[0].message.content)
        except ValueError:
            raise
        except Exception:
            raise