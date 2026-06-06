'use client'

import { useState, useEffect } from 'react'
import { DashboardList } from '../dashboards/dashboard-list'
import { DashboardEditor } from '../dashboards/dashboard-editor'

export function DashboardsTab() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // Honor ?dashboard=<id> deep-link on first mount
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const id = params.get('dashboard')
    if (id) setSelectedId(id)
  }, [])

  if (selectedId) {
    return (
      <DashboardEditor
        dashboardId={selectedId}
        onBack={() => {
          setSelectedId(null)
          if (typeof window !== 'undefined') {
            const url = new URL(window.location.href)
            url.searchParams.delete('dashboard')
            window.history.replaceState({}, '', url.toString())
          }
        }}
      />
    )
  }

  return (
    <DashboardList
      onOpen={(id) => {
        setSelectedId(id)
        if (typeof window !== 'undefined') {
          const url = new URL(window.location.href)
          url.searchParams.set('dashboard', id)
          window.history.replaceState({}, '', url.toString())
        }
      }}
    />
  )
}
