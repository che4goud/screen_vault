"use client"

import { useEffect } from "react"
import type { Screenshot } from "@/types"
import { thumbnailUrl, parseTags } from "@/lib/api"
import { FileText } from "lucide-react"

const DOC_COLORS: Record<string, string> = {
  ".pdf":  "bg-red-50 text-red-400",
  ".docx": "bg-blue-50 text-blue-400",
  ".xlsx": "bg-green-50 text-green-500",
  ".pptx": "bg-orange-50 text-orange-400",
}

function getExt(filename: string): string {
  const parts = filename.split(".")
  return parts.length > 1 ? "." + parts.pop()!.toLowerCase() : ""
}

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
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="relative flex w-full max-w-5xl md:h-[85vh] flex-col md:flex-row overflow-hidden rounded-[32px] bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left Side: Image or Document icon */}
        <div className="relative flex-1 bg-[#f0f0f0] flex items-center justify-center overflow-hidden min-h-[300px]">
          {screenshot.type === "document" ? (
            <div className={`flex flex-col items-center gap-4 p-12 rounded-[24px] ${DOC_COLORS[getExt(screenshot.filename)] ?? "bg-gray-50 text-gray-400"}`}>
              <FileText className="h-20 w-20" />
              <span className="text-[13px] font-semibold tracking-widest uppercase opacity-60">
                {getExt(screenshot.filename).slice(1).toUpperCase()}
              </span>
            </div>
          ) : (
            <img
              src={thumbnailUrl(screenshot.thumbnail)}
              alt={screenshot.description ?? screenshot.filename}
              className="w-full h-full object-contain"
            />
          )}
          <button
            onClick={onClose}
            className="absolute top-4 left-4 h-10 w-10 flex items-center justify-center rounded-full bg-white/90 shadow-md md:hidden hover:bg-white transition-colors"
          >
            <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Right Side: Info and Actions */}
        <div className="w-full md:w-[400px] lg:w-[450px] flex flex-col p-6 lg:p-10 bg-white">
          <div className="flex items-center justify-between mb-8">
            <div className="flex gap-4">
               <div className="h-12 w-12 rounded-full border flex items-center justify-center hover:bg-gray-50 cursor-pointer">
                 <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                 </svg>
               </div>
               <div className="h-12 w-12 rounded-full border flex items-center justify-center hover:bg-gray-50 cursor-pointer">
                 <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
                 </svg>
               </div>
            </div>
            <button className="bg-red-600 text-white px-8 py-3.5 rounded-full font-bold text-[16px] shadow-lg hover:bg-red-700 transition-colors">
              Save
            </button>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            <h1 className="text-3xl font-bold text-gray-900 mb-6 leading-tight">
              {screenshot.description || screenshot.filename || "Screenshot"}
            </h1>

            <div className="flex items-center gap-3 mb-8">
              <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white font-black text-lg">
                SV
              </div>
              <div>
                 <p className="font-bold text-gray-900">ScreenVault User</p>
                 <p className="text-sm text-gray-500">Captured on {date}</p>
              </div>
            </div>

            {screenshot.ocr_text && (
              <div className="mb-8">
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  {screenshot.type === "document" ? "Document Text" : "Extracted Text"}
                </h3>
                <div className="bg-gray-50 rounded-2xl p-4 text-[14px] font-mono text-gray-700 leading-relaxed max-h-[200px] overflow-y-auto whitespace-pre-wrap">
                   {screenshot.ocr_text}
                </div>
              </div>
            )}

            {tags.length > 0 && (
              <div className="mb-8">
                <h3 className="text-lg font-bold text-gray-900 mb-3">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-4 py-2 bg-gray-100 hover:bg-gray-200 cursor-pointer rounded-full text-sm font-bold text-gray-800 transition-colors"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-8 pt-6 border-t flex flex-wrap gap-3">
             <a
                href={`/api/open?path=${encodeURIComponent(screenshot.filepath)}`}
                className="flex-1 bg-gray-100 px-6 py-3.5 rounded-full font-bold text-center text-gray-900 hover:bg-gray-200 transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                {screenshot.type === "document" ? "Open Document" : "Open in Preview"}
              </a>
              <button 
                onClick={onClose}
                className="md:flex h-12 w-12 items-center justify-center rounded-full border hover:bg-gray-50 transition-colors hidden"
              >
                <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
          </div>
        </div>
      </div>
    </div>
  )
}
