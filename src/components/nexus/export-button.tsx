'use client'

import { Download, FileJson, FileSpreadsheet } from 'lucide-react'
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
}

function flattenObject(obj: Record<string, unknown>, prefix = ''): Record<string, string> {
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(result, flattenObject(value as Record<string, unknown>, newKey))
    } else if (Array.isArray(value)) {
      result[newKey] = JSON.stringify(value)
    } else {
      result[newKey] = String(value ?? '')
    }
  }
  return result
}

function toCSV(data: Record<string, unknown>[]): string {
  if (!data.length) return ''
  const flat = data.map((row) => flattenObject(row))
  const headers = Object.keys(flat[0])
  const escape = (val: string) => {
    if (val.includes(',') || val.includes('"') || val.includes('\n')) {
      return `"${val.replace(/"/g, '""')}"`
    }
    return val
  }
  const headerRow = headers.map(escape).join(',')
  const rows = flat.map((row) =>
    headers.map((h) => escape(row[h] || '')).join(',')
  )
  return [headerRow, ...rows].join('\n')
}

function downloadFile(content: string, filename: string, mimeType: string) {
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

export function ExportButton({ data, filename, label = 'Export' }: ExportButtonProps) {
  const exportCSV = () => {
    const csv = toCSV(data)
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
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-xs text-muted-foreground hover:text-foreground">
          <Download className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{label}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuItem onClick={exportCSV} className="gap-2 text-xs cursor-pointer">
          <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportJSON} className="gap-2 text-xs cursor-pointer">
          <FileJson className="h-3.5 w-3.5 text-blue-400" />
          Export as JSON
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
