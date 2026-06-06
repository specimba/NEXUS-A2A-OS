import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
  // If Supabase credentials are not configured, skip auth middleware
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

  if (!supabaseUrl || !supabaseKey || supabaseUrl === '' || supabaseKey === '') {
    // No Supabase configured — allow all requests through
    // Redirect /protected to home since auth isn't available
    if (request.nextUrl.pathname.startsWith('/protected')) {
      const url = request.nextUrl.clone()
      url.pathname = '/'
      return NextResponse.redirect(url)
    }
    return NextResponse.next({ request })
  }

  // Supabase is configured — use full auth middleware
  try {
    const { createServerClient } = await import('@supabase/ssr')

    let supabaseResponse = NextResponse.next({ request })

    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    })

    const { data } = await supabase.auth.getClaims()
    const user = data?.claims

    if (!user && request.nextUrl.pathname.startsWith('/protected')) {
      const url = request.nextUrl.clone()
      url.pathname = '/auth/login'
      return NextResponse.redirect(url)
    }

    return supabaseResponse
  } catch (error) {
    // If Supabase client creation fails, just pass through
    console.error('Supabase middleware error:', error)
    return NextResponse.next({ request })
  }
}
