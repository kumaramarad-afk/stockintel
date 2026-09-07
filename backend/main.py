from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import ensure_user_schema
from app.routers import auth_oauth, checkout, health, newsletters, research, stocks, users, watchlists, webhooks

ensure_user_schema()

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
app.include_router(stocks.router, prefix=api_prefix)
app.include_router(research.router, prefix=api_prefix)
app.include_router(newsletters.router, prefix=api_prefix)
app.include_router(watchlists.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(auth_oauth.router, prefix=api_prefix)
app.include_router(checkout.router)
app.include_router(webhooks.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_user_schema()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "getstockreport", "docs": "/docs"}
