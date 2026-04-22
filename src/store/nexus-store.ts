import { create } from 'zustand'

export type NexusTab = 'overview' | 'stresslab' | 'gmr' | 'governor' | 'vault' | 'research' | 'swarm' | 'tokens' | 'ratelimit'

export interface ChatMessage {
  role: string
  content: string
  timestamp: number
}

export type NotificationType = 'info' | 'warning' | 'error' | 'success'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  time: string
  read: boolean
  source: string
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
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id' | 'read'>) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  clearNotification: (id: string) => void
  clearAllNotifications: () => void
  unreadCount: () => number
  isNotificationCenterOpen: boolean
  toggleNotificationCenter: () => void
  setNotificationCenterOpen: (open: boolean) => void
  isExportDialogOpen: boolean
  toggleExportDialog: () => void
  setExportDialogOpen: (open: boolean) => void
}

const initialNotifications: Notification[] = [
  { id: 'n1', type: 'error', title: 'Swarm worker-2 error rate exceeded', message: 'Error rate at 34% — exceeds 25% threshold. Auto-recovery initiated.', time: '2m ago', read: false, source: 'Swarm' },
  { id: 'n2', type: 'warning', title: 'Governor blocked 3 CRITICAL actions', message: 'Patterns matched: delete_all (2x), override_constitution (1x). All blocked.', time: '5m ago', read: false, source: 'Governor' },
  { id: 'n3', type: 'warning', title: 'Token budget at 73.4%', message: '26,550 tokens remaining of 100,000 session budget. Burn rate: 142 tok/min.', time: '10m ago', read: false, source: 'Tokens' },
  { id: 'n4', type: 'info', title: 'StressLab test ISC-001 completed', message: 'Result: COLLAPSE detected. qwen3-coder collapsed at 95.3% rate in agentic mode.', time: '12m ago', read: false, source: 'StressLab' },
  { id: 'n5', type: 'success', title: 'New research paper vetted: OR-Bench', message: 'Over-Refusal Benchmark added to P1 queue. Relevance: 95%. Task assigned.', time: '15m ago', read: false, source: 'Research' },
  { id: 'n6', type: 'success', title: 'GMR pool FAST: all models healthy', message: 'gemma-fast (100%), nemotron-3-super (96%) — no fallbacks needed.', time: '20m ago', read: true, source: 'GMR' },
  { id: 'n7', type: 'info', title: 'Agent worker-3 trust score increased', message: 'Trust updated: 0.78 → 0.82. Reason: successful stress test completion.', time: '25m ago', read: true, source: 'Governor' },
  { id: 'n8', type: 'success', title: 'Constitution check passed', message: 'All limits within bounds: 3/5 agents, 12/20 API calls, 8/30 writes.', time: '30m ago', read: true, source: 'Vault' },
  { id: 'n9', type: 'warning', title: 'GMR failover: dolphin-mistral → trinity-large', message: 'Health dropped below 70% threshold. Failover completed in 1.2s.', time: '35m ago', read: true, source: 'GMR' },
  { id: 'n10', type: 'info', title: 'Swarm coordinator heartbeat healthy', message: 'All 3 active workers reporting nominal status. Uptime: 4h 23m.', time: '45m ago', read: true, source: 'Swarm' },
]

let notificationCounter = 100

export const useNexusStore = create<NexusState>((set, get) => ({
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
  notifications: initialNotifications,
  addNotification: (notification) =>
    set((s) => ({
      notifications: [
        {
          ...notification,
          id: `n${++notificationCounter}`,
          read: false,
        },
        ...s.notifications,
      ],
    })),
  markAsRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    })),
  markAllAsRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),
  clearNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    })),
  clearAllNotifications: () => set({ notifications: [] }),
  unreadCount: () => get().notifications.filter((n) => !n.read).length,
  isNotificationCenterOpen: false,
  toggleNotificationCenter: () => set((s) => ({ isNotificationCenterOpen: !s.isNotificationCenterOpen })),
  setNotificationCenterOpen: (open: boolean) => set({ isNotificationCenterOpen: open }),
  isExportDialogOpen: false,
  toggleExportDialog: () => set((s) => ({ isExportDialogOpen: !s.isExportDialogOpen })),
  setExportDialogOpen: (open: boolean) => set({ isExportDialogOpen: open }),
}))
