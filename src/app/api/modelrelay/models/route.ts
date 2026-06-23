import { NextResponse } from 'next/server'

const MODELS = [
  // Reasoning tier
  { id: 'glm-5-2', name: 'GLM-5.2', provider: 'z-ai', tier: 'reasoning', contextWindow: 128000, isFree: true, health: 'healthy', latencyMs: 12 },
  { id: 'deepseek-r1-free', name: 'DeepSeek R1 Free', provider: 'openrouter', tier: 'reasoning', contextWindow: 64000, isFree: true, health: 'healthy', latencyMs: 180 },
  { id: 'qwen3-coder', name: 'Qwen3 Coder', provider: 'openrouter', tier: 'reasoning', contextWindow: 128000, isFree: true, health: 'healthy', latencyMs: 195 },
  { id: 'trinity-large', name: 'Trinity Large', provider: 'openrouter', tier: 'reasoning', contextWindow: 96000, isFree: true, health: 'healthy', latencyMs: 210 },
  { id: 'deepseek-v3', name: 'DeepSeek V3', provider: 'bitdeer', tier: 'reasoning', contextWindow: 64000, isFree: true, health: 'degraded', latencyMs: 410 },
  { id: 'o3-mini-free', name: 'O3 Mini Free', provider: 'openrouter', tier: 'reasoning', contextWindow: 32000, isFree: true, health: 'healthy', latencyMs: 250 },
  // Balanced tier
  { id: 'llama4-maverick', name: 'Llama 4 Maverick', provider: 'openrouter', tier: 'balanced', contextWindow: 128000, isFree: true, health: 'healthy', latencyMs: 170 },
  { id: 'gemma-3-27b', name: 'Gemma 3 27B', provider: 'openrouter', tier: 'balanced', contextWindow: 96000, isFree: true, health: 'healthy', latencyMs: 160 },
  { id: 'mistral-small', name: 'Mistral Small', provider: 'mistral', tier: 'balanced', contextWindow: 32000, isFree: true, health: 'degraded', latencyMs: 320 },
  { id: 'llama3.3-70b', name: 'Llama 3.3 70B', provider: 'cerebras', tier: 'balanced', contextWindow: 128000, isFree: true, health: 'healthy', latencyMs: 45 },
  { id: 'fireworks-llama3.1', name: 'Llama 3.1 70B', provider: 'fireworks', tier: 'balanced', contextWindow: 128000, isFree: true, health: 'healthy', latencyMs: 95 },
  { id: 'qwen2.5-72b-instruct', name: 'Qwen 2.5 72B', provider: 'dashscope', tier: 'balanced', contextWindow: 128000, isFree: true, health: 'unknown', latencyMs: 0 },
  // Fast tier
  { id: 'qwen3-8b-cerebras', name: 'Qwen3 8B', provider: 'cerebras', tier: 'fast', contextWindow: 32000, isFree: true, health: 'healthy', latencyMs: 35 },
  { id: 'llama3.1-8b-groq', name: 'Llama 3.1 8B', provider: 'groq', tier: 'fast', contextWindow: 32000, isFree: true, health: 'healthy', latencyMs: 38 },
  { id: 'mixtral-8x7b-groq', name: 'Mixtral 8x7B', provider: 'groq', tier: 'fast', contextWindow: 32000, isFree: true, health: 'healthy', latencyMs: 42 },
  { id: 'gemma2-9b-groq', name: 'Gemma 2 9B', provider: 'groq', tier: 'fast', contextWindow: 16000, isFree: true, health: 'healthy', latencyMs: 28 },
  { id: 'fireworks-qwen2.5', name: 'Qwen 2.5 72B Fast', provider: 'fireworks', tier: 'fast', contextWindow: 32000, isFree: true, health: 'healthy', latencyMs: 88 },
  { id: 'sambanova-llama3.1', name: 'Llama 3.1 8B SN', provider: 'sambanova', tier: 'fast', contextWindow: 16000, isFree: true, health: 'unknown', latencyMs: 0 },
  { id: 'siliconflow-qwen3', name: 'Qwen3 8B SF', provider: 'siliconflow', tier: 'fast', contextWindow: 16000, isFree: true, health: 'unknown', latencyMs: 0 },
  // Free tier
  { id: 'phi-4-free', name: 'Phi-4 Free', provider: 'openrouter', tier: 'free', contextWindow: 16000, isFree: true, health: 'healthy', latencyMs: 150 },
  { id: 'gemma-fast', name: 'Gemma Fast', provider: 'openrouter', tier: 'free', contextWindow: 8000, isFree: true, health: 'healthy', latencyMs: 120 },
  { id: 'codestral-free', name: 'Codestral Free', provider: 'codestral', tier: 'free', contextWindow: 32000, isFree: true, health: 'unknown', latencyMs: 0 },
  { id: 'nvidia-llama3.1', name: 'Llama 3.1 8B NIM', provider: 'nvidia', tier: 'free', contextWindow: 16000, isFree: true, health: 'unknown', latencyMs: 0 },
  { id: 'opencode-qwen3', name: 'Qwen3 Coder OC', provider: 'opencode', tier: 'free', contextWindow: 16000, isFree: true, health: 'unknown', latencyMs: 0 },
]

export async function GET() {
  return NextResponse.json({ models: MODELS, total: MODELS.length })
}

