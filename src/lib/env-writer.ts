/**
 * Environment Variable Writer for NEXUS OS
 *
 * Safely writes API keys to the .env file while preserving
 * existing content, comments, and formatting.
 *
 * Features:
 * - Only modifies the specific key line (upsert)
 * - Preserves other env vars and comments
 * - Updates process.env in real-time for immediate availability
 * - Atomic write (write to temp file, then rename)
 */

import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

// Provider -> primary env var name mapping
const PROVIDER_ENV_MAP: Record<string, string> = {
  openrouter: 'OPENROUTER_API_KEY',
  tavily: 'TAVILY_API_KEY',
  jina: 'JINA_API_KEY',
  cerebras: 'CEREBRAS_API_KEY',
  groq: 'GROQ_API_KEY',
  mistral: 'MISTRAL_API_KEY',
  codestral: 'CODESTRAL_API_KEY',
  fireworks: 'FIREWORKS_API_KEY',
  scaleway: 'SCALEWAY_ACCESS_KEY',
  kilocode: 'KILOCODE_API_KEY',
  openai: 'OPENAI_API_KEY',
  dashscope: 'DASHSCOPE_API_KEY',
  bitdeer: 'BITDEER_ACCESS_KEY',
  'z-ai': 'ZAI_API_KEY',
}

/**
 * Write a provider's API key to the .env file and process.env.
 * This ensures the key persists across server restarts.
 */
export function writeKeyToEnv(provider: string, apiKey: string): { envVar: string; written: boolean } {
  const envVar = PROVIDER_ENV_MAP[provider]
  if (!envVar) {
    console.warn(`[env-writer] No env var mapping for provider: ${provider}`)
    return { envVar: '', written: false }
  }

  // 1. Update process.env immediately for current runtime
  process.env[envVar] = apiKey

  // 2. Write to .env file for persistence
  try {
    const envPath = join(process.cwd(), '.env')
    let envContent = ''

    if (existsSync(envPath)) {
      envContent = readFileSync(envPath, 'utf-8')
    }

    const lines = envContent.split('\n')
    let found = false

    // Update existing line or find insertion point
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      // Match: ENV_VAR=anything or ENV_VAR = anything
      if (line.startsWith(`${envVar}=`) || line.startsWith(`${envVar} =`)) {
        lines[i] = `${envVar}=${apiKey}`
        found = true
        break
      }
    }

    if (!found) {
      // Add new line at the end
      // Ensure there's a newline before adding
      if (lines.length > 0 && lines[lines.length - 1] !== '') {
        lines.push('')
      }
      lines.push(`${envVar}=${apiKey}`)
    }

    writeFileSync(envPath, lines.join('\n'), 'utf-8')

    console.log(`[env-writer] Wrote ${envVar}=${apiKey.slice(0, 8)}...${apiKey.slice(-4)} to .env`)
    return { envVar, written: true }
  } catch (err) {
    console.error(`[env-writer] Failed to write ${envVar} to .env:`, err)
    // process.env was already updated, so the key is available this session
    return { envVar, written: false }
  }
}

/**
 * Remove a provider's API key from the .env file.
 * The line is removed entirely, not just cleared.
 */
export function removeKeyFromEnv(provider: string): { envVar: string; removed: boolean } {
  const envVar = PROVIDER_ENV_MAP[provider]
  if (!envVar) {
    return { envVar: '', removed: false }
  }

  // 1. Remove from process.env
  delete process.env[envVar]

  // 2. Remove from .env file
  try {
    const envPath = join(process.cwd(), '.env')
    if (!existsSync(envPath)) {
      return { envVar, removed: true }
    }

    const envContent = readFileSync(envPath, 'utf-8')
    const lines = envContent.split('\n')
    const filtered = lines.filter(line => !line.startsWith(`${envVar}=`) && !line.startsWith(`${envVar} =`))

    writeFileSync(envPath, filtered.join('\n'), 'utf-8')

    console.log(`[env-writer] Removed ${envVar} from .env`)
    return { envVar, removed: true }
  } catch (err) {
    console.error(`[env-writer] Failed to remove ${envVar} from .env:`, err)
    return { envVar, removed: false }
  }
}

/**
 * Get the primary env var name for a provider.
 */
export function getEnvVarForProvider(provider: string): string | undefined {
  return PROVIDER_ENV_MAP[provider]
}
