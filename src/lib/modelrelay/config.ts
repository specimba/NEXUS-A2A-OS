/**
 * ModelRelay Configuration — Provider endpoints, routing strategies, and defaults.
 * TypeScript port of the Python ModelRelay Gateway config.
 */

export interface ProviderConfig {
  id: string
  name: string
  provider: string
  baseUrl: string
  chatPath: string
  modelsPath: string
  authType: 'bearer' | 'x-api-key' | 'none'
  quotaType: 'messages' | 'tokens' | 'credits' | 'unlimited' | 'free_tier' | 'requests'
  quotaRemaining: number | string
  costPer1m: number
  latencyMs: number
  status: 'up' | 'degraded' | 'down' | 'cooldown'
  tier: number // Quality tier 0-100
  priority: number // Lower = higher priority
  isFree: boolean
  isLocal: boolean
  models?: string[]
  envKey: string // Which .env key to use
}

export const PROVIDERS: Record<string, ProviderConfig> = {
  zai: {
    id: 'zai',
    name: 'Z-AI (GLM-5.2)',
    provider: 'zai',
    baseUrl: 'https://api.z.ai',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'varies',
    costPer1m: 0.0,
    latencyMs: 250,
    status: 'up',
    tier: 95,
    priority: 1,
    isFree: true,
    isLocal: false,
    models: ['glm-5.2'],
    envKey: 'ZAI_API_KEY',
  },
  nvidia: {
    id: 'nvidia',
    name: 'NVIDIA NIM (serial governed lane)',
    provider: 'nvidia',
    baseUrl: 'https://integrate.api.nvidia.com',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'requests',
    quotaRemaining: '8 RPM serial ceiling',
    costPer1m: 0.0,
    latencyMs: 200,
    status: 'up',
    tier: 91,
    priority: 2,
    isFree: true,
    isLocal: false,
    models: [
      'minimaxai/minimax-m3',
      'nvidia/nemotron-3-ultra-550b-a55b',
      'qwen/qwen3.5-122b-a10b',
    ],
    envKey: 'NVIDIA_API_KEY',
  },
  openrouter: {
    id: 'openrouter',
    name: 'OpenRouter',
    provider: 'openrouter',
    baseUrl: 'https://openrouter.ai',
    chatPath: '/api/v1/chat/completions',
    modelsPath: '/api/v1/models',
    authType: 'bearer',
    quotaType: 'credits',
    quotaRemaining: 'varies',
    costPer1m: 0.0,
    latencyMs: 180,
    status: 'up',
    tier: 80,
    priority: 3,
    isFree: true,
    isLocal: false,
    models: [
      'nvidia/llama-3.3-nemotron-super-128k',
      'deepseek/deepseek-chat-v3-0324',
      'google/gemini-2.5-pro-preview',
    ],
    envKey: 'OPENROUTER_API_KEY',
  },
  groq: {
    id: 'groq',
    name: 'Groq',
    provider: 'groq',
    baseUrl: 'https://api.groq.com',
    chatPath: '/openai/v1/chat/completions',
    modelsPath: '/openai/v1/models',
    authType: 'bearer',
    quotaType: 'requests',
    quotaRemaining: 'free_tier',
    costPer1m: 0.5,
    latencyMs: 80,
    status: 'up',
    tier: 75,
    priority: 4,
    isFree: false,
    isLocal: false,
    models: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768'],
    envKey: 'GROQ_API_KEY',
  },
  cerebras: {
    id: 'cerebras',
    name: 'Cerebras',
    provider: 'cerebras',
    baseUrl: 'https://api.cerebras.ai',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.6,
    latencyMs: 60,
    status: 'up',
    tier: 72,
    priority: 5,
    isFree: false,
    isLocal: false,
    models: ['llama-3.3-70b', 'llama-3.1-8b'],
    envKey: 'CEREBRAS_API_KEY',
  },
  sambanova: {
    id: 'sambanova',
    name: 'SambaNova',
    provider: 'sambanova',
    baseUrl: 'https://api.sambanova.ai',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.0,
    latencyMs: 150,
    status: 'up',
    tier: 82,
    priority: 6,
    isFree: true,
    isLocal: false,
    models: ['DeepSeek-V3', 'Meta-Llama-3.3-70B-Instruct'],
    envKey: 'SAMBANOVA_API_KEY',
  },
  deepseek: {
    id: 'deepseek',
    name: 'DeepSeek',
    provider: 'deepseek',
    baseUrl: 'https://api.deepseek.com',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.5,
    latencyMs: 200,
    status: 'up',
    tier: 80,
    priority: 7,
    isFree: false,
    isLocal: false,
    models: ['deepseek-chat', 'deepseek-reasoner'],
    envKey: 'DEEPSEEK_API_KEY',
  },
  openai: {
    id: 'openai',
    name: 'OpenAI',
    provider: 'openai',
    baseUrl: 'https://api.openai.com',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'credits',
    quotaRemaining: '0_credit',
    costPer1m: 0.15,
    latencyMs: 300,
    status: 'up',
    tier: 88,
    priority: 8,
    isFree: false,
    isLocal: false,
    models: ['gpt-4o-mini'],
    envKey: 'OPENAI_API_KEY',
  },
  fireworks: {
    id: 'fireworks',
    name: 'Fireworks AI',
    provider: 'fireworks',
    baseUrl: 'https://api.fireworks.ai',
    chatPath: '/inference/v1/chat/completions',
    modelsPath: '/inference/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.2,
    latencyMs: 140,
    status: 'up',
    tier: 74,
    priority: 9,
    isFree: false,
    isLocal: false,
    models: ['llama-3.1-70b', 'qwen2.5-72b'],
    envKey: 'FIREWORKS_API_KEY',
  },
  siliconflow: {
    id: 'siliconflow',
    name: 'SiliconFlow (12 free models)',
    provider: 'siliconflow',
    baseUrl: 'https://api.siliconflow.cn',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.0,
    latencyMs: 400,
    status: 'up',
    tier: 91,
    priority: 3,
    isFree: true,
    isLocal: false,
    models: [
      'zai-org/GLM-5',
      'zai-org/GLM-5.1',
      'zai-org/GLM-4.5',
      'deepseek-ai/DeepSeek-V4-Flash',
      'deepseek-ai/DeepSeek-V4-Pro',
      'MiniMaxAI/MiniMax-M2.5',
      'MiniMaxAI/MiniMax-M2.1',
      'Qwen/Qwen3-235B-A22B',
      'Qwen/Qwen3-32B',
      'moonshotai/Kimi-K2-Thinking',
      'moonshotai/Kimi-K2.6',
      'moonshotai/Kimi-K2-Instruct',
    ],
    envKey: 'SILICONFLOW_API_KEY',
  },
  mistral: {
    id: 'mistral',
    name: 'Mistral AI',
    provider: 'mistral',
    baseUrl: 'https://api.mistral.ai',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.4,
    latencyMs: 220,
    status: 'up',
    tier: 82,
    priority: 11,
    isFree: false,
    isLocal: false,
    models: ['mistral-medium'],
    envKey: 'MISTRAL_API_KEY',
  },
  codestral: {
    id: 'codestral',
    name: 'Codestral',
    provider: 'codestral',
    baseUrl: 'https://codestral.mistral.ai',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.3,
    latencyMs: 180,
    status: 'up',
    tier: 78,
    priority: 12,
    isFree: false,
    isLocal: false,
    models: ['codestral-latest'],
    envKey: 'CODESTRAL_API_KEY',
  },
  bitdeer: {
    id: 'bitdeer',
    name: 'Bitdeer AI',
    provider: 'bitdeer',
    baseUrl: 'https://api.bitdeer.com',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'credits',
    quotaRemaining: 'varies',
    costPer1m: 0.0,
    latencyMs: 300,
    status: 'up',
    tier: 65,
    priority: 13,
    isFree: false,
    isLocal: false,
    models: ['bitdeer-default'],
    envKey: 'BITDEER_API_KEY',
  },
}

// ─── Routing Strategies ──────────────────────────────────────────────────

export interface RoutingStrategyConfig {
  description: string
  poolFilter: 'all' | 'free' | 'premium' | 'local'
  costWeight: number
  latencyWeight: number
  qualityWeight: number
  availabilityWeight: number
}

export const DEFAULT_STRATEGY = 'quota_aware'

export const ROUTING_STRATEGIES: Record<string, RoutingStrategyConfig> = {
  quota_aware: {
    description: 'Prioritize free tier, switch when quota exhausted',
    poolFilter: 'all',
    costWeight: 0.30,
    latencyWeight: 0.20,
    qualityWeight: 0.30,
    availabilityWeight: 0.20,
  },
  cost_optimized: {
    description: 'Always prefer cheapest option',
    poolFilter: 'free',
    costWeight: 0.50,
    latencyWeight: 0.15,
    qualityWeight: 0.20,
    availabilityWeight: 0.15,
  },
  quality_first: {
    description: 'Use best available model within budget',
    poolFilter: 'all',
    costWeight: 0.15,
    latencyWeight: 0.20,
    qualityWeight: 0.45,
    availabilityWeight: 0.20,
  },
  latency: {
    description: 'Minimize response time',
    poolFilter: 'all',
    costWeight: 0.10,
    latencyWeight: 0.50,
    qualityWeight: 0.25,
    availabilityWeight: 0.15,
  },
}

// ─── Intent Classification ──────────────────────────────────────────────

export type IntentCategory = 'code' | 'reasoning' | 'research' | 'speed' | 'general' | 'security'

export const INTENT_KEYWORDS: Record<IntentCategory, string[]> = {
  code: ['code', 'function', 'class', 'debug', 'fix', 'implement', 'api', 'endpoint', 'sql', 'query', 'refactor', 'test', 'deploy', 'docker', 'git', 'commit', 'bug', 'error', 'python', 'javascript', 'typescript', 'rust', 'golang'],
  reasoning: ['reasoning', 'logic', 'solve', 'plan', 'strategy', 'optimize', 'algorithm', 'tradeoff', 'decision', 'analyze', 'think', 'explain', 'reason'],
  research: ['research', 'analyze', 'study', 'paper', 'source', 'evidence', 'cite', 'literature', 'review', 'survey', 'find', 'search', 'investigate'],
  speed: ['quick', 'fast', 'summarize', 'list', 'extract', 'format', 'convert', 'translate', 'brief', 'short', 'concise', 'simple'],
  general: [],
  security: ['security', 'audit', 'vulnerability', 'auth', 'encrypt', 'permission', 'compliance', 'risk', 'threat', 'penetration', 'exploit', 'injection'],
}

// ─── Fallback Chains ─────────────────────────────────────────────────────

export const FALLBACK_CHAINS: Record<string, string[]> = {
  code: ['longcat/LongCat-2.0', 'nvidia/nvidia/nemotron-3-ultra-550b-a55b', 'siliconflow/deepseek-ai/DeepSeek-V4-Flash'],
  reasoning: ['internai/intern-s2-preview', 'nvidia/minimaxai/minimax-m3', 'siliconflow/zai-org/GLM-5.1'],
  research: ['longcat/LongCat-2.0', 'internai/intern-s2-preview', 'nvidia/qwen/qwen3.5-122b-a10b'],
  speed: ['siliconflow/deepseek-ai/DeepSeek-V4-Flash', 'groq/llama-3.3-70b-versatile', 'cerebras/llama-3.3-70b'],
  general: ['nvidia/minimaxai/minimax-m3', 'siliconflow/zai-org/GLM-5', 'openrouter/nvidia/llama-3.3-nemotron-super-128k'],
  security: ['nvidia/nvidia/nemotron-3-ultra-550b-a55b', 'internai/intern-s2-preview', 'openrouter/google/gemini-2.5-pro-preview'],
}

// ─── Model Registry ──────────────────────────────────────────────────────

export interface ModelInfo {
  modelId: string
  provider: string
  name: string
  tier: number
  costPer1mInput: number
  costPer1mOutput: number
  contextWindow: number
  latencyMsTypical: number
  supportsVision: boolean
  supportsFunctionCalling: boolean
  supportsStreaming: boolean
  isFree: boolean
  isLocal: boolean
  status: 'up' | 'degraded' | 'down'
}

export const MODELS: ModelInfo[] = [
  // ── Z-AI (Primary) ────────────────────────────────────────────────
  { modelId: 'zai/glm-5.2', provider: 'zai', name: 'GLM-5.2', tier: 99, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 300, supportsVision: true, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  // ── NVIDIA NIM (8 RPM ceiling; one request globally; no parallel retry) ──
  { modelId: 'nvidia/z-ai/glm-5.1', provider: 'nvidia', name: 'GLM-5.1 (NIM, suspended)', tier: 91, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 202752, latencyMsTypical: 2765, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'down' },
  { modelId: 'nvidia/minimaxai/minimax-m3', provider: 'nvidia', name: 'MiniMax M3 (NIM)', tier: 92, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 524288, latencyMsTypical: 4500, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'nvidia/nvidia/devstral-2-123b', provider: 'nvidia', name: 'Devstral 2 123B (NIM, suspended)', tier: 82, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 131072, latencyMsTypical: 1800, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'down' },
  { modelId: 'nvidia/moonshotai/kimi-k2-thinking', provider: 'nvidia', name: 'Kimi K2 Thinking (NIM, suspended)', tier: 93, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 262144, latencyMsTypical: 3200, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'down' },
  // ── OpenRouter Free/Low-Cost ───────────────────────────────────────
  { modelId: 'openrouter/nvidia/llama-3.3-nemotron-super-128k', provider: 'openrouter', name: 'Nemotron Super 128K', tier: 85, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 200, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'openrouter/deepseek/deepseek-chat-v3-0324', provider: 'openrouter', name: 'DeepSeek Chat V3', tier: 82, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 64000, latencyMsTypical: 180, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'openrouter/google/gemini-2.5-pro-preview', provider: 'openrouter', name: 'Gemini 2.5 Pro', tier: 97, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 1000000, latencyMsTypical: 400, supportsVision: true, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  // ── Groq ───────────────────────────────────────────────────────────
  { modelId: 'groq/llama-3.3-70b-versatile', provider: 'groq', name: 'Llama 3.3 70B (Groq)', tier: 75, costPer1mInput: 0.59, costPer1mOutput: 0.79, contextWindow: 128000, latencyMsTypical: 80, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  { modelId: 'groq/mixtral-8x7b-32768', provider: 'groq', name: 'Mixtral 8x7B (Groq)', tier: 70, costPer1mInput: 0.24, costPer1mOutput: 0.24, contextWindow: 32768, latencyMsTypical: 60, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── Cerebras ───────────────────────────────────────────────────────
  { modelId: 'cerebras/llama-3.3-70b', provider: 'cerebras', name: 'Llama 3.3 70B (Cerebras)', tier: 72, costPer1mInput: 0.6, costPer1mOutput: 0.6, contextWindow: 128000, latencyMsTypical: 40, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  { modelId: 'cerebras/llama-3.1-8b', provider: 'cerebras', name: 'Llama 3.1 8B (Cerebras)', tier: 55, costPer1mInput: 0.1, costPer1mOutput: 0.1, contextWindow: 128000, latencyMsTypical: 20, supportsVision: false, supportsFunctionCalling: false, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── SambaNova ──────────────────────────────────────────────────────
  { modelId: 'sambanova/DeepSeek-V3', provider: 'sambanova', name: 'DeepSeek V3 (SambaNova)', tier: 82, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 64000, latencyMsTypical: 150, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'sambanova/Meta-Llama-3.3-70B-Instruct', provider: 'sambanova', name: 'Llama 3.3 70B (SambaNova)', tier: 80, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 130, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  // ── DeepSeek ───────────────────────────────────────────────────────
  { modelId: 'deepseek/deepseek-chat', provider: 'deepseek', name: 'DeepSeek Chat', tier: 80, costPer1mInput: 0.27, costPer1mOutput: 1.1, contextWindow: 64000, latencyMsTypical: 200, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── OpenAI ─────────────────────────────────────────────────────────
  { modelId: 'openai/gpt-4o-mini', provider: 'openai', name: 'GPT-4o-mini', tier: 85, costPer1mInput: 0.15, costPer1mOutput: 0.6, contextWindow: 128000, latencyMsTypical: 300, supportsVision: true, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── Fireworks ──────────────────────────────────────────────────────
  { modelId: 'fireworks/llama-3.1-70b', provider: 'fireworks', name: 'Llama 3.1 70B (Fireworks)', tier: 74, costPer1mInput: 0.2, costPer1mOutput: 0.2, contextWindow: 128000, latencyMsTypical: 140, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  { modelId: 'fireworks/qwen2.5-72b', provider: 'fireworks', name: 'Qwen2.5 72B (Fireworks)', tier: 76, costPer1mInput: 0.2, costPer1mOutput: 0.2, contextWindow: 32768, latencyMsTypical: 150, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── SiliconFlow (12 free models, tier 91, key rotated 2026-06-28) ──
  { modelId: 'siliconflow/zai-org/GLM-5', provider: 'siliconflow', name: 'GLM-5 (SF)', tier: 95, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32768, latencyMsTypical: 400, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/zai-org/GLM-5.1', provider: 'siliconflow', name: 'GLM-5.1 (SF)', tier: 96, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 202752, latencyMsTypical: 450, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/deepseek-ai/DeepSeek-V4-Flash', provider: 'siliconflow', name: 'DeepSeek V4 Flash (SF)', tier: 85, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32768, latencyMsTypical: 120, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/deepseek-ai/DeepSeek-V4-Pro', provider: 'siliconflow', name: 'DeepSeek V4 Pro (SF)', tier: 90, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 65536, latencyMsTypical: 350, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/MiniMaxAI/MiniMax-M2.5', provider: 'siliconflow', name: 'MiniMax M2.5 (SF)', tier: 80, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32768, latencyMsTypical: 300, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/Qwen/Qwen3-235B-A22B', provider: 'siliconflow', name: 'Qwen3 235B MoE (SF)', tier: 88, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32768, latencyMsTypical: 500, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/moonshotai/Kimi-K2-Thinking', provider: 'siliconflow', name: 'Kimi K2 Thinking (SF)', tier: 93, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 65536, latencyMsTypical: 600, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  // ── Mistral ────────────────────────────────────────────────────────
  { modelId: 'mistral/mistral-medium', provider: 'mistral', name: 'Mistral Medium', tier: 82, costPer1mInput: 0.4, costPer1mOutput: 0.4, contextWindow: 32000, latencyMsTypical: 220, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── Codestral ──────────────────────────────────────────────────────
  { modelId: 'codestral/codestral-latest', provider: 'codestral', name: 'Codestral', tier: 78, costPer1mInput: 0.3, costPer1mOutput: 0.3, contextWindow: 32000, latencyMsTypical: 180, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  // ── Bitdeer ────────────────────────────────────────────────────────
  { modelId: 'bitdeer/bitdeer-default', provider: 'bitdeer', name: 'Bitdeer Default', tier: 65, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 8192, latencyMsTypical: 300, supportsVision: false, supportsFunctionCalling: false, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
]

// ─── Provider Health Tracking (in-memory) ────────────────────────────────

export interface ProviderHealth {
  providerId: string
  state: 'up' | 'degraded' | 'down' | 'cooldown'
  latencyMs: number
  latencyHistory: number[]
  failureCount: number
  consecutiveFailures: number
  lastSuccess: number | null
  lastFailure: number | null
  lastCheck: number | null
  cooldownUntil: number | null
}

export interface QuotaInfo {
  providerId: string
  quotaType: string
  remaining: number
  remainingStr: string
  isExhausted: boolean
  dailyLimit: number | null
  dailyUsed: number
}

// ─── Gateway Statistics ───────────────────────────────────────────────────

export interface GatewayStats {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  totalTokens: number
  totalCost: number
  startTime: number
  requestsPerMinute: number
}

// ─── Routing Result ──────────────────────────────────────────────────────

export interface RouteResult {
  requestId: string
  primaryModel: string
  fallbackChain: string[]
  provider: string
  intent: string
  strategy: string
  score: number
  estimatedLatencyMs: number
  estimatedCost: number
  reasoning: string
}

// ─── Circuit Breaker Config ──────────────────────────────────────────────

export const CIRCUIT_BREAKER_THRESHOLD = 3
export const CIRCUIT_BREAKER_COOLDOWN = 60 // seconds
export const HEALTH_CHECK_INTERVAL = 60 // seconds
export const LATENCY_SAMPLE_SIZE = 5
