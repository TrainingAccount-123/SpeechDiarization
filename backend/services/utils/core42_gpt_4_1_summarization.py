import yaml
import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL

client = OpenAI(
    base_url=OPENAI_BASE_URL,
    default_headers={"api-key": "<API_KEY>"},
    api_key=OPENAI_API_KEY
)

class OpenAISUmmaryGeneration:
    async def load_prompt(self) -> str:
        path = "services/utils/prompts/prompts.yaml"
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return data["meeting_summary"]["gpt_4_1"]["role"] + "\n" + data["meeting_summary"]["gpt_4_1"]["rules"]


    async def summarize_meeting(self, transcript: list[dict]) -> dict:
        system_prompt = await self.load_prompt()
        transcript_str = json.dumps(transcript)

        response = client.chat.completions.create(
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
                                    "type": "object",
                                    "properties": {
                                        "responsible_party": {
                                            "type": "string",
                                            "description": "Speaker label responsible for the action"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "What needs to be done"
                                        },
                                        "requested_by": {
                                            "type": "string",
                                            "description": "Speaker label who requested this, if applicable"
                                        }
                                    },
                                    "required": ["responsible_party", "description", "requested_by"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["summary", "action_items"],
                        "additionalProperties": False
                    }
                }
            }
        )

        return json.loads(response.choices[0].message.content)