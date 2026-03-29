"use client"

import { Search, X, Loader2 } from "lucide-react"

interface Props {
  value: string
  onChange: (v: string) => void
  isLoading: boolean
}

export default function SearchBar({ value, onChange, isLoading }: Props) {
  return (
    <div className="relative w-full max-w-xl mx-auto group">
      <div className="glass flex items-center rounded-[24px] px-6 py-4 shadow-xl shadow-black/5 hover:shadow-2xl hover:shadow-black/10 transition-all duration-300">
        <div className="mr-4 flex items-center justify-center">
          {isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <Search className="h-6 w-6 text-gray-400 group-focus-within:text-gray-600 transition-colors" />
          )}
        </div>
        
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search all photos..."
          className="flex-1 bg-transparent border-none text-[18px] text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-0 w-full font-light"
        />

        {value && (
          <button
            onClick={() => onChange("")}
            className="ml-4 p-1 rounded-full hover:bg-gray-100/50 text-gray-400 hover:text-gray-600 transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  )
}
