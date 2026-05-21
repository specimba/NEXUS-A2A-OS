import type { WidgetType } from './widget-catalog'

export interface CustomWidgetDTO {
  id: string
  dashboardId: string
  type: string         // WidgetType, but db stores as string
  title: string
  subtitle: string | null
  dataSource: string
  config: string       // JSON-stringified config
  posX: number
  posY: number
  width: number
  height: number
  createdAt: string
  updatedAt: string
}

export interface CustomDashboardDTO {
  id: string
  name: string
  description: string | null
  ownerId: string
  ownerName: string
  icon: string
  color: string
  isFavorite: boolean
  isPinned: boolean
  sharedWith: string   // JSON: SharedMember[]
  tags: string         // JSON: string[]
  lastViewed: string
  createdAt: string
  updatedAt: string
  widgets: CustomWidgetDTO[]
}

export interface SharedMember {
  id: string
  name: string
  role: 'viewer' | 'editor'
  avatar?: string
}

export function parseSharedWith(raw: string): SharedMember[] {
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function parseTags(raw: string): string[] {
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function parseConfig(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

export type { WidgetType }
