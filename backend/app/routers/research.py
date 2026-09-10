import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import db_session, optional_user
from app.models import ResearchNote, Stock, User
from app.schemas.research import (
    ResearchGenerateRequest,
    ResearchGenerateResponse,
    ResearchNoteCreate,
    ResearchNoteRead,
    ResearchSectionResponse,
)
from services.alerts import notify_from_report
from services.paywall import apply_paywall, resolve_access
from services.stock_service import (
    SECTION_HANDLERS,
    MissingApiKeyError,
    ResearchGenerationError,
    TickerNotFoundError,
    generate_section,
    generate_stock_research,
)

router = APIRouter(prefix="/research", tags=["research"])
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,15}$")


def _to_read(note: ResearchNote) -> ResearchNoteRead:
    payload = ResearchNoteRead.model_validate(note)
    payload.ticker = note.stock.ticker if note.stock else None
    return payload


def _normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not TICKER_RE.fullmatch(symbol):
        raise HTTPException(status_code=422, detail="Enter a valid ticker symbol, such as AAPL or BRK.B")
    return symbol


@router.get("", response_model=list[ResearchNoteRead])
def list_research(db: Session = Depends(db_session)) -> list[ResearchNoteRead]:
    notes = db.scalars(
        select(ResearchNote).options(selectinload(ResearchNote.stock)).order_by(ResearchNote.created_at.desc())
    ).all()
    return [_to_read(note) for note in notes]


@router.post("/generate", response_model=ResearchGenerateResponse)
def generate_research(
    payload: ResearchGenerateRequest,
    db: Session = Depends(db_session),
    user: User | None = Depends(optional_user),
) -> ResearchGenerateResponse:
    symbol = _normalize_ticker(payload.ticker)
    try:
        result = generate_stock_research(symbol)
    except TickerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingApiKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to generate stock research.") from exc
    if user is not None:
        resolve_access(user, symbol, db, consume=True)
    return ResearchGenerateResponse.model_validate(result)


@router.get("/report/{ticker}/{section}", response_model=ResearchSectionResponse)
def research_report_section(
    ticker: str,
    section: str,
    db: Session = Depends(db_session),
    user: User | None = Depends(optional_user),
) -> ResearchSectionResponse:
    symbol = _normalize_ticker(ticker)
    name = section.strip().lower()
    if name not in SECTION_HANDLERS:
        raise HTTPException(status_code=404, detail="Unknown research section")
    try:
        result = dict(generate_section(symbol, name))
    except TickerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raw = result.get("data")
    ready = bool(result.get("available") and raw)
    access = resolve_access(user, symbol, db, consume=ready)
    if ready:
        try:
            notify_from_report(db, symbol, name, raw)
        except Exception:
            pass
        result["data"] = apply_paywall(name, raw, access["entitlement"])
    result["access"] = access
    return ResearchSectionResponse.model_validate(result)


@router.get("/{note_id}", response_model=ResearchNoteRead)
def get_research(note_id: str, db: Session = Depends(db_session)) -> ResearchNoteRead:
    note = db.scalar(
        select(ResearchNote).options(selectinload(ResearchNote.stock)).where(ResearchNote.id == note_id)
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Research note not found")
    return _to_read(note)


@router.post("", response_model=ResearchNoteRead, status_code=201)
def create_research(payload: ResearchNoteCreate, db: Session = Depends(db_session)) -> ResearchNoteRead:
    if payload.stock_id is not None:
        stock = db.get(Stock, payload.stock_id)
        if stock is None:
            raise HTTPException(status_code=404, detail="Stock not found")

    note = ResearchNote(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    db.refresh(note, attribute_names=["stock"])
    return _to_read(note)
