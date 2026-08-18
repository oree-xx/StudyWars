from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.ai import generate_questions
from app.models import GenerateQuestionsResponse
from app.pdf_utils import extract_text_from_pdf

router = APIRouter(prefix="/api", tags=["questions"])

MAX_CHARS = 40_000  # keep the prompt bounded for very long documents


@router.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions_endpoint(
    file: Optional[UploadFile] = File(None),
    notes: Optional[str] = Form(None),
    num_questions: int = Form(5),
):
    if not file and not notes:
        raise HTTPException(400, "Provide either a PDF file or notes text.")

    if not (1 <= num_questions <= 20):
        raise HTTPException(400, "num_questions must be between 1 and 20.")

    if file:
        if file.content_type != "application/pdf":
            raise HTTPException(400, "Only PDF files are supported for upload.")
        raw = await file.read()
        text = extract_text_from_pdf(raw)
    else:
        text = (notes or "").strip()

    if not text:
        raise HTTPException(400, "Could not extract any text from the provided input.")

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    try:
        questions = generate_questions(text, num_questions)
    except RuntimeError as e:
        # Missing API key etc. — a config problem, not the caller's fault.
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(502, f"AI question generation failed: {e}")

    return GenerateQuestionsResponse(questions=questions)
