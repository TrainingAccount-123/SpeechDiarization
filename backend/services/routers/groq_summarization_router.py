from fastapi import APIRouter, HTTPException
from services.utils.groq_openai_oss_summarization import GroqSummarization
from pydantic import BaseModel
from groq import APIStatusError

router = APIRouter(prefix="/summarize_groq", tags=["summarization"])

summarization_obj = GroqSummarization()

class GetSummaryPayload(BaseModel):
    captions : list[dict]

@router.post("/get_summary")
async def get_summary(payload : GetSummaryPayload):
    try:
        captions = payload.captions
        return await summarization_obj.summarize_meeting(captions)

    except APIStatusError:
        raise HTTPException(status_code=429, detail="Message Too Large")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected Error Occurred")