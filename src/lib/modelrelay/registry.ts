/**
 * Registry facade — the tables the gateway routes with.
 *
 * Generated tables (from config/models.registry.json, the canonical
 * key-free registry) are merged OVER the legacy hand-authored config.ts:
 * generated entries win; legacy providers/models absent from the registry
 * are preserved so no routing capability is lost while config.ts is
 * retired. Providers the registry marks deprecated (e.g. the dead keyless
 * zai block) are dropped from the legacy side entirely.
 *
 * Do not import PROVIDERS/MODELS from './config' in new code — import
 * them from here.
 */
import {
  PROVIDERS as LEGACY_PROVIDERS,
  MODELS as LEGACY_MODELS,
  type ProviderConfig,
  type ModelInfo,
} from './config'
import {
  PROVIDERS_GENERATED,
  MODELS_GENERATED,
  DEPRECATED_PROVIDERS,
  REGISTRY_VERSION,
} from './config.generated'

const deprecated = new Set(DEPRECATED_PROVIDERS)

const legacyProviders: Record<string, ProviderConfig> = Object.fromEntries(
  Object.entries(LEGACY_PROVIDERS).filter(([id]) => !deprecated.has(id)),
)

export const PROVIDERS: Record<string, ProviderConfig> = {
  ...legacyProviders,
  ...PROVIDERS_GENERATED,
}

const generatedIds = new Set(MODELS_GENERATED.map((m) => m.modelId))

export const MODELS: ModelInfo[] = [
  ...MODELS_GENERATED,
  ...LEGACY_MODELS.filter(
    (m) => !generatedIds.has(m.modelId) && !deprecated.has(m.provider),
  ),
]

export { REGISTRY_VERSION }
