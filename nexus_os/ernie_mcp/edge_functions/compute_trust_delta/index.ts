/**
 * Supabase Edge Function: compute_trust_delta
 * Purpose: Periodic computation of trust score deltas based on agent performance
 * Schedule: Runs every 5 minutes via cron trigger
 * 
 * This function:
 * 1. Analyzes each agent's recent performance metrics
 * 2. Calculates trust score adjustments based on:
 *    - Proposal acceptance rate
 *    - Voting participation rate
 *    - Execution success rate
 *    - Anomaly detection results
 * 3. Applies computed deltas with appropriate decay
 * 4. Logs all trust changes for audit trail
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  try {
    console.log('[compute_trust_delta] Starting trust delta computation')
    
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)
    
    // Step 1: Fetch all active agents
    const { data: agents, error: agentsError } = await supabase
      .from('agents')
      .select('id, name, trust_score, capabilities, status')
      .eq('status', 'active')
    
    if (agentsError) {
      throw new Error(`Failed to fetch agents: ${agentsError.message}`)
    }
    
    console.log(`[compute_trust_delta] Processing ${agents.length} active agents`)
    
    let totalDeltasComputed = 0
    const trustChanges: Array<{ agent_id: string; delta: number; reason: string }> = []
    
    // Step 2: Compute trust delta for each agent
    for (const agent of agents) {
      try {
        const delta = await computeAgentTrustDelta(supabase, agent.id)
        
        if (Math.abs(delta.delta) > 0.01) {  // Only apply significant changes
          trustChanges.push({
            agent_id: agent.id,
            delta: delta.delta,
            reason: delta.reason
          })
          
          // Apply the delta
          if (delta.delta > 0) {
            await supabase.rpc('increment_agent_trust', {
              p_agent_ids: [agent.id],
              p_delta: delta.delta
            })
          } else if (delta.delta < 0) {
            await supabase.rpc('decrement_agent_trust', {
              p_agent_ids: [agent.id],
              p_delta: Math.abs(delta.delta)
            })
          }
          
          // Log the trust event
          await supabase.from('trust_events').insert({
            agent_id: agent.id,
            event_type: 'trust_delta_computed',
            delta: delta.delta,
            new_score: agent.trust_score + delta.delta,
            reason: delta.reason,
            metadata: delta.metadata
          })
          
          totalDeltasComputed++
        }
        
      } catch (agentError) {
        console.error(`[compute_trust_delta] Error computing delta for agent ${agent.id}:`, agentError)
        continue
      }
    }
    
    // Step 3: Generate summary report
    const summary = {
      timestamp: new Date().toISOString(),
      agents_processed: agents.length,
      deltas_applied: totalDeltasComputed,
      trust_changes: trustChanges,
      average_delta: trustChanges.length > 0 
        ? trustChanges.reduce((sum, c) => sum + c.delta, 0) / trustChanges.length 
        : 0
    }
    
    console.log('[compute_trust_delta] Summary:', JSON.stringify(summary))
    
    // Step 4: Publish summary to Kafka if configured
    const kafkaUrl = Deno.env.get('KAFKA_PRODUCER_URL')
    const kafkaApiKey = Deno.env.get('KAFKA_API_KEY')
    
    if (kafkaUrl && kafkaApiKey) {
      try {
        await fetch(kafkaUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${kafkaApiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            topic: 'nexus-trust-updates',
            records: [{
              key: 'trust-delta-computation',
              value: JSON.stringify(summary)
            }]
          })
        })
        console.log('[compute_trust_delta] Published summary to Kafka')
      } catch (kafkaError) {
        console.error('[compute_trust_delta] Kafka publish failed:', kafkaError)
      }
    }
    
    return new Response(
      JSON.stringify({ 
        status: 'success',
        summary: summary
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
    
  } catch (error) {
    console.error('[compute_trust_delta] Error:', error)
    
    return new Response(
      JSON.stringify({ 
        error: error.message,
        status: 'error'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

async function computeAgentTrustDelta(
  supabase: any, 
  agentId: string
): Promise<{ delta: number; reason: string; metadata: any }> {
  
  // Time window for analysis (7 days)
  const timeWindow = '7 days'
  
  // Step 1: Calculate proposal acceptance rate
  const { data: proposals } = await supabase
    .from('proposals')
    .select('id, status, created_at')
    .eq('proposer_id', agentId)
    .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
  
  const totalProposals = proposals?.length || 0
  const approvedProposals = proposals?.filter((p: any) => p.status === 'approved').length || 0
  const acceptanceRate = totalProposals > 0 ? approvedProposals / totalProposals : 0
  
  // Step 2: Calculate voting participation rate
  const { data: votes } = await supabase
    .from('proposal_votes')
    .select('id, created_at')
    .eq('agent_id', agentId)
    .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
  
  const totalVotes = votes?.length || 0
  const participationRate = totalProposals > 0 ? totalVotes / totalProposals : 0
  
  // Step 3: Calculate execution success rate
  const { data: executedProposals } = await supabase
    .from('proposals')
    .select('id, execution_result')
    .eq('proposer_id', agentId)
    .eq('status', 'executed')
    .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
  
  const totalExecuted = executedProposals?.length || 0
  const successfulExecutions = executedProposals?.filter((p: any) => 
    p.execution_result?.success === true
  ).length || 0
  const successRate = totalExecuted > 0 ? successfulExecutions / totalExecuted : 0
  
  // Step 4: Check for recent anomalies
  const { data: recentAnomalies } = await supabase
    .from('anomalies')
    .select('id, severity, anomaly_type')
    .eq('agent_id', agentId)
    .eq('resolved', false)
    .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
  
  const hasCriticalAnomalies = recentAnomalies?.some((a: any) => a.severity === 'critical') || false
  const hasHighAnomalies = recentAnomalies?.some((a: any) => a.severity === 'high') || false
  
  // Step 5: Calculate weighted delta
  let delta = 0
  
  // Proposal acceptance contribution (40% weight)
  if (totalProposals > 0) {
    // Good acceptance rates increase trust
    if (acceptanceRate > 0.7) {
      delta += (acceptanceRate - 0.7) * 2.0
    } else if (acceptanceRate < 0.3) {
      delta -= (0.3 - acceptanceRate) * 3.0  // Penalty for poor acceptance
    }
  }
  
  // Voting participation contribution (20% weight)
  if (participationRate > 0.5) {
    delta += participationRate * 0.5
  } else if (participationRate < 0.1 && totalProposals > 0) {
    delta -= 1.0  // Penalty for not participating
  }
  
  // Execution success contribution (30% weight)
  if (totalExecuted > 0) {
    if (successRate > 0.8) {
      delta += (successRate - 0.8) * 2.0
    } else if (successRate < 0.5) {
      delta -= (0.5 - successRate) * 3.0  // Penalty for poor execution
    }
  }
  
  // Anomaly penalties (10% weight)
  if (hasCriticalAnomalies) {
    delta -= 5.0  // Significant penalty for critical anomalies
  } else if (hasHighAnomalies) {
    delta -= 2.0  // Moderate penalty for high anomalies
  }
  
  // Apply decay factor to prevent rapid swings
  delta *= 0.1  // Only apply 10% of computed delta per run
  
  // Cap delta to prevent extreme changes
  delta = Math.max(-2.0, Math.min(2.0, delta))
  
  // Generate reason
  let reason = 'Trust delta computed from performance metrics'
  const reasons: string[] = []
  
  if (totalProposals > 0) {
    reasons.push(`acceptance rate: ${(acceptanceRate * 100).toFixed(1)}%`)
  }
  if (totalVotes > 0) {
    reasons.push(`participation rate: ${(participationRate * 100).toFixed(1)}%`)
  }
  if (totalExecuted > 0) {
    reasons.push(`success rate: ${(successRate * 100).toFixed(1)}%`)
  }
  if (hasCriticalAnomalies) {
    reasons.push('critical anomalies detected')
  } else if (hasHighAnomalies) {
    reasons.push('high anomalies detected')
  }
  
  if (reasons.length > 0) {
    reason = 'Trust delta: ' + reasons.join(', ')
  }
  
  // Metadata for audit trail
  const metadata = {
    time_window: timeWindow,
    total_proposals: totalProposals,
    approved_proposals: approvedProposals,
    acceptance_rate: acceptanceRate,
    total_votes: totalVotes,
    participation_rate: participationRate,
    total_executed: totalExecuted,
    successful_executions: successfulExecutions,
    success_rate: successRate,
    critical_anomalies: hasCriticalAnomalies,
    high_anomalies: hasHighAnomalies,
    computed_delta: delta,
    components: {
      acceptance_contribution: delta * 0.4,
      participation_contribution: delta * 0.2,
      success_contribution: delta * 0.3,
      anomaly_penalty: delta * 0.1
    }
  }
  
  return {
    delta: parseFloat(delta.toFixed(3)),
    reason: reason,
    metadata: metadata
  }
}