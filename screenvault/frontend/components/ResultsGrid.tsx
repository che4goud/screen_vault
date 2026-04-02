"use client"

import type { Screenshot } from "@/types"
import ScreenshotCard from "./ScreenshotCard"
import DocumentCard from "./DocumentCard"
import { Loader2, Image as ImageIcon } from "lucide-react"

interface Props {
  results: Screenshot[]
  total: number
  query: string
  isLoading: boolean
  onSelect: (s: Screenshot) => void
}

export default function ResultsGrid({ results, total, query, isLoading, onSelect }: Props) {
  if (isLoading && results.length === 0) {
    return (
      <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 15 }).map((_, i) => (
          <div key={i} className="aspect-[3/4] animate-pulse rounded-[24px] bg-gray-100" />
        ))}
      </div>
    )
  }

  // Only show if no query and NO results (fresh vault)
  if (!query && results.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <div className="glass p-6 rounded-full mb-8">
          <ImageIcon className="h-10 w-10 text-gray-300" />
        </div>
        <p className="text-[18px] font-medium text-gray-400">Vault is empty</p>
        <p className="mt-2 text-[14px] text-gray-300">Nothing captured yet, keep vaulting!</p>
      </div>
    )
  }

  // Show "No matches" only if we ARE searching and found 0
  if (results.length === 0 && query && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <p className="text-[18px] font-medium text-gray-500">No matches for "{query}"</p>
        <p className="mt-2 text-[14px] text-gray-400">Try adjusting your search or filters</p>
      </div>
    )
  }

  return (
    <div className="space-y-12">
      <div className="flex items-center justify-center">
        <p className="text-[14px] font-medium text-gray-400 tracking-widest uppercase bg-gray-50 px-4 py-1 rounded-full">
          {query ? `${total} Items Found` : `Recent Items`}
        </p>
      </div>
      
      <div className="columns-2 sm:columns-3 lg:columns-4 xl:columns-5 gap-8 space-y-8">
        {results.map((s) => (
          <div key={s.id} className="break-inside-avoid">
            {s.type === "document"
              ? <DocumentCard item={s} onClick={onSelect} />
              : <ScreenshotCard screenshot={s} onClick={onSelect} />
            }
          </div>
        ))}
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-300" />
        </div>
      )}
    </div>
  )
}
