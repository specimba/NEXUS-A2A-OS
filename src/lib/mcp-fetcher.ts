// Hardened fetcher for MCP Hub panels.
//
// SWR's default behavior treats any successful fetch (including a 500 with a
// JSON body) as data — so panels were rendering `{error: "..."}` as an array
// and crashing on `.map()` / `.filter()`. This fetcher:
//   1. Throws on non-OK so SWR's `error` channel triggers properly.
//   2. Tolerates non-JSON error bodies (e.g. HTML 500 pages from Next).
//
// The exported `safeArray` helper is for sites that destructure SWR data with
// a default value: if the server returns an object on error and SWR is in a
// "keep last" state, we still want to render an empty list instead of crashing.

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `Request failed (${status})`)
    this.status = status
    this.body = body
  }
}

export async function jsonFetcher<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: 'no-store' })
  const text = await res.text()
  let parsed: unknown = undefined
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      // Server returned non-JSON (e.g. Next dev error page) — treat as raw text.
      parsed = { error: text.slice(0, 500) }
    }
  }
  if (!res.ok) {
    const msg =
      typeof parsed === 'object' && parsed && 'error' in parsed
        ? String((parsed as { error: unknown }).error)
        : `Request failed (${res.status})`
    throw new ApiError(res.status, parsed, msg)
  }
  return (parsed as T) ?? (undefined as T)
}

// Coerce anything that isn't an array to an empty array. Useful when defaulting
// SWR data because an HTTP error response may transiently be `{error: "..."}`.
export function safeArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}
