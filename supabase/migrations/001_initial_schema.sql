-- AetherTrade-Swarm Initial Schema
-- Supabase project: sooufmgxxuirbsxouxju (EU-West)

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE regime_state AS ENUM ('bull', 'range', 'bear', 'crisis');
CREATE TYPE signal_direction AS ENUM ('long', 'short', 'neutral');
CREATE TYPE order_status AS ENUM ('pending', 'filled', 'cancelled', 'rejected');
CREATE TYPE order_side AS ENUM ('buy', 'sell');
CREATE TYPE alert_severity AS ENUM ('info', 'warning', 'critical');

-- ============================================================================
-- MARKET DATA
-- ============================================================================

CREATE TABLE market_data_daily (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT,
    adj_close DOUBLE PRECISION,
    source TEXT DEFAULT 'yfinance',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, date)
);

CREATE INDEX idx_market_data_symbol_date ON market_data_daily (symbol, date DESC);
CREATE INDEX idx_market_data_date ON market_data_daily (date DESC);

-- ============================================================================
-- API KEYS (migrated from Oracle Swarm)
-- ============================================================================

CREATE TABLE api_keys (
    key_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    owner_email TEXT,
    description TEXT,
    prefix TEXT,
    rate_limit_per_minute INT DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    request_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- REGIME DETECTION
-- ============================================================================

CREATE TABLE regime_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    regime regime_state NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    probabilities JSONB DEFAULT '{}',
    duration_days INT,
    trigger_reason TEXT,
    hmm_params JSONB DEFAULT '{}'
);

CREATE INDEX idx_regime_timestamp ON regime_history (timestamp DESC);

-- ============================================================================
-- SIGNALS
-- ============================================================================

CREATE TABLE signals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pod_name TEXT NOT NULL,
    asset TEXT NOT NULL,
    signal_name TEXT NOT NULL,
    direction signal_direction NOT NULL,
    strength DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    metadata JSONB DEFAULT '{}',
    regime regime_state,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_signals_pod_date ON signals (pod_name, created_at DESC);
CREATE INDEX idx_signals_asset ON signals (asset, created_at DESC);

-- ============================================================================
-- TRADES & POSITIONS
-- ============================================================================

CREATE TABLE trades (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    signal_id BIGINT REFERENCES signals(id),
    symbol TEXT NOT NULL,
    side order_side NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    total_value DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION DEFAULT 0,
    pod_name TEXT,
    status order_status DEFAULT 'filled',
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_trades_symbol ON trades (symbol, executed_at DESC);
CREATE INDEX idx_trades_pod ON trades (pod_name, executed_at DESC);

CREATE TABLE positions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    side order_side NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    avg_entry_price DOUBLE PRECISION NOT NULL,
    current_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION DEFAULT 0,
    realized_pnl DOUBLE PRECISION DEFAULT 0,
    pod_name TEXT,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_positions_symbol ON positions (symbol);

-- ============================================================================
-- PORTFOLIO PERFORMANCE
-- ============================================================================

CREATE TABLE portfolio_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    nav DOUBLE PRECISION NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    gross_exposure DOUBLE PRECISION,
    net_exposure DOUBLE PRECISION,
    leverage DOUBLE PRECISION,
    position_count INT,
    daily_return DOUBLE PRECISION,
    cumulative_return DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_snapshots_date ON portfolio_snapshots (date DESC);

-- ============================================================================
-- POD METRICS
-- ============================================================================

CREATE TABLE pod_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pod_name TEXT NOT NULL,
    date DATE NOT NULL,
    signal_count INT DEFAULT 0,
    win_rate DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    total_return DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    allocation_weight DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (pod_name, date)
);

CREATE INDEX idx_pod_metrics_pod_date ON pod_metrics (pod_name, date DESC);

-- ============================================================================
-- RISK ALERTS
-- ============================================================================

CREATE TABLE risk_alerts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    severity alert_severity NOT NULL,
    metric TEXT NOT NULL,
    message TEXT NOT NULL,
    value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    auto_action TEXT,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_risk_alerts_severity ON risk_alerts (severity, triggered_at DESC);

-- ============================================================================
-- SYSTEM
-- ============================================================================

CREATE TABLE system_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    level TEXT NOT NULL DEFAULT 'info',
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_logs_created ON system_logs (created_at DESC);

-- ============================================================================
-- ENABLE RLS (basic — no user auth yet, service_role bypasses)
-- ============================================================================

ALTER TABLE market_data_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE regime_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE pod_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (backend uses service_role key)
CREATE POLICY "service_role_all" ON market_data_daily FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON api_keys FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON regime_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON signals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON trades FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON positions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON portfolio_snapshots FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON pod_metrics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON risk_alerts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON system_logs FOR ALL USING (true) WITH CHECK (true);

-- Anon can read market data and regime (public dashboard)
CREATE POLICY "anon_read_market" ON market_data_daily FOR SELECT USING (true);
CREATE POLICY "anon_read_regime" ON regime_history FOR SELECT USING (true);
CREATE POLICY "anon_read_snapshots" ON portfolio_snapshots FOR SELECT USING (true);
CREATE POLICY "anon_read_pod_metrics" ON pod_metrics FOR SELECT USING (true);
