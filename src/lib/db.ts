import { PrismaClient } from '@prisma/client'
import path from 'node:path'

// ────────────────────────────────────────────────────────────────────────────
// DATABASE_URL bulletproofing
// ────────────────────────────────────────────────────────────────────────────
// The dev sandbox occasionally resyncs and wipes the untracked .env file,
// which leaves Prisma with no DATABASE_URL and turns every API route into a
// 500. We keep the canonical SQLite file at <repo>/db/custom.db (which IS
// tracked in git), and set DATABASE_URL programmatically before Prisma reads
// it. This way the app keeps working even on a fresh, env-less environment.
//
// In production (Vercel), DATABASE_URL is provided via env vars on the
// Project Settings, so this fallback is a no-op there.
// ────────────────────────────────────────────────────────────────────────────
if (!process.env.DATABASE_URL) {
  const dbPath = path.resolve(process.cwd(), 'db', 'custom.db')
  process.env.DATABASE_URL = `file:${dbPath}`
}

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
  })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
