from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import ensure_user_schema
from app.routers import (
    auth_oauth,
    checkout,
    contact,
    health,
    markets,
    newsletter,
    newsletters,
    plan_exceptions,
    research,
    search,
    stocks,
    users,
    watchlists,
    webhooks,
)
from app.scheduled_tasks import start_scheduler, stop_scheduler
from services.stock_seed import upsert_company_names

ensure_user_schema()
try:
    upsert_company_names()
except Exception:
    # DB may be unavailable in some local/test contexts.
    pass

app = FastAPI(
    title="GetStockReport API",
    description="Institutional-grade stock research API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(health.router, prefix=api_prefix)
app.include_router(search.router, prefix=api_prefix)
app.include_router(stocks.router, prefix=api_prefix)
app.include_router(research.router, prefix=api_prefix)
app.include_router(markets.router, prefix=api_prefix)
app.include_router(newsletters.router, prefix=api_prefix)
app.include_router(newsletter.router, prefix=api_prefix)
app.include_router(plan_exceptions.router, prefix=api_prefix)
app.include_router(contact.router, prefix=api_prefix)
app.include_router(watchlists.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(auth_oauth.router, prefix=api_prefix)
app.include_router(checkout.router)
app.include_router(webhooks.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_user_schema()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "getstockreport", "docs": "/docs"}
