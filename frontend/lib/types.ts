export type PriceSnapshot = {
  id: string;
  price: string;
  change_percent: string | null;
  volume: number | null;
  market_cap: number | null;
  as_of: string;
};

export type Stock = {
  id: string;
  ticker: string;
  name: string;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  currency: string;
  description: string | null;
  latest_price: PriceSnapshot | null;
};

export type ResearchNote = {
  id: string;
  stock_id: string | null;
  author_id: string;
  title: string;
  summary: string | null;
  body: string;
  rating: string | null;
  target_price: string | null;
  published_at: string | null;
  created_at: string;
  ticker: string | null;
};

export type Newsletter = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
};

export type NewsletterIssue = {
  id: string;
  newsletter_id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  body: string;
  published_at: string | null;
  created_at: string;
  ticker?: string | null;
};

export type NewsletterStatus = {
  tier: string;
  status: string;
  newsletter_enabled: boolean;
  subscribed_at: string | null;
  newsletter_emails_received: number;
  email_preference: string;
};

export type NewsletterArchiveItem = {
  date: string;
  ticker: string;
  reason: string;
  sentiment: string;
  issue_id: string | null;
  research_path: string;
};

export type NewsletterToday = {
  date: string | null;
  ticker: string | null;
  reason: string | null;
  sentiment: string | null;
  research_path: string | null;
  issue_id: string | null;
  full_access: boolean;
  movers: Array<{
    ticker?: string;
    change_percent?: number;
    headline?: string;
  }>;
  earnings: Array<{
    date?: string;
    ticker?: string;
    eps_estimate?: number | null;
    eps_actual?: number | null;
  }>;
  macro: Record<string, unknown>;
  html: string | null;
};

export type WatchlistItem = {
  id: string;
  stock_id: string;
  notes: string | null;
  added_at: string;
  ticker: string | null;
  name: string | null;
};

export type Watchlist = {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  items: WatchlistItem[];
};

export type PlatformStats = {
  stocks: number;
  research_notes: number;
  newsletter_issues: number;
  subscribers: number;
};

export type CurrentPriceData = {
  price: number | null;
  change_percent: number | null;
  currency: string;
  previous_close: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  as_of: string | null;
};

export type AnalystRatingsData = {
  consensus: string | null;
  target_mean: number | null;
  target_high: number | null;
  target_low: number | null;
  number_of_analysts: number | null;
  distribution: Record<string, number> | null;
};

export type BasicFinancialsData = {
  pe_ratio: number | null;
  market_cap: number | null;
  revenue: number | null;
  eps: number | null;
  profit_margin: number | null;
  source: string | null;
};

export type StockResearchReport = {
  ticker: string;
  name: string | null;
  current_price: CurrentPriceData;
  analyst_ratings: AnalystRatingsData;
  financials: BasicFinancialsData;
  report: string;
};
