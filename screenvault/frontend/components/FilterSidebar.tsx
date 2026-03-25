"use client"

import type { Filters } from "@/types"

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
  allTags: string[]
}

export default function FilterSidebar({ filters, onChange, allTags }: Props) {
  const set = (key: keyof Filters, value: string) =>
    onChange({ ...filters, [key]: value })

  const hasFilters = filters.dateFrom || filters.dateTo || filters.tag

  return (
    <aside className="w-56 shrink-0 space-y-6">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Filters</span>
        {hasFilters && (
          <button
            onClick={() => onChange({ dateFrom: "", dateTo: "", tag: "" })}
            className="text-xs text-indigo-500 hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Date range */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-gray-600">Date from</label>
        <input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => set("dateFrom", e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm
                     focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      <div className="space-y-2">
        <label className="block text-xs font-medium text-gray-600">Date to</label>
        <input
          type="date"
          value={filters.dateTo}
          onChange={(e) => set("dateTo", e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm
                     focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      {/* Tag filter */}
      {allTags.length > 0 && (
        <div className="space-y-2">
          <label className="block text-xs font-medium text-gray-600">Tag</label>
          <div className="flex flex-wrap gap-1.5">
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => set("tag", filters.tag === tag ? "" : tag)}
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors
                  ${filters.tag === tag
                    ? "bg-indigo-500 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}
