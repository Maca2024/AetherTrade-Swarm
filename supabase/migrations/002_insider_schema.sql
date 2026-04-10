-- AetherTrade-Swarm — Insider Trading Schema
-- Migration 002: SEC EDGAR Form 4 insider trade pipeline
-- Supabase project: sooufmgxxuirbsxouxju (EU-West, Ireland)
--
-- Run after: 001_initial_schema.sql
-- Applied:   2026-04-08
--
-- Tables:
--   insider_trades                 — raw Form 4 transaction records
--   insider_clusters               — detected cluster buy events
--   insider_backtests              — historical backtest result summaries
--   insider_webhook_subscriptions  — pro-tier real-time alert subscriptions

-- ============================================================================
-- ENUMS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE insider_transaction_code AS ENUM (
        'P',  -- Open market purchase (primary bullish signal)
        'S',  -- Open market sale
        'A',  -- Grant/award (compensation, less informative)
        'D',  -- Return/disposition
        'F',  -- Tax withholding on vested shares
        'G',  -- Gift
        'M',  -- Option exercise
        'C',  -- Conversion of derivative security
        'E',  -- Expiration of short derivative
        'H',  -- Expiration of long derivative
        'I',  -- Discretionary transaction in 10b5-1 plan
        'J',  -- Other acquisition or disposition
        'K',  -- Equity swap
        'L',  -- Small acquisition (Rule 16a-6)
        'O',  -- Exercise of out-of-the-money option
        'U',  -- Tender offer disposition
        'W',  -- Acquisition by will or laws of descent
        'X',  -- Exercise of in-the-money option
        'Z'   -- Voting trust deposit/withdrawal
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- insider_trades
-- ============================================================================
-- Stores one row per non-derivative transaction parsed from a Form 4 filing.
-- Natural deduplication key: (form4_url, insider_name, transaction_date, transaction_code)
-- because a single Form 4 filing may contain multiple transactions.

CREATE TABLE IF NOT EXISTS insider_trades (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Company identifiers (from Form 4 <issuer> element)
    cik                 TEXT            NOT NULL,
    ticker              TEXT            NOT NULL,
    company_name        TEXT            NOT NULL,

    -- Insider information (from Form 4 <reportingOwner> element)
    insider_name        TEXT            NOT NULL,
    insider_title       TEXT            NOT NULL DEFAULT '',

    -- Transaction details (from <nonDerivativeTransaction> element)
    transaction_date    DATE            NOT NULL,
    transaction_code    TEXT            NOT NULL,           -- P, S, A, D, F, G, M, C, …
    shares              DOUBLE PRECISION NOT NULL,          -- positive = acquired, negative = disposed
    price_per_share     DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_value         DOUBLE PRECISION NOT NULL DEFAULT 0, -- ABS(shares) * price_per_share
    shares_owned_after  DOUBLE PRECISION NOT NULL DEFAULT 0, -- post-transaction holding

    -- Filing provenance
    filing_timestamp    TIMESTAMPTZ     NOT NULL,
    form4_url           TEXT            NOT NULL,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Deduplication: one row per (filing, insider, transaction date, code).
    -- A single Form 4 can have multiple rows if the insider made multiple trades.
    CONSTRAINT uq_insider_trade
        UNIQUE (form4_url, insider_name, transaction_date, transaction_code)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_insider_trades_ticker
    ON insider_trades (ticker);

CREATE INDEX IF NOT EXISTS idx_insider_trades_transaction_date
    ON insider_trades (transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_insider_trades_ticker_date
    ON insider_trades (ticker, transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_insider_trades_code_date
    ON insider_trades (transaction_code, transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_insider_trades_cik
    ON insider_trades (cik);

CREATE INDEX IF NOT EXISTS idx_insider_trades_filing_timestamp
    ON insider_trades (filing_timestamp DESC);

-- ============================================================================
-- insider_clusters
-- ============================================================================
-- Each row represents a cluster buy event: 3+ unique insiders buying
-- the same company within a 10-day rolling window (open-market purchases only).
-- trades_json stores constituent trade IDs and insider names as JSONB for
-- efficient retrieval without a separate join table.

CREATE TABLE IF NOT EXISTS insider_clusters (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Company
    ticker              TEXT            NOT NULL,
    cik                 TEXT            NOT NULL,
    company_name        TEXT            NOT NULL,

    -- Cluster window (inclusive)
    window_start        DATE            NOT NULL,
    window_end          DATE            NOT NULL,

    -- Aggregate metrics across all trades in window
    insider_count       INT             NOT NULL CHECK (insider_count >= 2),
    total_value         DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_price           DOUBLE PRECISION NOT NULL DEFAULT 0,

    -- Signal quality score: 0-100
    -- Scoring: base 40 + 10/extra insider + 15 CEO/CFO + 10 trade>100K + 5 multi-director
    cluster_strength    INT             NOT NULL DEFAULT 0
                            CHECK (cluster_strength BETWEEN 0 AND 100),

    -- Constituent trade references stored as JSONB:
    -- { "trade_ids": [1, 2, 3], "insider_names": ["John Doe", "Jane Smith"] }
    trades_json         JSONB           NOT NULL DEFAULT '{}',

    detected_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Prevent duplicate cluster records for same company/window
    CONSTRAINT uq_insider_cluster
        UNIQUE (ticker, window_start, window_end)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_insider_clusters_ticker
    ON insider_clusters (ticker);

CREATE INDEX IF NOT EXISTS idx_insider_clusters_strength
    ON insider_clusters (cluster_strength DESC);

CREATE INDEX IF NOT EXISTS idx_insider_clusters_detected_at
    ON insider_clusters (detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_insider_clusters_window_start
    ON insider_clusters (window_start DESC);

CREATE INDEX IF NOT EXISTS idx_insider_clusters_ticker_strength
    ON insider_clusters (ticker, cluster_strength DESC);

-- GIN index on trades_json for efficient insider name lookup
CREATE INDEX IF NOT EXISTS idx_insider_clusters_trades_json
    ON insider_clusters USING gin(trades_json);

-- ============================================================================
-- insider_backtests
-- ============================================================================
-- Stores summary statistics from each historical backtest run.
-- Each run produces 3 rows: one per hold period (60, 90, 180 days).

CREATE TABLE IF NOT EXISTS insider_backtests (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_date            TIMESTAMPTZ     NOT NULL,
    period_days         INT             NOT NULL,       -- 60, 90, or 180

    -- Return statistics
    total_return        DOUBLE PRECISION NOT NULL,      -- cumulative portfolio return, e.g. 0.45 = +45%
    sharpe_ratio        DOUBLE PRECISION NOT NULL,      -- annualised Sharpe
    win_rate            DOUBLE PRECISION NOT NULL,      -- fraction 0.0-1.0
    max_drawdown        DOUBLE PRECISION NOT NULL,      -- negative, e.g. -0.18 = -18%
    alpha_vs_spy        DOUBLE PRECISION NOT NULL,      -- mean per-trade alpha vs SPY

    -- Metadata
    trade_count         INT             NOT NULL DEFAULT 0,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insider_backtests_period
    ON insider_backtests (period_days, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_insider_backtests_run_date
    ON insider_backtests (run_date DESC);

-- ============================================================================
-- insider_webhook_subscriptions
-- ============================================================================
-- Pro/Enterprise tier real-time cluster alert subscriptions.
-- When a cluster with strength >= min_strength is detected, a POST is
-- delivered to the subscriber's URL with a ClusterOut JSON payload.

CREATE TABLE IF NOT EXISTS insider_webhook_subscriptions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscription_id     UUID            NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    owner_email         TEXT            NOT NULL,
    key_id              TEXT            NOT NULL,       -- references api_keys.key_id (text FK)
    url                 TEXT            NOT NULL,
    min_strength        INT             NOT NULL DEFAULT 60
                            CHECK (min_strength BETWEEN 40 AND 100),

    -- Optional ticker watchlist — NULL means subscribe to all tickers
    tickers             TEXT[]          DEFAULT NULL,

    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_triggered_at   TIMESTAMPTZ     DEFAULT NULL,
    trigger_count       INT             NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_insider_webhooks_key_id
    ON insider_webhook_subscriptions (key_id);

CREATE INDEX IF NOT EXISTS idx_insider_webhooks_active
    ON insider_webhook_subscriptions (is_active)
    WHERE is_active = TRUE;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE insider_trades                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE insider_clusters                ENABLE ROW LEVEL SECURITY;
ALTER TABLE insider_backtests               ENABLE ROW LEVEL SECURITY;
ALTER TABLE insider_webhook_subscriptions   ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- insider_trades policies
-- ----------------------------------------------------------------------------

CREATE POLICY insider_trades_service_all
    ON insider_trades
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Anon users can read recent trades (last 30 days) for landing page previews
CREATE POLICY insider_trades_anon_read
    ON insider_trades
    FOR SELECT
    TO anon
    USING (transaction_date >= CURRENT_DATE - INTERVAL '30 days');

-- ----------------------------------------------------------------------------
-- insider_clusters policies
-- ----------------------------------------------------------------------------

CREATE POLICY insider_clusters_service_all
    ON insider_clusters
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Anon users can read all clusters (used for public signal dashboard)
CREATE POLICY insider_clusters_anon_read
    ON insider_clusters
    FOR SELECT
    TO anon
    USING (true);

-- ----------------------------------------------------------------------------
-- insider_backtests policies
-- ----------------------------------------------------------------------------

CREATE POLICY insider_backtests_service_all
    ON insider_backtests
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Backtest results are public — used for marketing / validation pages
CREATE POLICY insider_backtests_anon_read
    ON insider_backtests
    FOR SELECT
    TO anon
    USING (true);

-- ----------------------------------------------------------------------------
-- insider_webhook_subscriptions policies
-- Webhook URLs may contain secrets — no anon read access.
-- ----------------------------------------------------------------------------

CREATE POLICY insider_webhooks_service_all
    ON insider_webhook_subscriptions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Active clusters in the last 30 days, ordered by strength.
-- Used by /api/v1/insider/clusters/hot endpoint.
CREATE OR REPLACE VIEW v_insider_hot_clusters AS
SELECT
    ic.id,
    ic.ticker,
    ic.company_name,
    ic.cik,
    ic.insider_count,
    ic.total_value,
    ic.avg_price,
    ic.cluster_strength,
    ic.window_start,
    ic.window_end,
    ic.detected_at,
    ic.trades_json,
    CASE
        WHEN ic.cluster_strength >= 80 THEN 'STRONG BUY'
        WHEN ic.cluster_strength >= 60 THEN 'BUY'
        ELSE 'WATCH'
    END AS signal_label
FROM insider_clusters ic
WHERE ic.detected_at >= NOW() - INTERVAL '30 days'
ORDER BY ic.cluster_strength DESC;

-- Latest insider buy summary per ticker (last 30 days).
-- Used for portfolio overlay and dashboard widgets.
CREATE OR REPLACE VIEW v_insider_ticker_summary AS
SELECT
    ticker,
    company_name,
    COUNT(*)                                            AS trade_count,
    COUNT(*) FILTER (WHERE transaction_code = 'P')     AS buy_count,
    COUNT(*) FILTER (WHERE transaction_code = 'S')     AS sell_count,
    SUM(total_value) FILTER (WHERE transaction_code = 'P') AS total_buy_value,
    SUM(total_value) FILTER (WHERE transaction_code = 'S') AS total_sell_value,
    MAX(transaction_date)                               AS latest_trade_date,
    COUNT(DISTINCT insider_name)                        AS unique_insiders
FROM insider_trades
WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ticker, company_name
ORDER BY total_buy_value DESC NULLS LAST;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE insider_trades IS
    'SEC EDGAR Form 4 non-derivative transactions parsed by edgar_fetcher.py. '
    'P = open-market purchase (primary actionable signal). '
    'Fetched and upserted on a daily cron schedule.';

COMMENT ON TABLE insider_clusters IS
    'Detected insider cluster buy events from cluster_detector.py. '
    'A cluster requires 3+ unique insiders buying the same ticker within 10 days, '
    'each trade > $25K value. cluster_strength 80-100 = STRONG BUY signal.';

COMMENT ON TABLE insider_backtests IS
    'Historical backtest results for the cluster buy strategy (2020-2025). '
    'Hold periods: 60, 90, 180 calendar days vs SPY buy-and-hold benchmark.';

COMMENT ON TABLE insider_webhook_subscriptions IS
    'Pro/Enterprise real-time cluster alert subscriptions. '
    'Payload: ClusterOut JSON. Triggered on new cluster detection. '
    'Requires PRO or ENTERPRISE API key tier.';

COMMENT ON COLUMN insider_trades.transaction_code IS
    'P=open-market purchase (bullish) S=sale A=grant D=disposition '
    'F=tax-withholding M=option-exercise C=conversion G=gift. '
    'Only P is used for cluster detection.';

COMMENT ON COLUMN insider_trades.shares IS
    'Positive = acquisition (P, A, M, C). Negative = disposition (S, D, F).';

COMMENT ON COLUMN insider_clusters.cluster_strength IS
    'Score 0-100: base 40 for threshold; +10 per extra insider above 3; '
    '+15 if CEO/CFO/Chairman included; +10 if single trade > $100K; '
    '+5 if 2+ directors present. Capped at 100.';

COMMENT ON COLUMN insider_clusters.trades_json IS
    'JSONB: {"trade_ids": [1,2,3], "insider_names": ["A","B","C"]}. '
    'Stores constituent trade references for fast cluster detail lookups.';
