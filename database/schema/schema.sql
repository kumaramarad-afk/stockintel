-- StockIntel canonical PostgreSQL schema

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    notes TEXT,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (watchlist_id, stock_id)
);

CREATE TABLE IF NOT EXISTS research_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID REFERENCES stocks(id) ON DELETE SET NULL,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    body TEXT NOT NULL,
    rating VARCHAR(16),
    target_price NUMERIC(18, 4),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletter_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(128) NOT NULL,
    excerpt TEXT,
    body TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    ticker VARCHAR(16),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (newsletter_id, slug)
);

CREATE TABLE IF NOT EXISTS newsletter_picks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pick_date DATE NOT NULL UNIQUE,
    ticker VARCHAR(16) NOT NULL,
    reason TEXT NOT NULL,
    analyst_upgrades INTEGER NOT NULL DEFAULT 0,
    institutional_buying DOUBLE PRECISION NOT NULL DEFAULT 0,
    sentiment VARCHAR(50) NOT NULL DEFAULT 'bullish',
    issue_id UUID REFERENCES newsletter_issues(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletter_sends (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pick_id UUID NOT NULL REFERENCES newsletter_picks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    click_url VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS subscribers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    is_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
    subscriber_id UUID NOT NULL REFERENCES subscribers(id) ON DELETE CASCADE,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (newsletter_id, subscriber_id)
);

CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks (ticker);
CREATE INDEX IF NOT EXISTS idx_stocks_name_trgm ON stocks USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_price_stock_asof ON price_snapshots (stock_id, as_of DESC);
CREATE INDEX IF NOT EXISTS idx_research_stock ON research_notes (stock_id);
CREATE INDEX IF NOT EXISTS idx_research_published ON research_notes (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists (user_id);
CREATE INDEX IF NOT EXISTS idx_issues_newsletter ON newsletter_issues (newsletter_id);
CREATE INDEX IF NOT EXISTS idx_newsletter_picks_date ON newsletter_picks (pick_date DESC);
CREATE INDEX IF NOT EXISTS idx_newsletter_sends_user ON newsletter_sends (user_id);
CREATE TABLE IF NOT EXISTS plan_exceptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    plan VARCHAR(32) NOT NULL DEFAULT 'premium',
    note VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers (email);
CREATE INDEX IF NOT EXISTS idx_plan_exceptions_email ON plan_exceptions (email);
