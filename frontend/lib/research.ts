export type SectionState<T> = {
  loading: boolean;
  error: string | null;
  data: T | null;
  available: boolean;
};

export type AccessInfo = {
  tier: "guest" | "free" | "pro" | string;
  entitlement: "public" | "basic" | "full" | "locked" | string;
  reports_used: number;
  reports_limit: number;
  pro: boolean;
  locked_fields: string[];
};

export type ResearchSection<T> = {
  ticker: string;
  available: boolean;
  error: string | null;
  data: T | null;
  access?: AccessInfo | null;
};

export type AnalystAction = {
  name: string | null;
  firm: string | null;
  stars: number | null;
  previous_target: number | string | null;
  new_target: number | string | null;
  direction: "raised" | "lowered" | "unchanged" | string | null;
  days_ago: number | null;
  outlook?: string | null;
  outlook_label?: string | null;
  date?: string | null;
};

export type TopAnalyst = {
  name: string | null;
  firm: string | null;
  stars: number | null;
  accuracy_pct: number | string | null;
  current_target: number | string | null;
  sentiment: string | null;
  days_ago: number | null;
};

export type HeaderData = {
  name: string | null;
  ticker: string;
  price: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  previous_close: number | null;
  change_amount: number | null;
  change_percent: number | null;
  volume?: number | null;
  currency?: string;
  sector?: string | null;
  month_return?: number | null;
  as_of?: string | null;
  composite_score: number | null;
  scores: {
    fundamental: number | null;
    technical: number | null;
    analyst: number | null;
    institutional: number | null;
    sentiment: number | null;
  };
  risk_flags: string[];
  signal_label?: string | null;
  signal_emoji?: string | null;
  signal_tone?: "green" | "amber" | "red" | string | null;
  bullish_count?: number | null;
  neutral_count?: number | null;
  bearish_count?: number | null;
  total_analysts?: number | null;
  average_target?: number | string | null;
  upside_pct?: number | string | null;
  recent_actions?: AnalystAction[];
  top_analysts?: TopAnalyst[];
};

export type AiData = {
  what_the_data_shows?: string;
  why_it_scores: string;
  key_risks: string | string[];
  upcoming_catalysts?: string[];
  summary_preview?: string;
  outlook?: string;
  disclaimer?: string | null;
  options_opportunity: boolean | null;
  implied_move: number | null;
  historical_move: number | null;
};

export type TechnicalsData = {
  price: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  pct_from_52w_high: number | null;
  pct_from_52w_low: number | null;
  volume: number | null;
  volume_avg_30d: number | null;
  volume_vs_avg_pct: number | null;
  ma50: number | null;
  ma200: number | null;
  above_ma50: boolean | null;
  above_ma200: boolean | null;
  cross_alert: "golden_cross" | "death_cross" | null;
  rsi: number | null;
  rsi_label: string | null;
  macd: number | null;
  macd_histogram: number | null;
  macd_signal: string | null;
  bollinger_squeeze: boolean | null;
  support: number | null;
  resistance: number | null;
  pattern: string | null;
};

export type QuarterRevenue = { period: string | null; revenue: number | null; growth_pct: number | null };
export type EpsQuarter = {
  quarter: string | null;
  eps_estimate: number | null;
  eps_actual: number | null;
  beat: boolean | null;
  surprise_pct?: number | null;
};

export type FundamentalsData = {
  revenue_quarters: QuarterRevenue[];
  revenue_acceleration: boolean | null;
  eps_quarters: EpsQuarter[];
  beat_streak: number | null;
  gross_margin: number | null;
  gross_margin_trend: string | null;
  operating_margin: number | null;
  free_cash_flow: number | null;
  free_cash_flow_positive: boolean | null;
  debt_to_equity: number | null;
  return_on_equity: number | null;
  pe_ratio: number | null;
  peg_ratio: number | null;
  price_to_sales: number | null;
  price_to_book: number | null;
  ev_ebitda: number | null;
  sector_pe: number | null;
};

export type AnalystItem = {
  firm: string | null;
  action: string | null;
  from_grade?: string | null;
  to_grade?: string | null;
  date: string | null;
};

export type AnalystsData = {
  consensus: string | null;
  total_analysts: number | null;
  bullish?: number | null;
  neutral?: number | null;
  bearish?: number | null;
  average_target: number | string | null;
  upside_pct: number | string | null;
  high_target: number | string | null;
  low_target: number | string | null;
  upgrades: AnalystItem[];
  downgrades: AnalystItem[];
  recent_actions?: AnalystAction[];
  top_analysts?: TopAnalyst[];
  eps_revisions_trend: string | null;
  top_analyst: { firm: string | null; rating: string | null; date: string | null } | null;
};

export type EarningsRow = {
  quarter: string | null;
  eps_estimate: number | null;
  eps_actual: number | null;
  beat: boolean | null;
  next_day_move: number | null;
};

export type EarningsData = {
  next_earnings_date: string | null;
  days_away: number | null;
  time_of_day: string | null;
  eps_estimate: number | null;
  eps_whisper: number | null;
  revenue_estimate: number | null;
  results: EarningsRow[];
  average_historical_move: number | null;
  implied_move: number | null;
  volatility_underpriced: boolean | null;
};

export type Headline = {
  source: string | null;
  headline: string | null;
  url?: string | null;
  published_at: string | null;
  sentiment: "positive" | "negative" | "neutral";
};

export type SentimentData = {
  overall_score: number | null;
  headlines: Headline[];
  reddit: { mention_count: number; trend: string } | null;
  google_trends: { score: number; direction: string } | null;
  positive_ratio: number | null;
  positive_count: number | null;
  negative_count: number | null;
};

export type InsiderRow = {
  name: string | null;
  title: string | null;
  action: string | null;
  shares: number | string | null;
  value: number | string | null;
  date: string | null;
};

export type HolderRow = {
  holder: string | null;
  shares: number | string | null;
  value: number | string | null;
  pct: number | string | null;
  change: number | string | null;
};

export type CongressRow = {
  politician: string | null;
  action: string | null;
  amount: string | null;
  date: string | null;
};

export type OwnershipData = {
  insider_transactions: InsiderRow[];
  net_insider_sentiment: string | null;
  insider_selling?: boolean;
  institutional_ownership_pct: number | null;
  institutional_ownership_change: number | null;
  new_institutional_additions?: number | null;
  new_institutional_buyers?: number | null;
  top_holders: HolderRow[];
  short_interest_pct: number | null;
  short_interest_trend: string | null;
  days_to_cover: number | null;
  congressional_trades: CongressRow[];
};

export type DividendsData = {
  annual_yield: number | null;
  payout_ratio: number | null;
  growth_rate_5y: number | null;
  next_dividend_date: string | null;
  annual_rate?: number | null;
};

export type SectorData = {
  sector: string | null;
  sector_etf: string | null;
  stock: { "1m": number | null; "3m": number | null; "1y": number | null };
  sector_etf_perf: { "1m": number | null; "3m": number | null; "1y": number | null };
  relative: { "1m": number | null; "3m": number | null; "1y": number | null };
  sector_momentum: "in" | "out" | null;
  sector_rank: number | null;
  peer_count: number | null;
};
