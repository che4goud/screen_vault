import type { SearchResponse, SummaryResponse, OrganiseResponse } from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// Phase 1: user id passed as header — replaced with JWT in Phase 3
const USER_ID = process.env.NEXT_PUBLIC_USER_ID ?? "dev-user-001"

export async function getAllScreenshots(page = 1): Promise<SearchResponse> {
  const params = new URLSearchParams({ page: String(page) })
  const res = await fetch(`${BASE_URL}/screenshots?${params}`, {
    headers: { "X-User-Id": USER_ID },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to load screenshots: ${res.status}`)
  }
  return res.json()
}

export async function searchScreenshots(
  query: string,
  page = 1,
  filters?: { dateFrom?: string; dateTo?: string; tag?: string }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, page: String(page) })
  if (filters?.dateFrom) params.set("date_from", filters.dateFrom)
  if (filters?.dateTo) params.set("date_to", filters.dateTo)
  if (filters?.tag) params.set("tag", filters.tag)

  const res = await fetch(`${BASE_URL}/search?${params}`, {
    headers: { "X-User-Id": USER_ID },
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Search failed: ${res.status}`)
  }

  return res.json()
}

export async function fetchSummary(query: string): Promise<SummaryResponse> {
  const params = new URLSearchParams({ q: query })
  const res = await fetch(`${BASE_URL}/summary?${params}`, {
    headers: { "X-User-Id": USER_ID },
  })
  if (!res.ok) return { summary: "" }
  return res.json()
}

export async function fetchOrganised(): Promise<OrganiseResponse> {
  const res = await fetch(`${BASE_URL}/organise`, {
    headers: { "X-User-Id": USER_ID },
  })
  if (!res.ok) return { clusters: [] }
  return res.json()
}

export async function syncScreenshots(): Promise<{ queued: number; skipped: number }> {
  const res = await fetch(`${BASE_URL}/sync`, {
    method: "POST",
    headers: { "X-User-Id": USER_ID },
  })
  if (!res.ok) return { queued: 0, skipped: 0 }
  return res.json()
}

export function thumbnailUrl(path: string | null): string {
  if (!path) return "/placeholder.png"
  // Backend serves thumbnails at /thumbnails/<filename>
  const filename = path.split("/").pop()
  return `${BASE_URL}/thumbnails/${filename}`
}

export function parseTags(raw: string): string[] {
  try {
    return JSON.parse(raw) ?? []
  } catch {
    return []
  }
}
