from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.ai import ConfigurationError, QuizGenerationError, generate_questions
from app.models import GenerateQuestionsResponse
from app.pdf_utils import extract_text_from_pdf

router = APIRouter(prefix="/api", tags=["questions"])

MAX_CHARS = 40_000
MAX_PDF_BYTES = 4 * 1024 * 1024


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
        raw = await file.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES:
            raise HTTPException(413, "Choose a PDF smaller than 4 MiB, or paste your notes.")
        try:
            text = await run_in_threadpool(extract_text_from_pdf, raw)
        except Exception:
            raise HTTPException(400, "This PDF could not be read. Try another file or paste your notes.") from None
    else:
        text = (notes or "").strip()
    if not text:
        raise HTTPException(400, "Could not extract any text from the provided input.")
    text = text[:MAX_CHARS]

    try:
        questions = await generate_questions(text, num_questions)
    except ConfigurationError as error:
        raise HTTPException(500, str(error)) from None
    except QuizGenerationError as error:
        raise HTTPException(502, str(error)) from None
    except Exception:
        # Provider errors can contain source text, request details or credentials.
        raise HTTPException(502, "Question generation is unavailable. Please try again or check the server's AI configuration.") from None
    return GenerateQuestionsResponse(questions=questions)
