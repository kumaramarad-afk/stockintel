-- Entity: newsletters, newsletter_issues, subscribers, newsletter_subscriptions

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (newsletter_id, slug)
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
