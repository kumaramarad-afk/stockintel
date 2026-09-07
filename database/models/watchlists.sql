-- Entity: watchlists, watchlist_items
-- Per-user coverage lists used by the research desk.

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
