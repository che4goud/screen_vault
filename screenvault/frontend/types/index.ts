export interface Screenshot {
  id: number
  filename: string
  filepath: string
  thumbnail: string | null
  captured_at: string
  description: string
  ocr_text?: string
  tags: string // JSON array string e.g. '["invoice","finance"]'
  snippet?: string // highlighted FTS5 snippet
  rank?: number
}

export interface SearchResponse {
  query: string
  total: number
  page: number
  per_page: number
  results: Screenshot[]
}

export interface Filters {
  dateFrom: string
  dateTo: string
  tag: string
}
