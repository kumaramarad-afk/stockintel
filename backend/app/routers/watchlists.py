from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import db_session
from app.models import Stock, Watchlist, WatchlistItem
from app.schemas.watchlist import WatchlistCreate, WatchlistItemCreate, WatchlistItemRead, WatchlistRead

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def _to_read(watchlist: Watchlist) -> WatchlistRead:
    items = [
        WatchlistItemRead(
            id=item.id,
            stock_id=item.stock_id,
            notes=item.notes,
            added_at=item.added_at,
            ticker=item.stock.ticker if item.stock else None,
            name=item.stock.name if item.stock else None,
        )
        for item in watchlist.items
    ]
    return WatchlistRead(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        created_at=watchlist.created_at,
        items=items,
    )


@router.get("", response_model=list[WatchlistRead])
def list_watchlists(db: Session = Depends(db_session)) -> list[WatchlistRead]:
    watchlists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.items).selectinload(WatchlistItem.stock))
    ).all()
    return [_to_read(watchlist) for watchlist in watchlists]


@router.post("", response_model=WatchlistRead, status_code=201)
def create_watchlist(payload: WatchlistCreate, db: Session = Depends(db_session)) -> WatchlistRead:
    watchlist = Watchlist(**payload.model_dump())
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    watchlist.items = []
    return _to_read(watchlist)


@router.post("/{watchlist_id}/items", response_model=WatchlistRead)
def add_watchlist_item(
    watchlist_id: str,
    payload: WatchlistItemCreate,
    db: Session = Depends(db_session),
) -> WatchlistRead:
    watchlist = db.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.items).selectinload(WatchlistItem.stock))
        .where(Watchlist.id == watchlist_id)
    )
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    stock = db.get(Stock, payload.stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    watchlist.items.append(WatchlistItem(stock_id=payload.stock_id, notes=payload.notes))
    db.commit()
    db.refresh(watchlist)
    return _to_read(watchlist)
