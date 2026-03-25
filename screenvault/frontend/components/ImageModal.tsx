"use client"

import { useEffect } from "react"
import Image from "next/image"
import type { Screenshot } from "@/types"
import { thumbnailUrl, parseTags } from "@/lib/api"

interface Props {
  screenshot: Screenshot | null
  onClose: () => void
}

export default function ImageModal({ screenshot, onClose }: Props) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [onClose])

  if (!screenshot) return null

  const tags = parseTags(screenshot.tags)
  const date = screenshot.captured_at
    ? new Date(screenshot.captured_at).toLocaleString("en-US", {
        dateStyle: "medium", timeStyle: "short",
      })
    : "Unknown date"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-3">
          <div>
            <p className="font-medium text-gray-800">{screenshot.filename}</p>
            <p className="text-xs text-gray-400">{date}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Image */}
        <div className="relative h-[50vh] w-full bg-gray-50">
          <Image
            src={thumbnailUrl(screenshot.thumbnail)}
            alt={screenshot.description ?? screenshot.filename}
            fill
            className="object-contain"
          />
        </div>

        {/* Details */}
        <div className="space-y-3 px-5 py-4">
          {screenshot.description && (
            <div>
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Description
              </p>
              <p className="text-sm text-gray-700">{screenshot.description}</p>
            </div>
          )}

          {screenshot.ocr_text && (
            <div>
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Text found in screenshot
              </p>
              <p className="max-h-24 overflow-y-auto rounded-lg bg-gray-50 px-3 py-2 text-xs
                            font-mono text-gray-600 leading-relaxed">
                {screenshot.ocr_text}
              </p>
            </div>
          )}

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t px-5 py-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-gray-500 hover:bg-gray-100"
          >
            Close
          </button>
          <a
            href={`/api/open?path=${encodeURIComponent(screenshot.filepath)}`}
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm text-white hover:bg-indigo-600"
          >
            Open in Preview
          </a>
        </div>
      </div>
    </div>
  )
}
