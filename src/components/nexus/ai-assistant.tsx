'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, X, Send, Trash2, Bot, User, MessageSquare, ChevronDown, Cpu, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  useNexusStore,
  ChatMessage,
} from '@/store/nexus-store'

// ─── Model Options (inspired by GLM5 team's model selector) ───

const AI_MODELS = [
  { id: 'default', label: 'NEXUS AI', description: 'GLM-4.7 via z-ai SDK', icon: '⚡' },
  { id: 'reasoning', label: 'Llama 3.3 70B', description: 'Cerebras Free (ultra-fast)', icon: '🧠' },
  { id: 'balanced', label: 'DeepSeek R1', description: 'Strong reasoning (OR Free)', icon: '⚙️' },
  { id: 'fast', label: 'Llama 3.1 8B', description: 'Cerebras Free (fastest)', icon: '⚡' },
] as const

type AIModel = typeof AI_MODELS[number]['id']

const QUICK_PROMPTS = [
  'System Status',
  'Run StressLab Test',
  'Show Trust Scores',
  'Analyze Vault Entries',
  'Governance Report',
  'GMR Pool Status',
]

// ─── Local Storage Keys ───

const CHAT_STORAGE_KEY = 'nexus-chat-history'
const MAX_STORED_MESSAGES = 50

function loadStoredMessages(): ChatMessage[] {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Migrate old messages: extract [model] from content → model field
        return parsed.slice(-MAX_STORED_MESSAGES).map((msg: ChatMessage) => {
          if (msg.role === 'assistant' && !msg.model) {
            const match = msg.content.match(/\s*\[([^\]]+)\]\s*$/)
            if (match) {
              return {
                ...msg,
                content: msg.content.replace(/\s*\[[^\]]+\]\s*$/, ''),
                model: match[1],
              }
            }
          }
          return msg
        })
      }
    }
  } catch { /* ignore */ }
  return []
}

function saveMessages(messages: ChatMessage[]) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)))
  } catch { /* ignore */ }
}

// ─── Sub-components ───

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 mb-4 px-1">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
        <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
      </div>
      <div className="rounded-xl rounded-tl-none bg-muted px-4 py-2.5">
        <div className="flex gap-1.5">
          <motion.span
            className="h-2 w-2 rounded-full bg-emerald-400"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
          />
          <motion.span
            className="h-2 w-2 rounded-full bg-emerald-400"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
          />
          <motion.span
            className="h-2 w-2 rounded-full bg-emerald-400"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
          />
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex items-start gap-2 mb-3 px-1 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isUser
            ? 'bg-emerald-500/20'
            : 'bg-muted'
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        )}
      </div>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed break-words ${
          isUser
            ? 'rounded-tr-none bg-gradient-to-br from-emerald-500 to-emerald-700 text-white'
            : 'rounded-tl-none bg-muted text-foreground'
        }`}
      >
        {/* Render message with basic formatting */}
        {message.content.split('\n').map((line, i) => {
          // Bold text: **text**
          const boldFormatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          // Code inline: `text`
          const codeFormatted = boldFormatted.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 text-xs font-mono">$1</code>')
          return (
            <span key={i}>
              {i > 0 && <br />}
              {codeFormatted.includes('<strong>') || codeFormatted.includes('<code') ? (
                <span dangerouslySetInnerHTML={{ __html: codeFormatted }} />
              ) : (
                line
              )}
            </span>
          )
        })}
        {/* Model badge — shown as subtle tag below assistant messages */}
        {!isUser && message.model && (
          <div className="mt-1.5 text-[9px] text-muted-foreground/40 font-mono">· {message.model}</div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Scroll-to-Bottom Button ───

function ScrollToBottom({ onClick }: { onClick: () => void }) {
  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      onClick={onClick}
      className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-card border border-border/60 shadow-lg hover:bg-accent transition-colors cursor-pointer"
      aria-label="Scroll to bottom"
    >
      <ChevronDown className="h-4 w-4 text-muted-foreground" />
    </motion.button>
  )
}

// ─── Main Component ───

export function NexusAssistant() {
  const {
    isChatOpen,
    toggleChat,
    setChatOpen,
    chatMessages,
    addChatMessage,
    clearChatMessages,
  } = useNexusStore()

  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState<AIModel>('default')
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [messageCount, setMessageCount] = useState(0)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const prevMessageCountRef = useRef(0)

  // ─── Scroll Management ───

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (scrollContainerRef.current) {
      const el = scrollContainerRef.current
      el.scrollTo({ top: el.scrollHeight, behavior })
    }
  }, [])

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return
    const el = scrollContainerRef.current
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setIsAtBottom(distanceFromBottom < 60)
  }, [])

  // Auto-scroll when new messages arrive (only if already at bottom)
  useEffect(() => {
    if (chatMessages.length > prevMessageCountRef.current && isAtBottom) {
      requestAnimationFrame(() => scrollToBottom('smooth'))
    }
    prevMessageCountRef.current = chatMessages.length
    setMessageCount(chatMessages.length)
  }, [chatMessages, isAtBottom, scrollToBottom])

  // Focus input when chat opens
  useEffect(() => {
    if (isChatOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isChatOpen])

  // Persist messages to localStorage
  useEffect(() => {
    if (chatMessages.length > 0) {
      saveMessages(chatMessages)
    }
  }, [chatMessages])

  // Load stored messages on mount
  useEffect(() => {
    const stored = loadStoredMessages()
    if (stored.length > 0 && chatMessages.length === 0) {
      stored.forEach((msg) => addChatMessage(msg))
    }
  }, [chatMessages.length, addChatMessage])

  // ─── Message Sending ───

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      const trimmed = content.trim()
      setInput('')

      // Get current messages BEFORE adding the new user message
      const currentMessages = useNexusStore.getState().chatMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }))

      // Add user message to store
      addChatMessage({ role: 'user', content: trimmed })
      setIsLoading(true)

      try {
        // Build request body with model preference
        const requestBody: Record<string, unknown> = {
          messages: [
            ...currentMessages,
            { role: 'user', content: trimmed },
          ],
        }

        // If a specific model is selected, pass it along
        if (selectedModel !== 'default') {
          requestBody.model = selectedModel
        }

        // Route based on model selection:
        // - default (NEXUS AI) → z-ai-web-dev-sdk
        // - reasoning/fast (Cerebras models) → AI Bridge
        // - balanced (DeepSeek R1) → Claude proxy → OpenRouter
        let response: Response | null = null
        let usedEndpoint = ''

        // For Cerebras models, use the AI bridge directly
        if (selectedModel === 'reasoning' || selectedModel === 'fast') {
          try {
            response = await fetch('/api/ai-bridge', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ...requestBody,
                tier: selectedModel === 'reasoning' ? 'reasoning' : 'fast',
              }),
            })
            if (response.ok) {
              usedEndpoint = 'cerebras'
            } else {
              response = null
            }
          } catch {
            response = null
          }
        }

        // Default: Try z-ai-web-dev-sdk first (reliable)
        if (!response && selectedModel === 'default') {
          try {
            response = await fetch('/api/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(requestBody),
            })
            if (response.ok) {
              usedEndpoint = 'z-ai-sdk'
            } else {
              response = null
            }
          } catch {
            response = null
          }
        }

        // Fallback to Claude proxy (OpenRouter)
        if (!response) {
          try {
            response = await fetch('/api/claude', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(requestBody),
            })
            if (response.ok) {
              usedEndpoint = 'openrouter'
            } else {
              response = null
            }
          } catch {
            response = null
          }
        }

        // Last resort: z-ai SDK
        if (!response) {
          try {
            response = await fetch('/api/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ messages: [...currentMessages, { role: 'user', content: trimmed }] }),
            })
            if (response.ok) {
              usedEndpoint = 'z-ai-sdk'
            } else {
              response = null
            }
          } catch {
            response = null
          }
        }

        if (!response || !response.ok) {
          throw new Error('Failed to get response from any provider')
        }

        const data = await response.json()
        // Determine the actual model name for transparency (stored as metadata, NOT in content)
        // Normalize: data.model could be a string, an object from ai-bridge, or undefined
        let actualModel: string
        if (typeof data.model === 'string') {
          // Clean up model names: remove provider prefixes, :free suffixes, etc.
          const raw = data.model
          // Common patterns: "deepseek/deepseek-r1:free" → "DeepSeek R1"
          // "google/gemma-4-26b-a4b-it:free" → "Gemma 4"
          // "qwen/qwen3-coder:free" → "Qwen3 Coder"
          // "arcee-ai/trinity-large-preview:free" → "Trinity Large"
          // "glm-4-plus" → "GLM-4 Plus"
          // "glm-4.7" → "GLM-4.7"
          // "claude-opus-4" → handled below
          if (raw.includes('/')) {
            const name = raw.split('/').pop()?.replace(/:free$/, '').replace(/:preview$/, '') || raw
            if (name.includes('deepseek-r1')) actualModel = 'DeepSeek R1'
            else if (name.includes('gemma-4')) actualModel = 'Gemma 4'
            else if (name.includes('gemma')) actualModel = 'Gemma'
            else if (name.includes('qwen3-coder')) actualModel = 'Qwen3 Coder'
            else if (name.includes('qwen')) actualModel = 'Qwen'
            else if (name.includes('trinity-large')) actualModel = 'Trinity Large'
            else if (name.includes('trinity')) actualModel = 'Trinity'
            else if (name.includes('llama')) actualModel = 'Llama'
            else actualModel = name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          } else if (raw.startsWith('claude-')) {
            // Map proxy model IDs to actual underlying models
            if (raw.includes('opus')) actualModel = 'Qwen3 Coder'
            else if (raw.includes('sonnet')) actualModel = 'Trinity Large'
            else if (raw.includes('haiku')) actualModel = 'Gemma 4'
            else actualModel = raw
          } else {
            // z-ai SDK models: "glm-4-plus", "glm-4.7", etc.
            actualModel = raw.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          }
        } else if (data.model && typeof data.model === 'object' && data.model.displayName) {
          actualModel = data.model.displayName
        } else {
          actualModel = usedEndpoint === 'cerebras' ? 'Cerebras'
            : usedEndpoint === 'openrouter' ? 'OpenRouter'
            : 'GLM-4.7'
        }
        // Clean the response content — strip any trailing [model] tags the model itself might have added
        const cleanResponse = data.response.replace(/\s*\[[\w\-]+\]\s*$/, '').trim()
        addChatMessage({ role: 'assistant', content: cleanResponse, model: actualModel })
      } catch {
        addChatMessage({
          role: 'assistant',
          content:
            '⚠ Connection error. The NEXUS kernel may be offline. Please try again.',
        })
      } finally {
        setIsLoading(false)
      }
    },
    [isLoading, addChatMessage, selectedModel]
  )

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      sendMessage(input)
    },
    [input, sendMessage]
  )

  const handleQuickPrompt = useCallback(
    (prompt: string) => {
      sendMessage(prompt)
    },
    [sendMessage]
  )

  const handleClearChat = useCallback(() => {
    clearChatMessages()
    if (typeof window !== 'undefined') {
      localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }, [clearChatMessages])

  const currentModel = AI_MODELS.find(m => m.id === selectedModel) ?? AI_MODELS[0]

  return (
    <>
      {/* Floating Chat Button */}
      <AnimatePresence>
        {!isChatOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={toggleChat}
            className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-shadow cursor-pointer"
            aria-label="Open NEXUS AI Assistant"
          >
            <Zap className="h-6 w-6 text-white" />
            {/* Notification dot when no messages */}
            {messageCount === 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-4 w-4 rounded-full bg-emerald-500" />
              </span>
            )}
            {/* Unread badge when messages exist */}
            {messageCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white">
                {messageCount > 9 ? '9+' : messageCount}
              </span>
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 z-50 flex h-full w-full sm:w-[420px] flex-col border-l border-border/60 bg-card/95 backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border/60 px-4 py-3 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700">
                  <Zap className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold tracking-wide">
                    NEXUS AI
                  </h3>
                  <div className="flex items-center gap-1.5">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
                      Online
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {/* Model Selector */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 gap-1.5 text-[10px] text-muted-foreground hover:text-foreground px-2"
                    >
                      <Cpu className="h-3 w-3" />
                      <span className="hidden sm:inline max-w-[70px] truncate">{currentModel.icon} {currentModel.label}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    {AI_MODELS.map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => setSelectedModel(model.id)}
                        className="flex items-center gap-2 cursor-pointer"
                      >
                        <span className="text-sm">{model.icon}</span>
                        <div className="flex-1">
                          <div className="text-xs font-medium">{model.label}</div>
                          <div className="text-[10px] text-muted-foreground">{model.description}</div>
                        </div>
                        {selectedModel === model.id && (
                          <span className="h-2 w-2 rounded-full bg-emerald-500" />
                        )}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                {chatMessages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={handleClearChat}
                    aria-label="Clear chat"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground"
                  onClick={() => setChatOpen(false)}
                  aria-label="Close chat"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Messages Area — Fixed scrolling with plain overflow-y-auto */}
            <div className="flex-1 min-h-0 relative">
              <div
                ref={scrollContainerRef}
                onScroll={handleScroll}
                className="h-full overflow-y-auto custom-scrollbar px-4 py-4 scroll-smooth"
              >
                {chatMessages.length === 0 && !isLoading && (
                  <div className="flex flex-col items-center justify-center gap-4 py-8 text-center">
                    <div className="relative">
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
                        <Sparkles className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500">
                        <Zap className="h-3 w-3 text-white" />
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold mb-1">
                        NEXUS AI Assistant
                      </h4>
                      <p className="text-xs text-muted-foreground max-w-[280px]">
                        Ask about system status, governance, StressLab results,
                        GMR routing, vault entries, or research pipeline.
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 w-full max-w-[300px] mt-2">
                      {QUICK_PROMPTS.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => handleQuickPrompt(prompt)}
                          className="text-left text-xs rounded-lg border border-border/60 bg-muted/50 px-3 py-2.5 hover:bg-emerald-500/10 hover:border-emerald-500/30 transition-colors cursor-pointer"
                        >
                          <span className="text-emerald-600 dark:text-emerald-400 mr-1.5">▸</span>
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {chatMessages.map((msg, i) => (
                  <MessageBubble key={`${msg.timestamp}-${i}`} message={msg} />
                ))}

                {isLoading && <TypingIndicator />}

                {/* Quick prompts when chat has messages */}
                {chatMessages.length > 0 && !isLoading && (
                  <div className="flex flex-wrap gap-1.5 mt-2 mb-2 px-1">
                    {QUICK_PROMPTS.slice(0, 4).map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => handleQuickPrompt(prompt)}
                        className="text-[10px] rounded-full border border-border/60 bg-muted/50 px-2.5 py-1 hover:bg-emerald-500/10 hover:border-emerald-500/30 transition-colors cursor-pointer"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                )}

                {/* Invisible anchor for scroll-to-bottom */}
                <div ref={messagesEndRef} />
              </div>

              {/* Scroll-to-bottom indicator */}
              <AnimatePresence>
                {!isAtBottom && chatMessages.length > 0 && (
                  <ScrollToBottom onClick={() => scrollToBottom('smooth')} />
                )}
              </AnimatePresence>
            </div>

            {/* Input Area */}
            <div className="border-t border-border/60 p-3 shrink-0">
              <form onSubmit={handleSubmit} className="flex items-center gap-2">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask NEXUS AI..."
                  disabled={isLoading}
                  className="flex-1 h-9 text-sm bg-muted/50 border-border/60 focus-visible:border-emerald-500/50 focus-visible:ring-emerald-500/20"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={!input.trim() || isLoading}
                  className="h-9 w-9 shrink-0 bg-gradient-to-br from-emerald-500 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 text-white shadow-sm disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </form>
              <div className="mt-2 flex items-center justify-between">
                <p className="text-[10px] text-muted-foreground">
                  NEXUS OS v3.1 · {currentModel.icon} {currentModel.label}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {messageCount} messages
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Backdrop for mobile */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setChatOpen(false)}
            className="fixed inset-0 z-40 bg-black/40 sm:hidden"
          />
        )}
      </AnimatePresence>
    </>
  )
}
