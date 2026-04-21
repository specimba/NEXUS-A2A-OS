import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET() {
  try {
    const configs = await db.systemConfig.findMany()
    const settings: Record<string, string> = {}
    for (const c of configs) {
      settings[c.key] = c.value
    }

    const configured = !!(settings['OPENROUTER_API_KEY'] || settings['ZAI_SDK_KEY'])

    return NextResponse.json({
      settings,
      configured,
      providers: {
        openrouter: !!settings['OPENROUTER_API_KEY'],
        openai: !!settings['OPENAI_API_KEY'],
        cerebras: !!settings['CEREBRAS_API_KEY'],
        jina: !!settings['JINA_API_KEY'],
        kilocode: !!settings['KILOCODE_API_KEY'],
        zai_sdk: true,
      }
    })
  } catch (error) {
    console.error('Settings GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { key, value } = body as { key: string; value: string }

    if (!key || !value) {
      return NextResponse.json({ error: 'Key and value are required' }, { status: 400 })
    }

    await db.systemConfig.upsert({
      where: { key },
      update: { value },
      create: { key, value },
    })

    return NextResponse.json({ success: true, key })
  } catch (error) {
    console.error('Settings PUT error:', error)
    return NextResponse.json({ error: 'Failed to save setting' }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const key = searchParams.get('key')

    if (!key) {
      return NextResponse.json({ error: 'Key is required' }, { status: 400 })
    }

    await db.systemConfig.deleteMany({ where: { key } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Settings DELETE error:', error)
    return NextResponse.json({ error: 'Failed to delete setting' }, { status: 500 })
  }
}
