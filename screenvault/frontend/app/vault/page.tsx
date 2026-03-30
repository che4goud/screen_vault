"use client"

import { useState, useCallback, useEffect } from "react"
import useSWR from "swr"
import { Sparkles } from "lucide-react"

import SearchBar from "@/components/SearchBar"
import ResultsGrid from "@/components/ResultsGrid"
import ImageModal from "@/components/ImageModal"
import { searchScreenshots, getAllScreenshots, syncScreenshots, fetchSummary } from "@/lib/api"
import { useDebounce } from "@/lib/useDebounce"
import type { Screenshot, SearchResponse, SummaryResponse } from "@/types"

export default function Home() {
  const [query, setQuery] = useState("")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Screenshot | null>(null)

  const debouncedQuery = useDebounce(query, 400)

  const isSearching = debouncedQuery.length > 0

  // Main search results — returns immediately, no summary blocking
  const { data, isLoading, error } = useSWR<SearchResponse>(
    isSearching
      ? ["search", debouncedQuery, page]
      : ["all", page],
    () => isSearching
      ? searchScreenshots(debouncedQuery, page)
      : getAllScreenshots(page),
    { keepPreviousData: true }
  )

  // Summary fetched in parallel — doesn't block results from showing
  const { data: summaryData } = useSWR<SummaryResponse>(
    isSearching ? ["summary", debouncedQuery] : null,
    () => fetchSummary(debouncedQuery),
    { revalidateOnFocus: false }
  )

  // On mount: scan watch folder and enqueue new screenshots
  useEffect(() => {
    syncScreenshots().catch(() => {})
  }, [])

  const handleQueryChange = useCallback((v: string) => {
    setQuery(v)
    setPage(1)
  }, [])

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div className="min-h-screen bg-[#fdfdfd] selection:bg-black selection:text-white">
      <main className="mx-auto max-w-[1400px] px-6 pt-16 pb-24">
        {/* Header Section: Search */}
        <div className="flex flex-col items-center gap-8 mb-16">
          <div className="w-full max-w-2xl px-4">
            <SearchBar
              value={query}
              onChange={handleQueryChange}
              isLoading={isLoading && !!debouncedQuery}
            />
          </div>
        </div>

        <div className="relative">
          {error && (
            <div className="mx-auto max-w-2xl mb-12 glass border-red-100 bg-red-50/50 px-8 py-4 rounded-2xl text-[14px] text-red-600">
              {error.message}
            </div>
          )}

          {isSearching && summaryData?.summary && (
            <div className="mx-auto max-w-2xl glass px-8 py-5 rounded-2xl border border-gray-100 mb-8">
              <div className="flex items-start gap-3">
                <Sparkles className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
                <p className="text-[14px] text-gray-600 leading-relaxed">{summaryData.summary}</p>
              </div>
            </div>
          )}

          <ResultsGrid
            results={data?.results ?? []}
            total={data?.total ?? 0}
            query={debouncedQuery}
            isLoading={isLoading}
            onSelect={setSelected}
          />

          {totalPages > 1 && (
            <div className="mt-20 flex items-center justify-center gap-8">
              <button
                disabled={page === 1}
                onClick={() => {
                  setPage((p) => p - 1)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                className="glass p-3 rounded-full disabled:opacity-30 disabled:pointer-events-none hover:bg-white"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-[14px] font-medium text-gray-400 tracking-widest uppercase">
                {page} / {totalPages}
              </span>
              <button
                disabled={page === totalPages}
                onClick={() => {
                  setPage((p) => p + 1)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                className="glass p-3 rounded-full disabled:opacity-30 disabled:pointer-events-none hover:bg-white"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19l7-7-7-7" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </main>

      <ImageModal screenshot={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
