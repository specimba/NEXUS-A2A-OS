'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, X, Send, Trash2, Bot, User, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useNexusStore,
  ChatMessage,
} from '@/store/nexus-store'

const QUICK_PROMPTS = [
  'System Status',
  'Run StressLab Test',
  'Show Trust Scores',
  'Free Claude Models',
]

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 mb-4">
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
      className={`flex items-start gap-2 mb-4 ${isUser ? 'flex-row-reverse' : ''}`}
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
        className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'rounded-tr-none bg-gradient-to-br from-emerald-500 to-emerald-700 text-white'
            : 'rounded-tl-none bg-muted text-foreground'
        }`}
      >
        {message.content}
      </div>
    </motion.div>
  )
}

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
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        '[data-slot="scroll-area-viewport"]'
      )
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [chatMessages, isLoading, scrollToBottom])

  useEffect(() => {
    if (isChatOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isChatOpen])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      const trimmed = content.trim()
      setInput('')

      // Get current messages BEFORE adding the new user message to avoid duplication
      const currentMessages = useNexusStore.getState().chatMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }))

      // Add user message to store
      addChatMessage({ role: 'user', content: trimmed })
      setIsLoading(true)

      try {
        // Try free Claude proxy first (port 8082)
        let response: Response | null = null
        let usedEndpoint = ''

        try {
          response = await fetch('/api/claude', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: [
                ...currentMessages,
                { role: 'user', content: trimmed },
              ],
            }),
          })
          if (response.ok) {
            usedEndpoint = 'claude-proxy'
          } else {
            response = null
          }
        } catch {
          // Free Claude proxy not available, fall through
          response = null
        }

        // Fallback to z-ai-web-dev-sdk
        if (!response) {
          response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: [
                ...currentMessages,
                { role: 'user', content: trimmed },
              ],
            }),
          })
          usedEndpoint = 'z-ai-sdk'
        }

        if (!response.ok) {
          throw new Error('Failed to get response')
        }

        const data = await response.json()
        const modelInfo = data.model ? ` [via ${data.model}]` : usedEndpoint === 'claude-proxy' ? ' [free Claude]' : ''
        addChatMessage({ role: 'assistant', content: data.response + modelInfo })
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
    [isLoading, addChatMessage]
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
            {/* Notification dot */}
            {chatMessages.length === 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-4 w-4 rounded-full bg-emerald-500" />
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
            className="fixed right-0 top-0 z-50 flex h-full w-full sm:w-[400px] flex-col border-l border-border/60 bg-card/95 backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
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
                {chatMessages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={clearChatMessages}
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

            {/* Messages Area */}
            <ScrollArea ref={scrollRef} className="flex-1 px-4 py-4">
              {chatMessages.length === 0 && !isLoading && (
                <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
                    <MessageSquare className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold mb-1">
                      NEXUS AI Assistant
                    </h4>
                    <p className="text-xs text-muted-foreground max-w-[260px]">
                      Ask about system status, governance, StressLab results,
                      GMR routing, vault entries, or research pipeline.
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 w-full max-w-[280px] mt-2">
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
                <div className="flex flex-wrap gap-1.5 mt-2 mb-2">
                  {QUICK_PROMPTS.map((prompt) => (
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
            </ScrollArea>

            {/* Input Area */}
            <div className="border-t border-border/60 p-3">
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
              <p className="mt-2 text-center text-[10px] text-muted-foreground">
                NEXUS OS v3.0 · Governance Intelligence Layer
              </p>
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
