from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://stockintel:stockintel@localhost:5432/stockintel"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    anthropic_api_key: str = ""
    alpha_vantage_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    finnhub_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "StockIntel/1.0"
    sec_user_agent: str = "StockIntel research@example.com"
    frontend_url: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"
    google_client_id: str = ""
    google_client_secret: str = ""
    apple_client_id: str = ""
    apple_client_secret: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "GetStockReport <alerts@getstockreport.com>"
    monthly_report_limit: int = 5
    pro_price_cents: int = 700

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
