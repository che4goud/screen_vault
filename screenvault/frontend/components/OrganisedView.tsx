"use client"

import type { Cluster, Screenshot } from "@/types"
import ScreenshotCard from "./ScreenshotCard"
import { Loader2 } from "lucide-react"

interface Props {
  clusters: Cluster[]
  isLoading: boolean
  onSelect: (s: Screenshot) => void
}

export default function OrganisedView({ clusters, isLoading, onSelect }: Props) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-gray-300" />
        <p className="text-[13px] text-gray-400">Organising your vault…</p>
      </div>
    )
  }

  if (clusters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <p className="text-[18px] font-medium text-gray-400">Nothing to organise yet</p>
        <p className="mt-2 text-[14px] text-gray-300">Add some screenshots to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-20">
      {clusters.map((cluster, i) => (
        <section key={i}>
          <h2 className="text-[13px] font-semibold text-gray-400 tracking-widest uppercase mb-8">
            {cluster.name}
            <span className="ml-3 font-normal text-gray-300">{cluster.screenshots.length}</span>
          </h2>
          <div className="columns-2 sm:columns-3 lg:columns-4 xl:columns-5 gap-8">
            {cluster.screenshots.map((s) => (
              <div key={s.id} className="break-inside-avoid mb-6">
                <ScreenshotCard screenshot={s} onClick={onSelect} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
