// web never touches SQLite; the engine owns the data (design D1)
const ENGINE_URL = process.env.ENGINE_URL ?? "http://127.0.0.1:8000";

export class EngineError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

export async function engine<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${ENGINE_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new EngineError(`ต่อ engine ที่ ${ENGINE_URL} ไม่ได้ (ลืมรัน engine หรือเปล่า)`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new EngineError(body.detail ?? `engine ตอบ ${res.status}`, res.status);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export type Run = {
  id: number;
  status: "running" | "succeeded" | "failed";
  started_at: string;
  finished_at: string | null;
  price_date: string | null;
  total: number | null;
  succeeded: number | null;
  failed: number | null;
  error: string | null;
};

export type CdcState = "bear-far" | "bear-approaching" | "just-crossed" | "bull";

export type Check = {
  name: string;
  passed: boolean | null;
  value: number | null;
  threshold: string;
  reason: string;
};

export type FairValueItem = {
  method: string;
  label: string;
  fair_value: number | null;
  mos: number | null;
  reason: string | null;
};

export type FairValueSummary = {
  label: string;
  undervalued: number;
  computed: number;
  min_mos: number | null;
  median_mos: number | null;
  max_mos: number | null;
  median_fair_value: number | null;
  max_fair_value: number | null;
};

export type Evaluation = {
  symbol: string;
  name: string;
  sector: string;
  market: string;
  price: number;
  price_date: string;
  candidate_rank: number | null;
  liquidity: { passed: boolean; value: number; threshold: number; reason: string };
  quality: { passed: boolean; checks: Check[]; inflection: { flag: boolean; reason: string | null } } | null;
  fair_value: {
    price: number;
    eps_ttm: number | null;
    items: FairValueItem[];
    summary: FairValueSummary;
    structure_change: { flag: boolean; reason: string | null };
    // absent in runs saved before market caps came from yfinance
    history_gap?: { flag: boolean; reason: string | null };
  } | null;
  cdc: {
    state: CdcState | null;
    fast?: number;
    slow?: number;
    gap_pct?: number;
    speed?: number;
    eta_days?: number | null;
    days_since_cross?: number | null;
    reason: string | null;
  };
  risk_reward: {
    entry: number;
    stop: number;
    target: number | null;
    target_optimistic: number | null;
    rrr: number | null;
    low_rrr: boolean;
    upside: number | null;
    hold_months: number;
    reward_per_month: number | null;
    reason: string | null;
  } | null;
  inclusion: { included: boolean; reasons: string[] };
};

export type StockInfo = { symbol: string; name: string; sector: string; market: string };

export type CalendarEvent = {
  id?: number;
  date: string;
  label: string;
  kind: "statement" | "index_review" | "manual";
  estimated: boolean;
};

export type StockDetail = {
  stock: StockInfo;
  run: Run | null;
  evaluation: Evaluation | null;
  failure: string | null;
  hints: { sector_matched: boolean; items: string[] };
  events: CalendarEvent[];
};

export type Failure = { symbol: string; name: string | null; reason: string };
