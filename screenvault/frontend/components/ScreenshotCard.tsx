"use client"

import type { Screenshot } from "@/types"
import { thumbnailUrl } from "@/lib/api"

interface Props {
  screenshot: Screenshot
  onClick: (s: Screenshot) => void
}

export default function ScreenshotCard({ screenshot, onClick }: Props) {
  return (
    <div className="group relative break-inside-avoid overflow-hidden rounded-[24px] bg-white transition-all duration-500 hover:shadow-2xl hover:shadow-black/20 mb-6 cursor-zoom-in">
      <button
        onClick={() => onClick(screenshot)}
        className="w-full text-left focus:outline-none block"
      >
        <div className="relative w-full overflow-hidden">
          <img
            src={thumbnailUrl(screenshot.thumbnail)}
            alt={screenshot.description ?? screenshot.filename}
            className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-105"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = "/placeholder.png"
            }}
          />
          {/* Subtle overlay on hover if needed, but keeping it clean like the image */}
          <div className="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/5" />
        </div>
      </button>
    </div>
  )
}
