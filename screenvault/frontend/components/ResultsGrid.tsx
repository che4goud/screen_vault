"use client"

import type { Screenshot } from "@/types"
import ScreenshotCard from "./ScreenshotCard"

interface Props {
  results: Screenshot[]
  total: number
  query: string
  isLoading: boolean
  onSelect: (s: Screenshot) => void
}

export default function ResultsGrid({ results, total, query, isLoading, onSelect }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-52 animate-pulse rounded-xl bg-gray-100" />
        ))}
      </div>
    )
  }

  if (!query) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <svg className="mb-4 h-12 w-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14
               M8 10h.01M3 5h18a1 1 0 011 1v12a1 1 0 01-1 1H3a1 1 0 01-1-1V6a1 1 0 011-1z" />
        </svg>
        <p className="text-gray-400">Type to search your screenshots</p>
        <p className="mt-1 text-sm text-gray-300">Try "invoice", "meeting notes", or "login page"</p>
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <p className="text-gray-500">No results for <span className="font-medium">"{query}"</span></p>
        <p className="mt-1 text-sm text-gray-400">Try different keywords or check your filters</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500">
        {total} result{total !== 1 ? "s" : ""} for{" "}
        <span className="font-medium text-gray-700">"{query}"</span>
      </p>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {results.map((s) => (
          <ScreenshotCard key={s.id} screenshot={s} onClick={onSelect} />
        ))}
      </div>
    </div>
  )
}
