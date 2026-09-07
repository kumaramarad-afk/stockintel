-- Entity: stocks, price_snapshots
-- Coverage universe and latest/historical market snapshots.

CREATE TABLE IF NOT EXISTS stocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(32),
    sector VARCHAR(128),
    industry VARCHAR(128),
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    price NUMERIC(18, 4) NOT NULL,
    change_percent NUMERIC(8, 4),
    volume BIGINT,
    market_cap BIGINT,
    as_of TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
