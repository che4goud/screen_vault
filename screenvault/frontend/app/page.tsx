"use client"

import { useState, useCallback } from "react"
import useSWR from "swr"

import SearchBar from "@/components/SearchBar"
import FilterSidebar from "@/components/FilterSidebar"
import ResultsGrid from "@/components/ResultsGrid"
import ImageModal from "@/components/ImageModal"
import { searchScreenshots, parseTags } from "@/lib/api"
import { useDebounce } from "@/lib/useDebounce"
import type { Filters, Screenshot, SearchResponse } from "@/types"

const EMPTY_FILTERS: Filters = { dateFrom: "", dateTo: "", tag: "" }

export default function Home() {
  const [query, setQuery] = useState("")
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Screenshot | null>(null)

  const debouncedQuery = useDebounce(query, 400)

  const { data, isLoading, error } = useSWR<SearchResponse>(
    debouncedQuery ? ["search", debouncedQuery, page, filters] : null,
    () => searchScreenshots(debouncedQuery, page, filters),
    { keepPreviousData: true }
  )

  const handleQueryChange = useCallback((v: string) => {
    setQuery(v)
    setPage(1)
  }, [])

  const handleFiltersChange = useCallback((f: Filters) => {
    setFilters(f)
    setPage(1)
  }, [])

  const allTags = Array.from(
    new Set((data?.results ?? []).flatMap((r) => parseTags(r.tags)))
  )

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white px-6 py-4 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center gap-6">
          <span className="shrink-0 text-xl font-bold text-indigo-600">ScreenVault</span>
          <SearchBar
            value={query}
            onChange={handleQueryChange}
            isLoading={isLoading && !!debouncedQuery}
          />
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl gap-8 px-6 py-8">
        <FilterSidebar
          filters={filters}
          onChange={handleFiltersChange}
          allTags={allTags}
        />

        <div className="min-w-0 flex-1">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {error.message}
            </div>
          )}
          <ResultsGrid
            results={data?.results ?? []}
            total={data?.total ?? 0}
            query={debouncedQuery}
            isLoading={isLoading && !!debouncedQuery}
            onSelect={setSelected}
          />
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </main>

      <ImageModal screenshot={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
