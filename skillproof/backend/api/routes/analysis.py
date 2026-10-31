from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional
from schemas.candidate import AnalyzeRequest
from schemas.session import AnalyzeResponse
from database import repositories
from agents import orchestrator
from services.resume_service import extract_text_from_bytes, parse_resume, match_resume_to_repository

router = APIRouter(tags=['analysis'])

class ResumeParseRequest(BaseModel):
    resume_text: Optional[str] = None
    filename: Optional[str] = None

@router.post('/analyze', response_model=AnalyzeResponse, status_code=202)
def analyze(request: AnalyzeRequest, background: BackgroundTasks):
    from core.exceptions import AppError
    with orchestrator.schedule_lock:
        if len(orchestrator.scheduled) >= 20:
            raise AppError('Analysis queue full', 503, 'QUEUE_FULL')
    data = repositories.create(request.model_dump())
    # Dispatch after returning the QUEUED response. Durable rows are recovered on restart.
    background.add_task(orchestrator.submit, data['session_id'])
    return AnalyzeResponse(session_id=data['session_id'])

@router.post('/resume/parse')
async def parse_resume_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
):
    text = ""
    filename = "resume.txt"
    if file:
        content = await file.read()
        filename = file.filename or "uploaded_resume"
        text = extract_text_from_bytes(content, filename)
    else:
        try:
            body = await request.json()
            text = body.get("resume_text", "")
            filename = body.get("filename", "resume.txt")
        except Exception:
            pass

    parsed = parse_resume(text, filename)
    return {"status": "success", "profile": parsed}

@router.post('/session/{session_id}/resume')
async def attach_resume_to_session(
    session_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
):
    data = repositories.get(session_id)
    text = ""
    filename = "resume.txt"
    if file:
        content = await file.read()
        filename = file.filename or "uploaded_resume"
        text = extract_text_from_bytes(content, filename)
    else:
        try:
            body = await request.json()
            text = body.get("resume_text", "")
            filename = body.get("filename", "resume.txt")
        except Exception:
            pass

    parsed = parse_resume(text, filename)
    data["resume_info"] = parsed
    if data.get("code_evidence"):
        data["resume_verification"] = match_resume_to_repository(
            parsed.get("extracted_skills", []),
            data.get("code_evidence", []),
            data.get("rag_evidence", {}),
            data.get("repository_snapshot", {}).get("languages", [])
        )
    repositories.save(data)
    return {
        "status": "success",
        "session_id": session_id,
        "resume_info": parsed,
        "resume_verification": data.get("resume_verification")
    }
