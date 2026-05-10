import { NextResponse } from 'next/server'
import { getAllModels } from '@/lib/modelrelay/gateway'

export async function GET() {
  try {
    const models = getAllModels()
    return NextResponse.json({ models, total: models.length })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get models' },
      { status: 500 }
    )
  }
}
