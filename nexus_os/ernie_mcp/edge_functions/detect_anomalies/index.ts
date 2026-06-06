/**
 * Supabase Edge Function: detect_anomalies
 * Purpose: Detect and alert on system anomalies in real-time
 * Schedule: Runs every 30 seconds via cron trigger
 * 
 * This function detects:
 * 1. Spam attacks (excessive proposal creation)
 * 2. Trust collapse (rapid trust score drops)
 * 3. Network partition (low voting participation)
 * 4. Voting anomalies (unusual voting patterns)
 * 5. Proposal anomalies (suspicious proposal patterns)
 * 6. Behavioral anomalies (unusual agent behavior)
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface Anomaly {
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  agent_id?: string
  proposal_id?: string
  metadata: Record<string, unknown>
}

serve(async (req) => {
  try {
    console.log('[detect_anomalies] Starting anomaly detection')
    
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)
    
    const detectedAnomalies: Anomaly[] = []
    
    // Step 1: Detect spam attacks
    console.log('[detect_anomalies] Checking for spam attacks...')
    const spamAnomalies = await detectSpamAttacks(supabase)
    detectedAnomalies.push(...spamAnomalies)
    
    // Step 2: Detect trust collapse
    console.log('[detect_anomalies] Checking for trust collapse...')
    const trustAnomalies = await detectTrustCollapse(supabase)
    detectedAnomalies.push(...trustAnomalies)
    
    // Step 3: Detect network partition
    console.log('[detect_anomalies] Checking for network partition...')
    const networkAnomalies = await detectNetworkPartition(supabase)
    detectedAnomalies.push(...networkAnomalies)
    
    // Step 4: Detect voting anomalies
    console.log('[detect_anomalies] Checking for voting anomalies...')
    const votingAnomalies = await detectVotingAnomalies(supabase)
    detectedAnomalies.push(...votingAnomalies)
    
    // Step 5: Detect proposal anomalies
    console.log('[detect_anomalies] Checking for proposal anomalies...')
    const proposalAnomalies = await detectProposalAnomalies(supabase)
    detectedAnomalies.push(...proposalAnomalies)
    
    // Step 6: Detect behavioral anomalies
    console.log('[detect_anomalies] Checking for behavioral anomalies...')
    const behaviorAnomalies = await detectBehavioralAnomalies(supabase)
    detectedAnomalies.push(...behaviorAnomalies)
    
    console.log(`[detect_anomalies] Detected ${detectedAnomalies.length} anomalies`)
    
    // Step 7: Store detected anomalies
    for (const anomaly of detectedAnomalies) {
      await supabase.from('anomalies').insert({
        anomaly_type: anomaly.type,
        severity: anomaly.severity,
        description: anomaly.description,
        agent_id: anomaly.agent_id,
        proposal_id: anomaly.proposal_id,
        metadata: anomaly.metadata,
        resolved: false
      })
    }
    
    // Step 8: Take automatic actions for critical anomalies
    for (const anomaly of detectedAnomalies) {
      if (anomaly.severity === 'critical') {
        await handleCriticalAnomaly(supabase, anomaly)
      }
    }
    
    // Step 9: Publish to Kafka if configured
    const kafkaUrl = Deno.env.get('KAFKA_PRODUCER_URL')
    const kafkaApiKey = Deno.env.get('KAFKA_API_KEY')
    
    if (kafkaUrl && kafkaApiKey && detectedAnomalies.length > 0) {
      try {
        await fetch(kafkaUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${kafkaApiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            topic: 'nexus-anomalies',
            records: detectedAnomalies.map(anomaly => ({
              key: anomaly.type,
              value: JSON.stringify(anomaly)
            }))
          })
        })
        console.log('[detect_anomalies] Published anomalies to Kafka')
      } catch (kafkaError) {
        console.error('[detect_anomalies] Kafka publish failed:', kafkaError)
      }
    }
    
    return new Response(
      JSON.stringify({ 
        status: 'success',
        anomalies_detected: detectedAnomalies.length,
        anomalies: detectedAnomalies
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
    
  } catch (error) {
    console.error('[detect_anomalies] Error:', error)
    
    return new Response(
      JSON.stringify({ 
        error: error.message,
        status: 'error'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

async function detectSpamAttacks(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for proposals created in last minute
  const oneMinuteAgo = new Date(Date.now() - 60 * 1000).toISOString()
  
  const { data: recentProposals } = await supabase
    .from('proposals')
    .select('proposer_id, created_at')
    .gte('created_at', oneMinuteAgo)
  
  if (!recentProposals) return anomalies
  
  // Count proposals per agent
  const proposalCounts: Record<string, number> = {}
  recentProposals.forEach((p: any) => {
    proposalCounts[p.proposer_id] = (proposalCounts[p.proposer_id] || 0) + 1
  })
  
  // Detect spam (more than 10 proposals per minute)
  for (const [agentId, count] of Object.entries(proposalCounts)) {
    if (count > 10) {
      anomalies.push({
        type: 'spam_detected',
        severity: count > 30 ? 'critical' : 'high',
        description: `${count} proposals created in 1 minute by agent ${agentId}`,
        agent_id: agentId,
        metadata: {
          proposal_count: count,
          time_window: '1 minute',
          threshold: 10
        }
      })
    }
  }
  
  return anomalies
}

async function detectTrustCollapse(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for trust score drops in last hour
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()
  
  const { data: agents } = await supabase
    .from('agents')
    .select('id, trust_score, status')
    .eq('status', 'active')
  
  if (!agents) return anomalies
  
  for (const agent of agents) {
    const { data: trustEvents } = await supabase
      .from('trust_events')
      .select('delta, created_at')
      .eq('agent_id', agent.id)
      .gte('created_at', oneHourAgo)
    
    if (!trustEvents) continue
    
    const hourlyDelta = trustEvents.reduce((sum: number, e: any) => sum + (e.delta || 0), 0)
    
    // Detect significant trust drop (>10 points in 1 hour)
    if (hourlyDelta < -10) {
      anomalies.push({
        type: 'trust_collapse',
        severity: hourlyDelta < -25 ? 'critical' : 'high',
        description: `Trust score dropped by ${hourlyDelta.toFixed(1)} points in 1 hour for agent ${agent.id}`,
        agent_id: agent.id,
        metadata: {
          hourly_delta: hourlyDelta,
          current_trust: agent.trust_score,
          time_window: '1 hour',
          threshold: -10
        }
      })
    }
  }
  
  return anomalies
}

async function detectNetworkPartition(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for proposals with low voting participation
  const { data: votingProposals } = await supabase
    .from('proposals')
    .select('id, created_at')
    .eq('status', 'voting')
    .gte('created_at', new Date(Date.now() - 10 * 60 * 1000).toISOString())  // Last 10 minutes
  
  if (!votingProposals) return anomalies
  
  const { data: allAgents } = await supabase
    .from('agents')
    .select('id')
    .eq('status', 'active')
  
  if (!allAgents) return anomalies
  
  const totalAgents = allAgents.length
  
  for (const proposal of votingProposals) {
    const { data: votes } = await supabase
      .from('proposal_votes')
      .select('agent_id')
      .eq('proposal_id', proposal.id)
    
    const voteCount = votes?.length || 0
    const participationRate = totalAgents > 0 ? voteCount / totalAgents : 0
    
    // Detect low participation (<33%)
    if (participationRate < 0.33 && totalAgents > 3) {
      anomalies.push({
        type: 'network_partition',
        severity: 'medium',
        description: `Low voting participation for proposal ${proposal.id}: ${voteCount}/${totalAgents} agents voted`,
        proposal_id: proposal.id,
        metadata: {
          vote_count: voteCount,
          total_agents: totalAgents,
          participation_rate: participationRate,
          threshold: 0.33
        }
      })
    }
  }
  
  return anomalies
}

async function detectVotingAnomalies(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for agents voting too quickly (potential automated voting)
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()
  
  const { data: recentVotes } = await supabase
    .from('proposal_votes')
    .select('agent_id, created_at, vote_type')
    .gte('created_at', fiveMinutesAgo)
  
  if (!recentVotes) return anomalies
  
  const voteCounts: Record<string, number> = {}
  recentVotes.forEach((v: any) => {
    voteCounts[v.agent_id] = (voteCounts[v.agent_id] || 0) + 1
  })
  
  // Detect excessive voting (>20 votes in 5 minutes)
  for (const [agentId, count] of Object.entries(voteCounts)) {
    if (count > 20) {
      anomalies.push({
        type: 'voting_anomaly',
        severity: 'high',
        description: `Agent ${agentId} cast ${count} votes in 5 minutes (potential automated voting)`,
        agent_id: agentId,
        metadata: {
          vote_count: count,
          time_window: '5 minutes',
          threshold: 20
        }
      })
    }
  }
  
  return anomalies
}

async function detectProposalAnomalies(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for similar proposals from same agent (potential duplicate spam)
  const { data: agentProposals } = await supabase
    .from('proposals')
    .select('id, proposer_id, description, proposed_action')
    .eq('status', 'pending')
    .gte('created_at', new Date(Date.now() - 60 * 60 * 1000).toISOString())  // Last hour
  
  if (!agentProposals) return anomalies
  
  // Group by agent
  const proposalsByAgent: Record<string, any[]> = {}
  agentProposals.forEach((p: any) => {
    if (!proposalsByAgent[p.proposer_id]) {
      proposalsByAgent[p.proposer_id] = []
    }
    proposalsByAgent[p.proposer_id].push(p)
  })
  
  // Detect duplicate proposals
  for (const [agentId, proposals] of Object.entries(proposalsByAgent)) {
    if (proposals.length > 5) {
      anomalies.push({
        type: 'proposal_anomaly',
        severity: 'medium',
        description: `Agent ${agentId} has ${proposals.length} pending proposals (potential duplicate spam)`,
        agent_id: agentId,
        metadata: {
          proposal_count: proposals.length,
          time_window: '1 hour',
          threshold: 5
        }
      })
    }
  }
  
  return anomalies
}

async function detectBehavioralAnomalies(supabase: any): Promise<Anomaly[]> {
  const anomalies: Anomaly[] = []
  
  // Check for agents with sudden behavior changes
  const { data: agents } = await supabase
    .from('agents')
    .select('id, trust_score, status')
    .eq('status', 'active')
  
  if (!agents) return anomalies
  
  for (const agent of agents) {
    // Compare current behavior to baseline
    const { data: recentActivity } = await supabase
      .from('trust_events')
      .select('event_type, delta, created_at')
      .eq('agent_id', agent.id)
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())  // Last 24 hours
    
    if (!recentActivity) continue
    
    // Check for unusual event type distribution
    const eventTypes: Record<string, number> = {}
    recentActivity.forEach((e: any) => {
      eventTypes[e.event_type] = (eventTypes[e.event_type] || 0) + 1
    })
    
    // Detect unusual concentration of negative events
    const negativeEvents = eventTypes['proposal_rejected'] || 0 + eventTypes['proposal_failed'] || 0
    const totalEvents = recentActivity.length
    
    if (totalEvents > 10 && negativeEvents / totalEvents > 0.7) {
      anomalies.push({
        type: 'behavioral_anomaly',
        severity: 'medium',
        description: `Agent ${agent.id} showing unusually high negative event rate (${negativeEvents}/${totalEvents})`,
        agent_id: agent.id,
        metadata: {
          negative_events: negativeEvents,
          total_events: totalEvents,
          negative_ratio: negativeEvents / totalEvents,
          event_distribution: eventTypes
        }
      })
    }
  }
  
  return anomalies
}

async function handleCriticalAnomaly(supabase: any, anomaly: Anomaly) {
  console.log(`[detect_anomalies] Handling critical anomaly: ${anomaly.type}`)
  
  // Take automatic protective actions based on anomaly type
  switch (anomaly.type) {
    case 'spam_detected':
      // Quarantine the spamming agent
      if (anomaly.agent_id) {
        await supabase
          .from('agents')
          .update({ status: 'quarantined' })
          .eq('id', anomaly.agent_id)
        
        console.log(`[detect_anomalies] Quarantined agent ${anomaly.agent_id} due to spam`)
      }
      break
    
    case 'trust_collapse':
      // Force trust floor for collapsing agent
      if (anomaly.agent_id) {
        await supabase
          .from('agents')
          .update({ trust_score: 0.0 })
          .eq('id', anomaly.agent_id)
        
        console.log(`[detect_anomalies] Set trust to 0 for collapsing agent ${anomaly.agent_id}`)
      }
      break
    
    default:
      console.log(`[detect_anomalies] No automatic action defined for ${anomaly.type}`)
  }
}