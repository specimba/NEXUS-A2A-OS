'use client'

import { Download, FileJson, FileSpreadsheet, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { toast } from 'sonner'

interface ExportButtonProps {
  data: Record<string, unknown>[]
  filename: string
  label?: string
  /** Map of original key → display header name for CSV export */
  columnHeaders?: Record<string, string>
}

/** Flatten nested objects for CSV serialization */
export function flattenObject(obj: Record<string, unknown>, prefix = ''): Record<string, string> {
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(result, flattenObject(value as Record<string, unknown>, newKey))
    } else if (Array.isArray(value)) {
      result[newKey] = JSON.stringify(value)
    } else {
      result[newKey] = formatValue(value, newKey)
    }
  }
  return result
}

/** Auto-format dates and numbers for readability */
function formatValue(value: unknown, key: string): string {
  if (value === null || value === undefined) return ''

  // Auto-format date-like values
  if (value instanceof Date) {
    return value.toISOString()
  }

  // Auto-detect ISO date strings
  if (typeof value === 'string') {
    const isoMatch = value.match(/^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?/)
    if (isoMatch) {
      try {
        const d = new Date(value)
        if (!isNaN(d.getTime())) {
          return d.toLocaleString()
        }
      } catch {
        // Not a valid date, return as-is
      }
    }
  }

  // Format numbers with locale
  if (typeof value === 'number') {
    // Check if key suggests a percentage
    const keyLower = key.toLowerCase()
    if (keyLower.includes('rate') || keyLower.includes('percent') || keyLower.includes('pct')) {
      return `${value}%`
    }
    // Check if key suggests a token count or large number
    if (keyLower.includes('token') || keyLower.includes('count') || Math.abs(value) >= 1000) {
      return value.toLocaleString()
    }
    // Trust scores and similar decimals
    if (value > 0 && value < 1 && keyLower.includes('trust')) {
      return value.toFixed(2)
    }
    return String(value)
  }

  return String(value)
}

/** Convert array of objects to CSV string with optional custom headers */
export function toCSV(data: Record<string, unknown>[], columnHeaders?: Record<string, string>): string {
  if (!data.length) return ''
  const flat = data.map((row) => flattenObject(row))
  const rawHeaders = Object.keys(flat[0])
  // Apply custom column headers if provided
  const displayHeaders = rawHeaders.map((h) => columnHeaders?.[h] || h)
  const escape = (val: string) => {
    if (val.includes(',') || val.includes('"') || val.includes('\n')) {
      return `"${val.replace(/"/g, '""')}"`
    }
    return val
  }
  const headerRow = displayHeaders.map(escape).join(',')
  const rows = flat.map((row) =>
    rawHeaders.map((h) => escape(row[h] || '')).join(',')
  )
  return [headerRow, ...rows].join('\n')
}

/** Trigger a file download in the browser */
export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function ExportButton({ data, filename, label = 'Export', columnHeaders }: ExportButtonProps) {
  const exportCSV = () => {
    const csv = toCSV(data, columnHeaders)
    downloadFile(csv, `${filename}.csv`, 'text/csv;charset=utf-8;')
    toast.success(`Exported ${data.length} rows as CSV`, {
      description: `File: ${filename}.csv`,
    })
  }

  const exportJSON = () => {
    const json = JSON.stringify(data, null, 2)
    downloadFile(json, `${filename}.json`, 'application/json;charset=utf-8;')
    toast.success(`Exported ${data.length} rows as JSON`, {
      description: `File: ${filename}.json`,
    })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground">
          <Download className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{label}</span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuItem onClick={exportCSV} className="gap-2 text-xs cursor-pointer">
          <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportJSON} className="gap-2 text-xs cursor-pointer">
          <FileJson className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          Export as JSON
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
