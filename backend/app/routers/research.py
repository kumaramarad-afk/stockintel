import logging
import re

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.deps import db_session, optional_user
from app.models import ResearchNote, Stock, User
from app.schemas.research import (
    CachedTickerItem,
    CachedTickerListResponse,
    ResearchGenerateRequest,
    ResearchGenerateResponse,
    ResearchNoteCreate,
    ResearchNoteRead,
    ResearchSectionResponse,
    ReasoningReportResponse,
)
from services.alerts import notify_from_report
from services.paywall import apply_paywall, resolve_access
from services.report_cache import (
    POPULAR_TICKERS,
    list_cached_tickers,
    public_report_payload,
    refresh_popular_reports,
)
from services.symbol_search import search_us_symbols
from services.ticker_catalog import display_name, resolve_query_to_ticker
from services.stock_service import (
    SECTION_HANDLERS,
    MissingApiKeyError,
    ResearchGenerationError,
    TickerNotFoundError,
    generate_section,
    generate_stock_research,
)

router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger(__name__)
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


@router.get("/tickers", response_model=CachedTickerListResponse)
def research_ticker_directory(db: Session = Depends(db_session)) -> CachedTickerListResponse:
    rows = list_cached_tickers(db)
    return CachedTickerListResponse(
        count=len(rows),
        tickers=[CachedTickerItem.model_validate(row) for row in rows],
    )


@router.get("/search", response_model=CachedTickerListResponse)
def research_ticker_search(q: str = Query("", max_length=64), db: Session = Depends(db_session)) -> CachedTickerListResponse:
    """Search popular + live US tickers by symbol or company name."""
    directory = {row["ticker"]: row for row in list_cached_tickers(db)}
    matches = search_us_symbols(q, limit=12)
    rows = []
    for match in matches:
        cached = directory.get(match["ticker"], {})
        rows.append(
            {
                "ticker": match["ticker"],
                "name": cached.get("name") or match.get("company_name") or match.get("name"),
                "one_line": cached.get("one_line"),
                "price": cached.get("price"),
                "as_of": cached.get("as_of"),
                "generated_at": cached.get("generated_at"),
            }
        )
    return CachedTickerListResponse(count=len(rows), tickers=[CachedTickerItem.model_validate(row) for row in rows])


@router.get("/resolve")
def research_resolve_query(q: str = Query(..., min_length=1, max_length=64)) -> dict[str, str | None]:
    """Resolve a ticker or company name to a canonical symbol for navigation."""
    symbol = resolve_query_to_ticker(q)
    if not symbol:
        hits = search_us_symbols(q, limit=1)
        symbol = hits[0]["ticker"] if hits else None
    if symbol:
        name = display_name(symbol)
        if not name:
            hits = search_us_symbols(symbol, limit=1)
            name = hits[0].get("company_name") if hits else None
        return {"ticker": symbol, "name": name}
    # Allow raw ticker navigation for symbols outside the catalog.
    candidate = q.strip().upper()
    if TICKER_RE.fullmatch(candidate):
        return {"ticker": candidate, "name": display_name(candidate)}
    raise HTTPException(status_code=404, detail="No matching ticker or company name")


@router.get("/public/{ticker}", response_model=ReasoningReportResponse)
def research_public_report(
    ticker: str,
    db: Session = Depends(db_session),
    user: User | None = Depends(optional_user),
) -> ReasoningReportResponse:
    symbol = _normalize_ticker(ticker)
    try:
        payload = public_report_payload(db, symbol, user)
    except TickerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingApiKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Public research report failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Failed to load research report.") from exc
    # Public pages do not consume monthly report quota — day-gating controls depth.
    access = resolve_access(user, symbol, db, consume=False)
    payload["access"] = access
    return ReasoningReportResponse.model_validate(payload)


@router.post("/admin/refresh-cache")
def refresh_report_cache(
    api_key: str | None = Query(default=None),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    limit: int | None = Query(default=None, ge=1, le=50),
) -> dict:
    expected = settings.internal_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="Internal API key is not configured")
    provided = api_key or x_internal_key
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    symbols = POPULAR_TICKERS[:limit] if limit else POPULAR_TICKERS
    return refresh_popular_reports(symbols)


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


@router.get("/report-new/{ticker}", response_model=ReasoningReportResponse)
def research_reasoning_report(
    ticker: str,
    db: Session = Depends(db_session),
    user: User | None = Depends(optional_user),
) -> ReasoningReportResponse:
    """Alias for the public reasoning report (cache-backed)."""
    return research_public_report(ticker, db, user)


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
