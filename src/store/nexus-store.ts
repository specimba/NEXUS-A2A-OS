import { create } from 'zustand'

export type NexusTab = 'overview' | 'stresslab' | 'gmr' | 'governor' | 'vault' | 'research' | 'swarm' | 'tokens'

interface NexusState {
  activeTab: NexusTab
  setActiveTab: (tab: NexusTab) => void
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

export const useNexusStore = create<NexusState>((set) => ({
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab }),
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
