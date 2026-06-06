'use client'

import { useEffect } from 'react'
import posthog from 'posthog-js'

// Lightweight env-gated PostHog initializer. If NEXT_PUBLIC_POSTHOG_KEY is not
// set the provider becomes a no-op so the app still ships without analytics.
// Place this near the top of the layout tree (e.g. in app/layout.tsx).
export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
    if (!key) return
    if (typeof window === 'undefined') return
    if ((posthog as unknown as { __loaded?: boolean }).__loaded) return

    posthog.init(key, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
      person_profiles: 'identified_only',
      capture_pageview: true,
      capture_pageleave: true,
      autocapture: true,
    })
  }, [])

  return <>{children}</>
}

// Convenience tracker used across the MCP hub. Safely no-ops when PostHog is
// not initialized.
export function trackEvent(event: string, properties?: Record<string, unknown>) {
  try {
    if (typeof window === 'undefined') return
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
    posthog.capture(event, properties)
  } catch {
    /* swallow */
  }
}

// Read a feature flag value (boolean / variant). Returns undefined when
// PostHog isn't configured.
export function useFeatureFlag(flagKey: string): boolean | string | undefined {
  if (typeof window === 'undefined') return undefined
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return undefined
  try {
    return posthog.getFeatureFlag(flagKey)
  } catch {
    return undefined
  }
}
