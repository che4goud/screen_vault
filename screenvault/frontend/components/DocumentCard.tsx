"use client"

import type { Screenshot } from "@/types"
import { FileText } from "lucide-react"

interface Props {
  item: Screenshot
  onClick: (s: Screenshot) => void
}

const EXT_COLORS: Record<string, string> = {
  ".pdf":  "bg-red-50 text-red-400",
  ".docx": "bg-blue-50 text-blue-400",
  ".xlsx": "bg-green-50 text-green-500",
  ".pptx": "bg-orange-50 text-orange-400",
}

const EXT_LABEL: Record<string, string> = {
  ".pdf":  "PDF",
  ".docx": "Word",
  ".xlsx": "Excel",
  ".pptx": "PowerPoint",
}

function getExt(filename: string): string {
  const parts = filename.split(".")
  return parts.length > 1 ? "." + parts.pop()!.toLowerCase() : ""
}

function pageLabel(ext: string, count: number): string {
  if (ext === ".xlsx") return `${count} sheet${count !== 1 ? "s" : ""}`
  if (ext === ".pptx") return `${count} slide${count !== 1 ? "s" : ""}`
  return `${count} page${count !== 1 ? "s" : ""}`
}

export default function DocumentCard({ item, onClick }: Props) {
  const ext = getExt(item.filename)
  const colorClass = EXT_COLORS[ext] ?? "bg-gray-50 text-gray-400"
  const label = EXT_LABEL[ext] ?? ext.toUpperCase().slice(1)
  const excerpt = item.ocr_text?.slice(0, 140) ?? item.description?.slice(0, 140) ?? ""

  return (
    <div className="group relative break-inside-avoid overflow-hidden rounded-[24px] bg-white transition-all duration-500 hover:shadow-2xl hover:shadow-black/20 mb-6 cursor-pointer">
      <button
        onClick={() => onClick(item)}
        className="w-full text-left focus:outline-none block p-5"
      >
        {/* File type icon block */}
        <div className={`w-full rounded-[16px] ${colorClass} flex flex-col items-center justify-center py-8 mb-4 gap-2`}>
          <FileText className="h-10 w-10" />
          <span className="text-[11px] font-semibold tracking-widest uppercase opacity-60">{label}</span>
        </div>

        {/* Filename */}
        <p className="text-[13px] font-semibold text-gray-800 truncate mb-1">
          {item.filename}
        </p>

        {/* Text excerpt */}
        {excerpt && (
          <p className="text-[11px] text-gray-400 line-clamp-3 leading-relaxed">
            {excerpt}
          </p>
        )}

        {/* Page / sheet / slide count */}
        {item.page_count != null && item.page_count > 0 && (
          <p className="mt-2 text-[10px] font-medium text-gray-300 uppercase tracking-wide">
            {pageLabel(ext, item.page_count)}
          </p>
        )}
      </button>
    </div>
  )
}
