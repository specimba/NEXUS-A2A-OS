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
    name: 'Z-AI (GLM-4.7)',
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
    models: ['glm-4-7', 'glm-5'],
    envKey: 'ZAI_API_KEY',
  },
  nvidia: {
    id: 'nvidia',
    name: 'NVIDIA NIM',
    provider: 'nvidia',
    baseUrl: 'https://integrate.api.nvidia.com',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'varies',
    costPer1m: 0.0,
    latencyMs: 200,
    status: 'up',
    tier: 90,
    priority: 2,
    isFree: true,
    isLocal: false,
    models: [
      'nemotron-4-340b-instruct',
      'llama-3.1-405b-instruct',
      'mistral-large',
      'llama-3.3-70b-instruct',
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
    name: 'SiliconFlow',
    provider: 'siliconflow',
    baseUrl: 'https://api.siliconflow.cn',
    chatPath: '/v1/chat/completions',
    modelsPath: '/v1/models',
    authType: 'bearer',
    quotaType: 'free_tier',
    quotaRemaining: 'free_tier',
    costPer1m: 0.3,
    latencyMs: 180,
    status: 'up',
    tier: 70,
    priority: 10,
    isFree: false,
    isLocal: false,
    models: ['deepseek-v3', 'qwen2.5-72b'],
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
  code: ['zai/glm-4-7', 'nvidia/llama-3.3-70b-instruct', 'openrouter/deepseek-chat-v3-0324', 'codestral/codestral-latest'],
  reasoning: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'openrouter/google/gemini-2.5-pro-preview', 'sambanova/DeepSeek-V3'],
  research: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'openrouter/nvidia/llama-3.3-nemotron-super-128k'],
  speed: ['groq/llama-3.3-70b-versatile', 'cerebras/llama-3.3-70b', 'groq/mixtral-8x7b-32768'],
  general: ['zai/glm-4-7', 'openrouter/nvidia/llama-3.3-nemotron-super-128k', 'groq/llama-3.3-70b-versatile'],
  security: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'sambanova/DeepSeek-V3'],
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
  { modelId: 'zai/glm-4-7', provider: 'zai', name: 'GLM-4.7', tier: 95, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 250, supportsVision: true, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'zai/glm-5', provider: 'zai', name: 'GLM-5', tier: 99, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 300, supportsVision: true, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  // ── NVIDIA NIM ─────────────────────────────────────────────────────
  { modelId: 'nvidia/nemotron-4-340b-instruct', provider: 'nvidia', name: 'Nemotron-4 340B', tier: 90, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 4096, latencyMsTypical: 200, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'nvidia/llama-3.1-405b-instruct', provider: 'nvidia', name: 'Llama 3.1 405B', tier: 88, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 4096, latencyMsTypical: 220, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'nvidia/llama-3.3-70b-instruct', provider: 'nvidia', name: 'Llama 3.3 70B', tier: 85, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 4096, latencyMsTypical: 180, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
  { modelId: 'nvidia/mistral-large', provider: 'nvidia', name: 'Mistral Large (NIM)', tier: 85, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32000, latencyMsTypical: 200, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: true, isLocal: false, status: 'up' },
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
  // ── SiliconFlow ────────────────────────────────────────────────────
  { modelId: 'siliconflow/deepseek-v3', provider: 'siliconflow', name: 'DeepSeek V3 (SiliconFlow)', tier: 70, costPer1mInput: 0.3, costPer1mOutput: 0.3, contextWindow: 64000, latencyMsTypical: 180, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
  { modelId: 'siliconflow/qwen2.5-72b', provider: 'siliconflow', name: 'Qwen2.5 72B (SiliconFlow)', tier: 72, costPer1mInput: 0.3, costPer1mOutput: 0.3, contextWindow: 32768, latencyMsTypical: 190, supportsVision: false, supportsFunctionCalling: true, supportsStreaming: true, isFree: false, isLocal: false, status: 'up' },
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
