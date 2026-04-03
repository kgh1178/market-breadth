export interface MarketStatusPayload {
  status: "ok" | "partial" | "error";
  as_of_date: string | null;
  series_valid: boolean;
  metrics_valid: boolean;
  price_basis: string;
  error_code: string | null;
  error_message: string | null;
}

export interface LatestPayload {
  date: string;
  pipeline_date: string;
  sp500: MarketStatusPayload & Record<string, unknown>;
  nikkei225: MarketStatusPayload & Record<string, unknown>;
  kospi200: MarketStatusPayload & Record<string, unknown>;
}

export interface SignalPayload {
  valid: boolean;
  required_markets: string[];
  missing_markets: string[];
  invalid_reason: string | null;
  signal?: string;
  state?: string;
}

export interface SignalsEnvelope {
  partial_data: boolean;
  signals: Record<string, SignalPayload>;
}
