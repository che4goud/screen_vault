export interface Screenshot {
  id: number
  filename: string
  filepath: string
  thumbnail: string | null
  captured_at: string
  description: string
  ocr_text?: string
  tags: string // JSON array string e.g. '["invoice","finance"]'
  snippet?: string // highlighted FTS5 snippet (legacy)
  rank?: number    // FTS5 BM25 rank (legacy)
  score?: number   // cosine similarity score 0-1
}

export interface SearchResponse {
  query: string
  total: number
  page: number
  per_page: number
  results: Screenshot[]
  summary?: string
}

export interface SummaryResponse {
  summary: string
}

export interface Filters {
  dateFrom: string
  dateTo: string
  tag: string
}
