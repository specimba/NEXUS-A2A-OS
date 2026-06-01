/**
 * Supabase Edge Function: on_proposal_created
 * Purpose: Handle new proposal creation events in NEXUS OS governance system
 * Triggers: Called when a new proposal is inserted into the proposals table
 * 
 * This function:
 * 1. Validates the proposal structure
 * 2. Notifies external systems (Kafka, webhooks)
 * 3. Initiates voting period if needed
 * 4. Logs to governance audit trail
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface ProposalEvent {
  proposal_id: string
  proposer_id: string
  proposed_action: Record<string, unknown>
  description: string
  governance_level: 'standard' | 'elevated' | 'critical'
  trace_id: string
}

serve(async (req) => {
  try {
    // Parse request body
    const event: ProposalEvent = await req.json()
    
    console.log(`[on_proposal_created] Processing proposal ${event.proposal_id} from agent ${event.proposer_id}`)
    
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)
    
    // Step 1: Validate proposal structure
    if (!event.proposal_id || !event.proposer_id || !event.proposed_action) {
      throw new Error('Invalid proposal structure: missing required fields')
    }
    
    // Step 2: Fetch proposer's current trust score
    const { data: agent } = await supabase
      .from('agents')
      .select('trust_score, status')
      .eq('id', event.proposer_id)
      .single()
    
    if (!agent) {
      throw new Error(`Agent not found: ${event.proposer_id}`)
    }
    
    if (agent.status !== 'active') {
      throw new Error(`Agent is not active: ${event.proposer_id} has status ${agent.status}`)
    }
    
    console.log(`[on_proposal_created] Agent trust score: ${agent.trust_score}`)
    
    // Step 3: Check if trust score meets governance level threshold
    const trustThresholds = {
      'standard': 0.0,    // Anyone can propose
      'elevated': 50.0,   // Need 50+ trust
      'critical': 75.0    // Need 75+ trust
    }
    
    const threshold = trustThresholds[event.governance_level] || 0.0
    if (agent.trust_score < threshold) {
      await supabase
        .from('proposals')
        .update({ 
          status: 'rejected',
          execution_result: { 
            error: `Trust score ${agent.trust_score} below threshold ${threshold} for ${event.governance_level} proposals`
          }
        })
        .eq('id', event.proposal_id)
      
      // Log to trust events
      await supabase.from('trust_events').insert({
        agent_id: event.proposer_id,
        event_type: 'proposal_rejected',
        delta: 0,
        reason: `Trust score below threshold for ${event.governance_level} proposal`,
        metadata: { proposal_id: event.proposal_id, governance_level: event.governance_level }
      })
      
      return new Response(
        JSON.stringify({ 
          status: 'rejected', 
          reason: `Trust score ${agent.trust_score} below threshold ${threshold}` 
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Step 4: Update proposal with trust snapshot
    await supabase
      .from('proposals')
      .update({ 
        proposer_trust_at_creation: agent.trust_score,
        status: 'voting'
      })
      .eq('id', event.proposal_id)
    
    // Step 5: Set voting period based on governance level
    const votingPeriods = {
      'standard': 24 * 60 * 60 * 1000,    // 24 hours
      'elevated': 48 * 60 * 60 * 1000,    // 48 hours  
      'critical': 72 * 60 * 60 * 1000     // 72 hours
    }
    
    const votingEndsAt = new Date(Date.now() + votingPeriods[event.governance_level])
    
    await supabase
      .from('proposals')
      .update({ voting_ends_at: votingEndsAt.toISOString() })
      .eq('id', event.proposal_id)
    
    // Step 6: Log trust event
    await supabase.from('trust_events').insert({
      agent_id: event.proposer_id,
      event_type: 'proposal_created',
      delta: 0,
      reason: `Created ${event.governance_level} proposal`,
      metadata: { 
        proposal_id: event.proposal_id,
        governance_level: event.governance_level,
        trust_at_creation: agent.trust_score
      }
    })
    
    // Step 7: Notify external systems (Kafka, if configured)
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
            topic: 'nexus-proposals',
            records: [{
              key: event.proposal_id,
              value: JSON.stringify({
                proposal_id: event.proposal_id,
                proposer_id: event.proposer_id,
                governance_level: event.governance_level,
                status: 'voting',
                voting_ends_at: votingEndsAt.toISOString(),
                trust_score: agent.trust_score,
                trace_id: event.trace_id
              })
            }]
          })
        })
        console.log('[on_proposal_created] Published to Kafka topic nexus-proposals')
      } catch (kafkaError) {
        console.error('[on_proposal_created] Kafka publish failed:', kafkaError)
        // Don't fail the function for Kafka errors
      }
    }
    
    // Step 8: Log to governance audit trail
    await supabase.from('governance_log').insert({
      actor_id: event.proposer_id,
      action: 'create_proposal',
      resource_id: event.proposal_id,
      decision: 'ALLOW',
      reason: `Proposal created with trust score ${agent.trust_score}`,
      trace_id: event.trace_id,
      kaiju_context: {
        governance_level: event.governance_level,
        trust_threshold: threshold,
        actual_trust: agent.trust_score
      }
    })
    
    console.log(`[on_proposal_created] Proposal ${event.proposal_id} processed successfully`)
    
    return new Response(
      JSON.stringify({ 
        status: 'success',
        proposal_id: event.proposal_id,
        voting_status: 'voting',
        voting_ends_at: votingEndsAt.toISOString(),
        trust_score: agent.trust_score
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
    
  } catch (error) {
    console.error('[on_proposal_created] Error:', error)
    
    return new Response(
      JSON.stringify({ 
        error: error.message,
        status: 'error'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})