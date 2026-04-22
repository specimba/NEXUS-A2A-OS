'use client'

import { useSyncExternalStore } from 'react'

/**
 * Hook to detect if the component is mounted on the client.
 * Uses useSyncExternalStore to avoid hydration mismatches.
 *
 * Returns `false` during SSR and `true` after mount.
 */
const emptySubscribe = () => () => {}

export function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,  // client snapshot
    () => false  // server snapshot
  )
}
