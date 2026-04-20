'use client'

import { NexusSidebar } from '@/components/nexus/sidebar'
import { NexusHeader } from '@/components/nexus/header'
import { NexusFooter } from '@/components/nexus/footer'
import { TabContent } from '@/components/nexus/tab-content'

export default function Home() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <NexusSidebar />

      {/* Main Area */}
      <div className="flex flex-1 flex-col min-w-0">
        <NexusHeader />

        {/* Content */}
        <main className="flex-1 overflow-auto bg-background">
          <TabContent />
        </main>

        {/* Sticky Footer */}
        <NexusFooter />
      </div>
    </div>
  )
}
