from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import db_session
from app.models import Stock
from app.schemas.stock import StockCreate, StockRead

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _to_read(stock: Stock) -> StockRead:
    latest = None
    if stock.prices:
        latest = max(stock.prices, key=lambda snapshot: snapshot.as_of)
    payload = StockRead.model_validate(stock)
    payload.latest_price = latest
    return payload


@router.get("", response_model=list[StockRead])
def list_stocks(db: Session = Depends(db_session)) -> list[StockRead]:
    stocks = db.scalars(select(Stock).options(selectinload(Stock.prices)).order_by(Stock.ticker)).all()
    return [_to_read(stock) for stock in stocks]


@router.get("/{ticker}", response_model=StockRead)
def get_stock(ticker: str, db: Session = Depends(db_session)) -> StockRead:
    stock = db.scalar(
        select(Stock).options(selectinload(Stock.prices)).where(Stock.ticker == ticker.upper())
    )
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return _to_read(stock)


@router.post("", response_model=StockRead, status_code=201)
def create_stock(payload: StockCreate, db: Session = Depends(db_session)) -> StockRead:
    ticker = payload.ticker.upper()
    existing = db.scalar(select(Stock).where(Stock.ticker == ticker))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ticker already exists")

    data = payload.model_dump()
    data["ticker"] = ticker
    stock = Stock(**data)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    stock.prices = []
    return _to_read(stock)
