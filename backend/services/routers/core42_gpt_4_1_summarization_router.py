from fastapi import APIRouter, HTTPException
from services.utils.core42_gpt_4_1_summarization import OpenAISUmmaryGeneration
from pydantic import BaseModel

router = APIRouter(prefix="/summarize",tags=["openai_summary"])

summary_generation_obj = OpenAISUmmaryGeneration()

class GetSummaryPayload(BaseModel):
    captions : list[dict]

@router.post("/get_summary")
async def get_summary(payload : GetSummaryPayload):
    try:
        captions = payload.captions
        return await summary_generation_obj.summarize_meeting(captions)

    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected Error Occurred")


