-- Entity: research_notes
-- Stock-linked research reports with rating and target price.

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
