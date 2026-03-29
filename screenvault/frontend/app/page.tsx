"use client"

import { useState, useCallback } from "react"
import useSWR from "swr"
import { RotateCcw } from "lucide-react"

import SearchBar from "@/components/SearchBar"
import ResultsGrid from "@/components/ResultsGrid"
import ImageModal from "@/components/ImageModal"
import { searchScreenshots, getAllScreenshots, parseTags } from "@/lib/api"
import { useDebounce } from "@/lib/useDebounce"
import type { Filters, Screenshot, SearchResponse } from "@/types"

const EMPTY_FILTERS: Filters = { dateFrom: "", dateTo: "", tag: "" }

export default function Home() {
  const [query, setQuery] = useState("")
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Screenshot | null>(null)

  const debouncedQuery = useDebounce(query, 400)

  const isSearching = debouncedQuery.length > 0

  const { data, isLoading, error, mutate } = useSWR<SearchResponse>(
    isSearching
      ? ["search", debouncedQuery, page, filters]
      : ["all", page],
    () => isSearching
      ? searchScreenshots(debouncedQuery, page, filters)
      : getAllScreenshots(page),
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
    <div className="min-h-screen bg-[#fdfdfd] selection:bg-black selection:text-white">
      <main className="mx-auto max-w-[1400px] px-6 pt-16 pb-24">
        {/* Header Section: Search & Filters */}
        <div className="flex flex-col items-center gap-8 mb-16">
          <div className="w-full max-w-2xl px-4">
            <SearchBar
              value={query}
              onChange={handleQueryChange}
              isLoading={isLoading && !!debouncedQuery}
            />
          </div>

          <div className="flex flex-col items-center gap-6">
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button 
                onClick={() => handleFiltersChange(EMPTY_FILTERS)}
                className={`glass px-6 py-2 rounded-full text-[14px] font-medium transition-all ${
                  !filters.tag && !filters.dateFrom ? 'bg-black text-white' : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                All
              </button>
              
              {["Favorites", "Recent", "Screenshots", "Videos"].map(label => (
                <button
                  key={label}
                  className="glass px-6 py-2 rounded-full text-[14px] font-medium text-gray-600 hover:bg-gray-100 transition-all border-none"
                >
                  {label}
                </button>
              ))}

              {allTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => handleFiltersChange({...filters, tag: filters.tag === tag ? "" : tag})}
                  className={`glass px-6 py-2 rounded-full text-[14px] font-medium transition-all ${
                    filters.tag === tag ? 'bg-black text-white border-transparent' : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>

            <button 
              onClick={() => mutate()}
              className="p-3 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-900 transition-all"
            >
              <RotateCcw className={`h-6 w-6 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="relative">
          {error && (
            <div className="mx-auto max-w-2xl mb-12 glass border-red-100 bg-red-50/50 px-8 py-4 rounded-2xl text-[14px] text-red-600">
              {error.message}
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
