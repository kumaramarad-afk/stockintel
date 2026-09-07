from pathlib import Path

from app.config import settings


def _file_key(*relative: str) -> str:
    root = Path(__file__).resolve().parents[2]
    for name in relative:
        path = root / name
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return ""


def anthropic_key() -> str:
    return settings.anthropic_api_key.strip() or _file_key("API Key.txt")


def alpha_vantage_key() -> str:
    return settings.alpha_vantage_api_key.strip()


def finnhub_key() -> str:
    return settings.finnhub_api_key.strip()


def sec_user_agent() -> str:
    return settings.sec_user_agent.strip() or "StockIntel research@example.com"


def reddit_user_agent() -> str:
    return settings.reddit_user_agent.strip() or "StockIntel/1.0"
