import { NextRequest, NextResponse } from "next/server"
import { exec } from "child_process"

export async function GET(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path")

  if (!path) {
    return NextResponse.json({ error: "Missing path" }, { status: 400 })
  }

  // Sanitize: only allow paths inside the screenvault storage dir
  const allowed = process.env.STORAGE_DIR ?? `${process.env.HOME}/.screenvault`
  if (!path.startsWith(allowed)) {
    return NextResponse.json({ error: "Path not allowed" }, { status: 403 })
  }

  return new Promise<NextResponse>((resolve) => {
    exec(`open "${path}"`, (err) => {
      if (err) {
        resolve(NextResponse.json({ error: "Failed to open file" }, { status: 500 }))
      } else {
        resolve(NextResponse.json({ ok: true }))
      }
    })
  })
}
