import { redirect } from 'next/navigation'

import { LogoutButton } from '@/components/logout-button'
import { createClient } from '@/lib/server'

export default async function Page() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-6 p-6 text-center">
      <div>
        <p className="text-sm text-muted-foreground">Signed in as</p>
        <h1 className="text-2xl font-semibold">{user.email}</h1>
      </div>
      <LogoutButton />
    </main>
  )
}
