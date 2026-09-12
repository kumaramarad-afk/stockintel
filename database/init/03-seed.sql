-- Demo data for local development. Safe to re-run only on a fresh database.

INSERT INTO users (id, email, full_name, hashed_password, is_admin)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'analyst@stockintel.local', 'Lead Analyst', 'placeholder-hash', TRUE)
ON CONFLICT (email) DO NOTHING;

INSERT INTO stocks (id, ticker, name, exchange, sector, industry, description)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'AAPL', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics', 'Designs and sells consumer electronics, software, and services.'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'MSFT', 'Microsoft Corporation', 'NASDAQ', 'Technology', 'Software', 'Cloud, productivity software, and AI platform company.'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'NVDA', 'NVIDIA Corporation', 'NASDAQ', 'Technology', 'Semiconductors', 'GPUs and accelerated computing platforms.'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'AMZN', 'Amazon.com, Inc.', 'NASDAQ', 'Consumer Discretionary', 'Internet Retail', 'E-commerce, AWS, and advertising.'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'GOOGL', 'Alphabet Inc.', 'NASDAQ', 'Communication Services', 'Internet Content', 'Search, YouTube, cloud, and advertising.')
ON CONFLICT (ticker) DO NOTHING;

INSERT INTO price_snapshots (stock_id, price, change_percent, volume, market_cap)
SELECT id, 227.50, 0.84, 48200000, 3450000000000 FROM stocks WHERE ticker = 'AAPL'
UNION ALL
SELECT id, 428.10, 1.12, 22100000, 3180000000000 FROM stocks WHERE ticker = 'MSFT'
UNION ALL
SELECT id, 119.40, -0.65, 315000000, 2920000000000 FROM stocks WHERE ticker = 'NVDA'
UNION ALL
SELECT id, 186.20, 0.31, 38400000, 1960000000000 FROM stocks WHERE ticker = 'AMZN'
UNION ALL
SELECT id, 164.80, -0.22, 19800000, 2030000000000 FROM stocks WHERE ticker = 'GOOGL';

INSERT INTO newsletters (id, name, slug, description)
VALUES
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1', 'StockIntel Weekly', 'weekly', 'Concise market, research, and earnings briefing.')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO newsletter_issues (newsletter_id, title, slug, excerpt, body, published_at, ticker)
SELECT id,
  'AI capex and the next earnings season',
  'ai-capex-earnings',
  'What mega-cap spend signals for semiconductors, cloud, and software multiples.',
  'This week we map AI infrastructure spend against earnings quality, balance-sheet flexibility, and valuation support across the coverage universe.',
  NOW() - INTERVAL '3 days',
  'NVDA'
FROM newsletters WHERE slug = 'weekly'
ON CONFLICT (newsletter_id, slug) DO NOTHING;

INSERT INTO newsletter_picks (pick_date, ticker, reason, analyst_upgrades, institutional_buying, sentiment)
VALUES (
  CURRENT_DATE,
  'NVDA',
  'Coverage revisions and institutional flow concentrated on the accelerator franchise this session.',
  3,
  84.2,
  'bullish'
)
ON CONFLICT (pick_date) DO NOTHING;

INSERT INTO research_notes (stock_id, author_id, title, summary, body, rating, target_price, published_at)
SELECT s.id,
  '11111111-1111-1111-1111-111111111111',
  'NVIDIA: inference demand vs. supply digestion',
  'Near-term digestion risk, longer-term platform flywheel intact.',
  'We remain constructive on NVIDIA''s data-center franchise. The debate is timing: hyperscaler capex conversion, networking attach, and software pull-through versus a pause in accelerator shipments.',
  'buy',
  145.00,
  NOW() - INTERVAL '1 day'
FROM stocks s WHERE s.ticker = 'NVDA';

INSERT INTO watchlists (id, user_id, name)
VALUES
  ('cccccccc-cccc-cccc-cccc-ccccccccccc1', '11111111-1111-1111-1111-111111111111', 'Core Coverage')
ON CONFLICT DO NOTHING;

INSERT INTO watchlist_items (watchlist_id, stock_id)
SELECT 'cccccccc-cccc-cccc-cccc-ccccccccccc1', id FROM stocks WHERE ticker IN ('AAPL', 'MSFT', 'NVDA')
ON CONFLICT (watchlist_id, stock_id) DO NOTHING;
