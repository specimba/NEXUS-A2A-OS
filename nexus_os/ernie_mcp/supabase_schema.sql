-- ERNIE MCP Governance Platform - Supabase Schema
-- Version: 1.0
-- Date: 2026-05-15
-- Purpose: Proposal governance, trust scoring, and anomaly detection for NEXUS OS

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- AGENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    trust_score REAL DEFAULT 25.0 CHECK (trust_score >= 0.0 AND trust_score <= 99.5),
    capabilities TEXT[], -- Array of capability strings
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'quarantined', 'deactivated')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for trust score queries
CREATE INDEX idx_agents_trust_score ON agents(trust_score);
CREATE INDEX idx_agents_status ON agents(status);

-- ============================================================================
-- PROPOSALS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposer_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    proposed_action JSONB NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'voting', 'approved', 'rejected', 'executed', 'failed')),
    governance_level TEXT DEFAULT 'standard' CHECK (governance_level IN ('standard', 'elevated', 'critical')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    voting_ends_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_result JSONB,
    lineage_id TEXT, -- For proposal chains
    trace_id TEXT NOT NULL,
    
    -- Trust snapshot at proposal time
    proposer_trust_at_creation REAL,
    
    -- Weighted voting results
    weighted_approvals REAL DEFAULT 0.0,
    weighted_rejections REAL DEFAULT 0.0,
    total_weight REAL DEFAULT 0.0
);

-- Indexes for common queries
CREATE INDEX idx_proposals_proposer ON proposals(proposer_id);
CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_created ON proposals(created_at DESC);
CREATE INDEX idx_proposals_lineage ON proposals(lineage_id);

-- ============================================================================
-- PROPOSAL_VOTES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS proposal_votes (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id TEXT NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    vote_type TEXT NOT NULL CHECK (vote_type IN ('approve', 'reject', 'abstain')),
    
    -- Weight of this vote (based on agent's trust score at voting time)
    vote_weight REAL DEFAULT 0.0,
    
    -- Reasoning for the vote
    reasoning TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one vote per agent per proposal
    UNIQUE(proposal_id, agent_id)
);

-- Indexes for voting queries
CREATE INDEX idx_votes_proposal ON proposal_votes(proposal_id);
CREATE INDEX idx_votes_agent ON proposal_votes(agent_id);
CREATE INDEX idx_votes_type ON proposal_votes(vote_type);

-- ============================================================================
-- TRUST_EVENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS trust_events (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'proposal_created',
        'proposal_approved',
        'proposal_rejected',
        'proposal_executed',
        'proposal_failed',
        'vote_cast',
        'trust_delta_computed',
        'anomaly_detected',
        'manual_adjustment',
        'system_correction'
    )),
    delta REAL DEFAULT 0.0, -- Trust score change
    new_score REAL, -- Trust score after change
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for trust event queries
CREATE INDEX idx_trust_events_agent ON trust_events(agent_id);
CREATE INDEX idx_trust_events_type ON trust_events(event_type);
CREATE INDEX idx_trust_events_created ON trust_events(created_at DESC);

-- ============================================================================
-- ANOMALIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS anomalies (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    anomaly_type TEXT NOT NULL CHECK (anomaly_type IN (
        'spam_detected',
        'trust_collapse',
        'network_partition',
        'voting_anomaly',
        'proposal_anomaly',
        'behavioral_anomaly'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    
    -- Entity identifiers
    agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
    proposal_id TEXT REFERENCES proposals(id) ON DELETE SET NULL,
    
    -- Anomaly data
    metadata JSONB,
    
    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolution_action TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for anomaly queries
CREATE INDEX idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_anomalies_resolved ON anomalies(resolved);
CREATE INDEX idx_anomalies_agent ON anomalies(agent_id);

-- ============================================================================
-- GOVERNANCE_LOG TABLE (Extended VAP audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS governance_log (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    resource_id TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'HOLD')),
    reason TEXT,
    
    -- VAP-specific fields
    trace_id TEXT NOT NULL,
    proof_chain TEXT, -- Hash chain reference
    signature TEXT, -- Cryptographic signature
    
    -- KAIJU context
    kaiju_context JSONB,
    
    -- Token budget context
    budget_usage_pct REAL,
    budget_remaining INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for governance queries
CREATE INDEX idx_governance_actor ON governance_log(actor_id);
CREATE INDEX idx_governance_decision ON governance_log(decision);
CREATE INDEX idx_governance_trace ON governance_log(trace_id);
CREATE INDEX idx_governance_created ON governance_log(created_at DESC);

-- ============================================================================
-- SKILLS TABLE (For MCP skill management)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT NOT NULL,
    
    -- Skill metadata
    input_schema JSONB,
    output_schema JSONB,
    
    -- Governance
    trust_level TEXT DEFAULT 'standard' CHECK (trust_level IN ('standard', 'elevated', 'critical')),
    cost_per_call REAL DEFAULT 0.0,
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'experimental')),
    
    -- Provenance
    created_by TEXT REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SKILL_PROPOSALS TABLE (For skill governance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_proposals (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id TEXT REFERENCES skills(id) ON DELETE CASCADE,
    proposed_by TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    proposal_type TEXT NOT NULL CHECK (proposal_type IN (
        'create_skill',
        'update_skill',
        'deprecate_skill',
        'change_trust_level'
    )),
    
    proposed_changes JSONB NOT NULL,
    reason TEXT,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'approved', 'rejected')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by TEXT REFERENCES agents(id) ON DELETE SET NULL,
    review_decision_reason TEXT
);

-- ============================================================================
-- STORED FUNCTIONS FOR TRUST SCORING
-- ============================================================================

-- Function to increment agent trust
CREATE OR REPLACE FUNCTION increment_agent_trust(
    p_agent_ids TEXT[],
    p_delta REAL
) RETURNS VOID AS $$
BEGIN
    UPDATE agents 
    SET trust_score = LEAST(trust_score + p_delta, 99.5),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ANY(p_agent_ids);
END;
$$ LANGUAGE plpgsql;

-- Function to decrement agent trust
CREATE OR REPLACE FUNCTION decrement_agent_trust(
    p_agent_ids TEXT[],
    p_delta REAL
) RETURNS VOID AS $$
BEGIN
    UPDATE agents 
    SET trust_score = GREATEST(trust_score - p_delta, 0.0),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ANY(p_agent_ids);
END;
$$ LANGUAGE plpgsql;

-- Function to compute trust delta based on recent performance
CREATE OR REPLACE FUNCTION compute_trust_delta(
    p_agent_id TEXT,
    p_days_back INTEGER DEFAULT 7
) RETURNS TABLE(delta REAL, reason TEXT) AS $$
DECLARE
    v_accepted_rate REAL;
    v_participation_rate REAL;
    v_total_proposals INTEGER;
    v_total_votes INTEGER;
    v_weighted_delta REAL;
BEGIN
    -- Calculate proposal acceptance rate
    SELECT 
        COUNT(*) FILTER (WHERE status = 'approved')::REAL / NULLIF(COUNT(*), 0),
        COUNT(*)
    INTO v_accepted_rate, v_total_proposals
    FROM proposals
    WHERE proposer_id = p_agent_id
    AND created_at >= CURRENT_TIMESTAMP - (p_days_back || ' days')::INTERVAL;
    
    -- Calculate voting participation rate
    SELECT COUNT(*)
    INTO v_total_votes
    FROM proposal_votes
    WHERE agent_id = p_agent_id
    AND created_at >= CURRENT_TIMESTAMP - (p_days_back || ' days')::INTERVAL;
    
    -- Calculate participation rate
    v_participation_rate := v_total_votes::REAL / NULLIF(v_total_proposals, 1);
    
    -- Compute weighted delta
    v_weighted_delta := (COALESCE(v_accepted_rate, 0) * 0.6 + COALESCE(v_participation_rate, 0) * 0.4) * 0.1;
    
    RETURN QUERY SELECT 
        v_weighted_delta,
        format('Accepted: %.1f%%, Participation: %.1f%%', 
               COALESCE(v_accepted_rate, 0) * 100, 
               COALESCE(v_participation_rate, 0) * 100);
END;
$$ LANGUAGE plpgsql;

-- Function to check consensus for a proposal
CREATE OR REPLACE FUNCTION check_proposal_consensus(
    p_proposal_id TEXT,
    p_threshold REAL DEFAULT 0.66
) RETURNS TABLE(has_consensus BOOLEAN, approval_ratio REAL, total_weight REAL) AS $$
DECLARE
    v_approvals REAL;
    v_total_weight REAL;
    v_approval_ratio REAL;
BEGIN
    -- Calculate weighted approvals and total weight
    SELECT 
        COALESCE(SUM(CASE WHEN vote_type = 'approve' THEN vote_weight ELSE 0 END), 0),
        COALESCE(SUM(vote_weight), 0)
    INTO v_approvals, v_total_weight
    FROM proposal_votes
    WHERE proposal_id = p_proposal_id;
    
    -- Calculate approval ratio
    IF v_total_weight > 0 THEN
        v_approval_ratio := v_approvals / v_total_weight;
    ELSE
        v_approval_ratio := 0;
    END IF;
    
    -- Check consensus
    RETURN QUERY SELECT 
        v_approval_ratio >= p_threshold,
        v_approval_ratio,
        v_total_weight;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Trigger to update updated_at timestamp on agents
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update proposal weighted voting results
CREATE OR REPLACE FUNCTION update_proposal_vote_totals()
RETURNS TRIGGER AS $$
BEGIN
    -- Recalculate weighted voting totals
    UPDATE proposals
    SET 
        weighted_approvals = (
            SELECT COALESCE(SUM(vote_weight), 0)
            FROM proposal_votes
            WHERE proposal_id = NEW.proposal_id AND vote_type = 'approve'
        ),
        weighted_rejections = (
            SELECT COALESCE(SUM(vote_weight), 0)
            FROM proposal_votes
            WHERE proposal_id = NEW.proposal_id AND vote_type = 'reject'
        ),
        total_weight = (
            SELECT COALESCE(SUM(vote_weight), 0)
            FROM proposal_votes
            WHERE proposal_id = NEW.proposal_id
        )
    WHERE id = NEW.proposal_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_proposal_votes AFTER INSERT OR UPDATE ON proposal_votes
    FOR EACH ROW EXECUTE FUNCTION update_proposal_vote_totals();

-- ============================================================================
-- INITIAL DATA SEEDING
-- ============================================================================

-- Insert initial agents (can be customized)
INSERT INTO agents (id, name, trust_score, capabilities, status) VALUES
    ('claude-nexus-v1', 'Claude NEXUS', 92.0, ARRAY['code_generation', 'governance_audit', 'swarm_orchestration'], 'active'),
    ('gpt4-nexus-v1', 'GPT-4 NEXUS', 88.0, ARRAY['research', 'analysis', 'documentation'], 'active'),
    ('llama-nexus-v1', 'Llama NEXUS', 75.0, ARRAY['local_inference', 'privacy_preserving'], 'active'),
    ('grok-agentic-v1', 'Grok Agentic Team Leader', 95.0, ARRAY['orchestration', 'routing', 'coordination'], 'active'),
    ('gemini-research-v1', 'Gemini Research Agent', 85.0, ARRAY['research', 'analysis', 'multi_hop_reasoning'], 'active')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for agent trust scores with recent activity
CREATE OR REPLACE VIEW v_agent_trust_summary AS
SELECT 
    a.id,
    a.name,
    a.trust_score,
    a.status,
    a.capabilities,
    COUNT(DISTINCT p.id) AS total_proposals,
    COUNT(DISTINCT CASE WHEN p.status = 'approved' THEN p.id END) AS approved_proposals,
    COUNT(DISTINCT pv.id) AS total_votes,
    MAX(te.created_at) AS last_trust_event
FROM agents a
LEFT JOIN proposals p ON a.id = p.proposer_id
LEFT JOIN proposal_votes pv ON a.id = pv.agent_id
LEFT JOIN trust_events te ON a.id = te.agent_id
GROUP BY a.id, a.name, a.trust_score, a.status, a.capabilities;

-- View for active proposals needing votes
CREATE OR REPLACE VIEW v_active_proposals AS
SELECT 
    p.id,
    p.proposer_id,
    a.name AS proposer_name,
    p.description,
    p.status,
    p.governance_level,
    p.created_at,
    p.voting_ends_at,
    p.weighted_approvals,
    p.weighted_rejections,
    p.total_weight,
    CASE 
        WHEN p.total_weight > 0 THEN (p.weighted_approvals / p.total_weight)
        ELSE 0 
    END AS approval_ratio,
    COUNT(DISTINCT pv.agent_id) AS vote_count
FROM proposals p
JOIN agents a ON p.proposer_id = a.id
LEFT JOIN proposal_votes pv ON p.id = pv.proposal_id
WHERE p.status IN ('pending', 'voting')
GROUP BY p.id, p.proposer_id, a.name, p.description, p.status, p.governance_level, 
         p.created_at, p.voting_ends_at, p.weighted_approvals, p.weighted_rejections, p.total_weight;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE proposal_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE governance_log ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (these should be customized based on auth system)
CREATE POLICY "Agents are readable by authenticated users" ON agents
    FOR SELECT USING (true);

CREATE POLICY "Proposals are readable by authenticated users" ON proposals
    FOR SELECT USING (true);

CREATE POLICY "Proposal votes are readable by authenticated users" ON proposal_votes
    FOR SELECT USING (true);

CREATE POLICY "Trust events are readable by authenticated users" ON trust_events
    FOR SELECT USING (true);

CREATE POLICY "Governance log is readable by authenticated users" ON governance_log
    FOR SELECT USING (true);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Grant necessary permissions (adjust as needed for your auth setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_supabase_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_supabase_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_supabase_user;