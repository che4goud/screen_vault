"use client"

import Image from "next/image"
import type { Screenshot } from "@/types"
import { thumbnailUrl, parseTags } from "@/lib/api"

interface Props {
  screenshot: Screenshot
  onClick: (s: Screenshot) => void
}

export default function ScreenshotCard({ screenshot, onClick }: Props) {
  const tags = parseTags(screenshot.tags)
  const date = screenshot.captured_at
    ? new Date(screenshot.captured_at).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric",
      })
    : "Unknown date"

  return (
    <button
      onClick={() => onClick(screenshot)}
      className="group flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white
                 text-left shadow-sm transition-all hover:border-indigo-300 hover:shadow-md
                 focus:outline-none focus:ring-2 focus:ring-indigo-300"
    >
      {/* Thumbnail */}
      <div className="relative h-40 w-full overflow-hidden bg-gray-100">
        <Image
          src={thumbnailUrl(screenshot.thumbnail)}
          alt={screenshot.description ?? screenshot.filename}
          fill
          className="object-cover transition-transform duration-300 group-hover:scale-105"
          onError={(e) => {
            (e.target as HTMLImageElement).src = "/placeholder.png"
          }}
        />
      </div>

      {/* Info */}
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <p className="text-xs text-gray-400">{date}</p>

        <p className="line-clamp-2 text-sm text-gray-700 leading-snug">
          {screenshot.description ?? screenshot.filename}
        </p>

        {/* FTS5 highlighted snippet */}
        {screenshot.snippet && (
          <p
            className="text-xs text-gray-500 line-clamp-1"
            dangerouslySetInnerHTML={{ __html: screenshot.snippet }}
          />
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="mt-auto flex flex-wrap gap-1 pt-1">
            {tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  )
}
