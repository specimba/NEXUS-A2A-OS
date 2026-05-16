/**
 * Supabase Edge Function: execute_approved_proposal
 * Purpose: Execute proposals that have reached consensus
 * Triggers: Called when a proposal's voting period ends or consensus is reached
 * 
 * This function:
 * 1. Calculates weighted voting results
 * 2. Checks if consensus threshold is met
 * 3. Executes the proposed action if approved
 * 4. Adjusts trust scores based on outcome
 * 5. Logs all actions to audit trail
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface ExecutionRequest {
  proposal_id: string
  force_execute?: boolean  // Skip consensus check if true (admin override)
}

interface ProposalAction {
  type: string  // 'code', 'configuration', 'resource', 'system', etc.
  target: string
  parameters: Record<string, unknown>
}

serve(async (req) => {
  try {
    // Parse request body
    const request: ExecutionRequest = await req.json()
    const { proposal_id, force_execute = false } = request
    
    console.log(`[execute_approved_proposal] Processing proposal ${proposal_id}`)
    
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)
    
    // Step 1: Fetch proposal with current voting status
    const { data: proposal, error: proposalError } = await supabase
      .from('proposals')
      .select(`
        *,
        proposer:agents(id, name, trust_score, status),
        votes:proposal_votes(
          id,
          agent_id,
          vote_type,
          vote_weight,
          reasoning,
          agent:agents(id, name, trust_score)
        )
      `)
      .eq('id', proposal_id)
      .single()
    
    if (proposalError || !proposal) {
      throw new Error(`Proposal not found: ${proposal_id}`)
    }
    
    console.log(`[execute_approved_proposal] Proposal status: ${proposal.status}`)
    
    // Check if proposal is in executable state
    if (proposal.status !== 'voting' && !force_execute) {
      return new Response(
        JSON.stringify({ 
          error: `Proposal not in voting state: ${proposal.status}`,
          proposal_id: proposal_id
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Step 2: Calculate consensus
    const weightedApprovals = proposal.votes
      .filter((v: any) => v.vote_type === 'approve')
      .reduce((sum: number, v: any) => sum + (v.vote_weight || v.agent?.trust_score || 0), 0)
    
    const totalWeight = proposal.votes
      .reduce((sum: number, v: any) => sum + (v.vote_weight || v.agent?.trust_score || 0), 0)
    
    const approvalRatio = totalWeight > 0 ? weightedApprovals / totalWeight : 0
    
    // Consensus thresholds based on governance level
    const consensusThresholds = {
      'standard': 0.50,    // Simple majority
      'elevated': 0.66,    // Super majority
      'critical': 0.75     // Very high consensus
    }
    
    const threshold = consensusThresholds[proposal.governance_level] || 0.50
    const hasConsensus = approvalRatio >= threshold || force_execute
    
    console.log(`[execute_approved_proposal] Voting results: ${approvalRatio.toFixed(2)}/${threshold} (consensus: ${hasConsensus})`)
    
    // Step 3: If no consensus, reject proposal
    if (!hasConsensus) {
      await supabase
        .from('proposals')
        .update({ 
          status: 'rejected',
          execution_result: {
            error: `Consensus not reached: ${approvalRatio.toFixed(2)} < ${threshold}`,
            weighted_approvals: weightedApprovals,
            total_weight: totalWeight,
            approval_ratio: approvalRatio
          }
        })
        .eq('id', proposal_id)
      
      // Penalize proposer for rejected proposal
      await supabase.rpc('decrement_agent_trust', {
        p_agent_ids: [proposal.proposer_id],
        p_delta: 5.0  // Moderate penalty
      })
      
      // Log trust event
      await supabase.from('trust_events').insert({
        agent_id: proposal.proposer_id,
        event_type: 'proposal_rejected',
        delta: -5.0,
        reason: `Proposal rejected: insufficient consensus (${approvalRatio.toFixed(2)} < ${threshold})`,
        metadata: {
          proposal_id: proposal_id,
          approval_ratio: approvalRatio,
          threshold: threshold
        }
      })
      
      return new Response(
        JSON.stringify({ 
          status: 'rejected',
          reason: 'Consensus not reached',
          approval_ratio: approvalRatio,
          threshold: threshold
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Step 4: Execute the proposed action
    const action: ProposalAction = proposal.proposed_action as ProposalAction
    let executionResult: any = { success: false }
    
    try {
      executionResult = await executeAction(action)
      
      if (executionResult.success) {
        // Update proposal as executed
        await supabase
          .from('proposals')
          .update({ 
            status: 'executed',
            executed_at: new Date().toISOString(),
            execution_result: executionResult
          })
          .eq('id', proposal_id)
        
        // Reward proposer for successful execution
        await supabase.rpc('increment_agent_trust', {
          p_agent_ids: [proposal.proposer_id],
          p_delta: 3.0  // Moderate reward
        })
        
        // Reward voters who approved
        const approvingAgents = proposal.votes
          .filter((v: any) => v.vote_type === 'approve')
          .map((v: any) => v.agent_id)
        
        if (approvingAgents.length > 0) {
          await supabase.rpc('increment_agent_trust', {
            p_agent_ids: approvingAgents,
            p_delta: 1.0  // Small reward for correct judgment
          })
        }
        
        // Log success trust event
        await supabase.from('trust_events').insert({
          agent_id: proposal.proposer_id,
          event_type: 'proposal_executed',
          delta: 3.0,
          reason: 'Proposal executed successfully',
          metadata: {
            proposal_id: proposal_id,
            action_type: action.type,
            result: executionResult
          }
        })
        
      } else {
        throw new Error(executionResult.error || 'Execution failed')
      }
      
    } catch (executionError) {
      console.error('[execute_approved_proposal] Execution error:', executionError)
      
      // Mark proposal as failed
      await supabase
        .from('proposals')
        .update({ 
          status: 'failed',
          executed_at: new Date().toISOString(),
          execution_result: {
            success: false,
            error: executionError.message
          }
        })
        .eq('id', proposal_id)
      
      // Penalize proposer for failed execution
      await supabase.rpc('decrement_agent_trust', {
        p_agent_ids: [proposal.proposer_id],
        p_delta: 10.0  // Significant penalty for failed execution
      })
      
      // Log failure trust event
      await supabase.from('trust_events').insert({
        agent_id: proposal.proposer_id,
        event_type: 'proposal_failed',
        delta: -10.0,
        reason: `Proposal execution failed: ${executionError.message}`,
        metadata: {
          proposal_id: proposal_id,
          action_type: action.type,
          error: executionError.message
        }
      })
      
      return new Response(
        JSON.stringify({ 
          status: 'failed',
          error: executionError.message
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Step 5: Notify external systems
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
            topic: 'nexus-proposals-executed',
            records: [{
              key: proposal_id,
              value: JSON.stringify({
                proposal_id: proposal_id,
                status: 'executed',
                execution_result: executionResult,
                approval_ratio: approvalRatio,
                executed_at: new Date().toISOString()
              })
            }]
          })
        })
      } catch (kafkaError) {
        console.error('[execute_approved_proposal] Kafka publish failed:', kafkaError)
      }
    }
    
    console.log(`[execute_approved_proposal] Proposal ${proposal_id} executed successfully`)
    
    return new Response(
      JSON.stringify({ 
        status: 'executed',
        proposal_id: proposal_id,
        execution_result: executionResult,
        approval_ratio: approvalRatio
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
    
  } catch (error) {
    console.error('[execute_approved_proposal] Error:', error)
    
    return new Response(
      JSON.stringify({ 
        error: error.message,
        status: 'error'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

// Action executor function
async function executeAction(action: ProposalAction): Promise<any> {
  console.log(`[executeAction] Executing ${action.type} on ${action.target}`)
  
  // In a real implementation, this would delegate to appropriate executors
  // For now, we simulate execution based on action type
  
  switch (action.type) {
    case 'configuration':
      return await executeConfigurationChange(action)
    
    case 'code':
      return await executeCodeAction(action)
    
    case 'resource':
      return await executeResourceAction(action)
    
    case 'system':
      return await executeSystemAction(action)
    
    default:
      return {
        success: false,
        error: `Unknown action type: ${action.type}`
      }
  }
}

async function executeConfigurationChange(action: ProposalAction): Promise<any> {
  // Simulate configuration change
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  return {
    success: true,
    message: `Configuration updated for ${action.target}`,
    changes: action.parameters
  }
}

async function executeCodeAction(action: ProposalAction): Promise<any> {
  // Simulate code execution
  await new Promise(resolve => setTimeout(resolve, 2000))
  
  return {
    success: true,
    message: `Code executed on ${action.target}`,
    output: `Action completed with parameters: ${JSON.stringify(action.parameters)}`
  }
}

async function executeResourceAction(action: ProposalAction): Promise<any> {
  // Simulate resource action
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  return {
    success: true,
    message: `Resource ${action.target} modified`,
    changes: action.parameters
  }
}

async function executeSystemAction(action: ProposalAction): Promise<any> {
  // Simulate system action
  await new Promise(resolve => setTimeout(resolve, 500))
  
  return {
    success: true,
    message: `System action executed: ${action.target}`,
    parameters: action.parameters
  }
}