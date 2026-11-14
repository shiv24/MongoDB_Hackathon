from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

from app import config
from app.repo import context, events, lessons, runs, users
from app.repo import scope
from app.session import current

router = APIRouter(prefix="/projects")


class SourceIn(BaseModel):
    title: str
    text: str
    kind: str = "spec"


class DecisionIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator('text')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Write a nonempty project rule')
        return value.strip()


@router.get("")
def list_projects(request: Request):
    return users.projects_for(current(request))


@router.get("/{project_id}/context")
def get_context(request: Request, project_id: str):
    s = current(request)
    return {
        "sources": context.list_sources(s, project_id),
        "decisions": context.list_decisions(s, project_id, include_superseded=True),
        "lessons": lessons.list_for(s, project_id),
        "runs": runs.recent(s, project_id),
    }


@router.post("/{project_id}/sources")
def add_source(request: Request, project_id: str, body: SourceIn):
    return context.add_source(current(request), project_id, body.title, body.text, body.kind)


@router.post("/{project_id}/sources/file")
async def add_source_file(request: Request, project_id: str, file: UploadFile = File(...),
                          title: str = Form(""), text: str = Form("")):
    session = current(request)
    scope.require_project(session, project_id)
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    is_pdf = file.content_type in {"application/pdf", "application/x-pdf"} or suffix == ".pdf"
    is_text = (file.content_type or "").startswith("text/") or suffix == ".txt"
    if not (is_pdf or is_text):
        raise ValueError("upload a PDF or text file")

    raw = await file.read(config.MAX_SOURCE_FILE_BYTES + 1)
    if len(raw) > config.MAX_SOURCE_FILE_BYTES:
        raise ValueError("file is larger than the 10 MB limit")

    if is_pdf:
        if not raw.startswith(b"%PDF-"):
            raise ValueError("the uploaded file is not a valid PDF")
        try:
            reader = PdfReader(BytesIO(raw))
            if reader.is_encrypted:
                raise ValueError("password-protected PDFs are not supported")
            if len(reader.pages) > config.MAX_PDF_PAGES:
                raise ValueError(f"PDF has more than {config.MAX_PDF_PAGES} pages")
            file_text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("the PDF could not be read") from exc
        kind = "pdf"
    else:
        try:
            file_text = raw.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise ValueError("text files must use UTF-8 encoding") from exc
        kind = "text"

    source_text = "\n\n".join(part for part in (text.strip(), file_text) if part)
    if not source_text:
        raise ValueError("the file contains no extractable text")
    source_title = title.strip() or Path(filename).stem.strip() or "Uploaded source"
    return context.add_source(session, project_id, source_title, source_text, kind)


@router.post("/{project_id}/decisions")
def add_decision(request: Request, project_id: str, body: DecisionIn):
    return context.add_decision(current(request), project_id, body.text)


@router.post("/decisions/{decision_id}/supersede")
def supersede_decision(request: Request, decision_id: str, body: DecisionIn):
    return context.supersede_decision(current(request), decision_id, body.text)


@router.get("/decisions/{decision_id}/history")
def decision_history(request: Request, decision_id: str):
    s = current(request)
    context.get_decision(s, decision_id)
    return events.history(s["team_id"], decision_id)
