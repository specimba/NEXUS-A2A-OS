import { create } from 'zustand'

export type NexusTab = 'overview' | 'stresslab' | 'gmr' | 'governor' | 'vault' | 'research' | 'swarm' | 'tokens'

export interface ChatMessage {
  role: string
  content: string
  timestamp: number
}

interface NexusState {
  activeTab: NexusTab
  setActiveTab: (tab: NexusTab) => void
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  isChatOpen: boolean
  toggleChat: () => void
  setChatOpen: (open: boolean) => void
  chatMessages: ChatMessage[]
  addChatMessage: (msg: { role: string; content: string }) => void
  clearChatMessages: () => void
}

export const useNexusStore = create<NexusState>((set) => ({
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab }),
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  isChatOpen: false,
  toggleChat: () => set((s) => ({ isChatOpen: !s.isChatOpen })),
  setChatOpen: (open) => set({ isChatOpen: open }),
  chatMessages: [],
  addChatMessage: (msg) =>
    set((s) => ({
      chatMessages: [
        ...s.chatMessages,
        { ...msg, timestamp: Date.now() },
      ],
    })),
  clearChatMessages: () => set({ chatMessages: [] }),
}))
