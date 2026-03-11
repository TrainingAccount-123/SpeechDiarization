import json
import yaml
from groq import Groq
from config import GROQ_API_KEY

class GroqSummarization:
    def __init__(self):
        try:
            self.client = Groq(
                api_key=GROQ_API_KEY,
            )
        except Exception:
            raise

    async def format_transcript(self,captions: list[dict]) -> str:
        try:
            lines = []
            for entry in captions:
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("text", "")
                lines.append(f"{speaker}: {text}")
            return "\n".join(lines)

        except Exception:
            raise

    async def summarize_meeting(self,captions: list[dict]) -> dict:
        try:
            transcript = await self.format_transcript(captions)

            with open("services/utils/prompts/prompts.yaml") as f:
                prompts = yaml.safe_load(f)

            prompt_template = prompts["meeting_summary"]["gpt_oss_120b"]

            prompt = ""

            for key in prompt_template:
                prompt = prompt + key.title() + ":\n" + prompt_template[key] + "\n\n"

            response = self.client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role" : "user",
                        "content" : transcript
                    }
                ],
            )

            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            return result

        except Exception:
            raise
