'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Send, Bot, User, Trash2, Loader2, Sparkles, Copy, Check, AlertCircle, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  model?: string
  error?: boolean
}

const AI_MODELS = [
  { id: 'glm-4-7-nim', name: 'GLM-4.7 (z-ai)', tier: 'reasoning' },
  { id: 'deepseek-r1-or', name: 'DeepSeek R1 (OR)', tier: 'reasoning' },
  { id: 'llama-3.3-70b-groq', name: 'Llama 3.3 70B (Groq)', tier: 'reasoning' },
  { id: 'llama-3.3-70b-cerebras', name: 'Llama 3.3 70B (Cerebras)', tier: 'reasoning' },
  { id: 'qwen3-coder-or', name: 'Qwen3 Coder (OR)', tier: 'balanced' },
  { id: 'trinity-large-or', name: 'Trinity Large (OR)', tier: 'balanced' },
  { id: 'step-3-5-flash-or', name: 'Step 3.5 Flash (OR)', tier: 'fast' },
  { id: 'gemma-4-26b-or', name: 'Gemma 4 26B (OR)', tier: 'fast' },
]

function generateId() {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-2 rounded-lg border border-border/50 bg-muted/50 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-muted/80 border-b border-border/50">
        <span className="text-[10px] font-mono text-muted-foreground">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-xs font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function formatMessageContent(content: string) {
  // Simple markdown-like rendering
  const parts: React.ReactNode[] = []
  let remaining = content
  let keyIndex = 0

  // Handle code blocks
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(remaining)) !== null) {
    // Add text before code block
    if (match.index > lastIndex) {
      const textBefore = remaining.slice(lastIndex, match.index)
      parts.push(renderInlineMarkdown(textBefore, keyIndex))
      keyIndex++
    }

    // Add code block
    parts.push(
      <CodeBlock key={`code-${keyIndex++}`} code={match[2].trim()} language={match[1] || undefined} />
    )
    lastIndex = match.index + match[0].length
  }

  // Add remaining text after last code block
  if (lastIndex < remaining.length) {
    parts.push(renderInlineMarkdown(remaining.slice(lastIndex), keyIndex))
  }

  return parts.length > 0 ? parts : content
}

function renderInlineMarkdown(text: string, baseKey: number): React.ReactNode {
  // Split by lines for paragraph handling
  const lines = text.split('\n')
  return lines.map((line, i) => {
    const key = `inline-${baseKey}-${i}`

    // Headers
    if (line.startsWith('### ')) {
      return <h4 key={key} className="font-bold text-sm mt-3 mb-1">{line.slice(4)}</h4>
    }
    if (line.startsWith('## ')) {
      return <h3 key={key} className="font-bold text-base mt-3 mb-1">{line.slice(3)}</h3>
    }
    if (line.startsWith('# ')) {
      return <h2 key={key} className="font-bold text-lg mt-3 mb-1">{line.slice(2)}</h2>
    }

    // List items
    if (line.startsWith('- ') || line.startsWith('* ')) {
      return (
        <div key={key} className="flex gap-2 ml-2">
          <span className="text-emerald-500 shrink-0">•</span>
          <span>{renderInlineFormatting(line.slice(2))}</span>
        </div>
      )
    }

    // Numbered list
    const numMatch = line.match(/^(\d+)\.\s/)
    if (numMatch) {
      return (
        <div key={key} className="flex gap-2 ml-2">
          <span className="text-emerald-500 shrink-0 font-mono text-xs">{numMatch[1]}.</span>
          <span>{renderInlineFormatting(line.slice(numMatch[0].length))}</span>
        </div>
      )
    }

    // Empty line = paragraph break
    if (line.trim() === '') {
      return <div key={key} className="h-2" />
    }

    // Regular text
    return <p key={key} className="leading-relaxed">{renderInlineFormatting(line)}</p>
  })
}

function renderInlineFormatting(text: string): React.ReactNode {
  // Bold
  const parts: React.ReactNode[] = []
  const boldRegex = /\*\*(.*?)\*\*/g
  let lastIdx = 0
  let bMatch
  let idx = 0

  while ((bMatch = boldRegex.exec(text)) !== null) {
    if (bMatch.index > lastIdx) {
      parts.push(text.slice(lastIdx, bMatch.index))
    }
    parts.push(<strong key={`b-${idx++}`} className="font-semibold">{bMatch[1]}</strong>)
    lastIdx = bMatch.index + bMatch[0].length
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx))
  }

  // Inline code
  const result: React.ReactNode[] = []
  for (const part of parts) {
    if (typeof part !== 'string') {
      result.push(part)
      continue
    }
    const codeRegex = /`([^`]+)`/g
    let cLastIdx = 0
    let cMatch
    let cIdx = 0
    while ((cMatch = codeRegex.exec(part)) !== null) {
      if (cMatch.index > cLastIdx) {
        result.push(part.slice(cLastIdx, cMatch.index))
      }
      result.push(
        <code key={`c-${cIdx++}`} className="px-1.5 py-0.5 rounded bg-muted/80 text-emerald-600 dark:text-emerald-400 text-xs font-mono">
          {cMatch[1]}
        </code>
      )
      cLastIdx = cMatch.index + cMatch[0].length
    }
    if (cLastIdx < part.length) {
      result.push(part.slice(cLastIdx))
    }
  }

  return result.length > 0 ? result : text
}

export function AiChatTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState('glm-4-7-nim')
  const [streamingContent, setStreamingContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const clearChat = useCallback(() => {
    setMessages([])
    setStreamingContent('')
    setError(null)
  }, [])

  const retryLastMessage = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
    if (lastUserMsg) {
      setMessages(prev => prev.slice(0, -1)) // Remove last assistant message (likely error)
      setError(null)
      // Re-send
      sendMessage(lastUserMsg.content)
    }
  }, [messages, selectedModel])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setStreamingContent('')
    setError(null)

    try {
      // Build messages array for API
      const apiMessages = [...messages, userMessage]
        .filter(m => !m.error)
        .map(m => ({ role: m.role, content: m.content }))

      // Try streaming first
      const response = await fetch('/api/ai/chat?stream=true', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          model: selectedModel,
        }),
      })

      if (!response.ok) {
        // Try non-streaming fallback
        const fallbackResponse = await fetch('/api/ai/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: apiMessages,
            model: selectedModel,
          }),
        })

        if (!fallbackResponse.ok) {
          throw new Error(`API error: ${fallbackResponse.status}`)
        }

        const data = await fallbackResponse.json()
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: data.response || data.error || 'No response received',
          timestamp: Date.now(),
          model: data.model || selectedModel,
          error: !!data.error,
        }
        setMessages(prev => [...prev, assistantMessage])
        setIsLoading(false)
        return
      }

      // Process SSE stream
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data:')) continue

          const payload = trimmed.slice(5).trim()
          if (payload === '[DONE]') {
            // Stream complete
            const assistantMessage: ChatMessage = {
              id: generateId(),
              role: 'assistant',
              content: accumulated,
              timestamp: Date.now(),
              model: selectedModel,
            }
            setMessages(prev => [...prev, assistantMessage])
            setStreamingContent('')
            setIsLoading(false)
            return
          }

          try {
            const parsed = JSON.parse(payload)
            if (parsed.error) {
              setError(parsed.error)
              continue
            }
            if (parsed.content) {
              accumulated += parsed.content
              setStreamingContent(accumulated)
            }
          } catch {
            // Skip unparseable chunks
          }
        }
      }

      // If we get here without [DONE], save what we have
      if (accumulated) {
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: accumulated,
          timestamp: Date.now(),
          model: selectedModel,
        }
        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to get response'
      setError(errorMsg)
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Error: ${errorMsg}`,
        timestamp: Date.now(),
        model: selectedModel,
        error: true,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setStreamingContent('')
      inputRef.current?.focus()
    }
  }, [messages, selectedModel, isLoading])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const selectedModelInfo = AI_MODELS.find(m => m.id === selectedModel)

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">AI Assistant</h2>
          <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
            AI
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="w-[200px] h-8 text-xs">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {AI_MODELS.map(model => (
                <SelectItem key={model.id} value={model.id} className="text-xs">
                  <div className="flex items-center gap-2">
                    <span>{model.name}</span>
                    <Badge variant="outline" className="h-3.5 px-1 text-[8px] border-emerald-600/30 text-emerald-600">
                      {model.tier}
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 h-8"
            onClick={clearChat}
            disabled={messages.length === 0}
          >
            <Trash2 className="h-3 w-3" />
            Clear
          </Button>
        </div>
      </div>

      {/* Chat Area */}
      <Card className="flex-1 bg-card/50 border-border/50 flex flex-col overflow-hidden min-h-0">
        <CardContent className="flex-1 p-0 flex flex-col min-h-0">
          <ScrollArea className="flex-1" ref={scrollRef}>
            <div className="p-4 space-y-4">
              {messages.length === 0 && !streamingContent && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 mb-4">
                    <Bot className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <h3 className="text-sm font-semibold mb-1">NEXUS OS AI Assistant</h3>
                  <p className="text-xs text-muted-foreground max-w-sm">
                    Ask about system status, governance decisions, StressLab tests, GMR routing, or any aspect of the NEXUS platform.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-4 max-w-md">
                    {[
                      'What is the current system status?',
                      'Explain the GMR model routing',
                      'How does the Governor work?',
                      'What is the Vault memory plane?',
                    ].map(suggestion => (
                      <button
                        key={suggestion}
                        onClick={() => sendMessage(suggestion)}
                        className="text-xs px-3 py-1.5 rounded-full border border-border/50 bg-card/80 hover:bg-emerald-600/10 hover:border-emerald-600/30 transition-all duration-200 text-muted-foreground hover:text-foreground"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'flex gap-3',
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {msg.role === 'assistant' && (
                    <div className={cn(
                      'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg',
                      msg.error
                        ? 'bg-red-500/10'
                        : 'bg-gradient-to-br from-emerald-500/20 to-emerald-600/10'
                    )}>
                      <Bot className={cn(
                        'h-4 w-4',
                        msg.error ? 'text-red-500' : 'text-emerald-600 dark:text-emerald-400'
                      )} />
                    </div>
                  )}

                  <div className={cn(
                    'max-w-[80%] rounded-xl px-4 py-2.5 text-sm',
                    msg.role === 'user'
                      ? 'bg-emerald-600/10 text-foreground border border-emerald-600/20'
                      : msg.error
                        ? 'bg-red-500/5 border border-red-500/20 text-red-600 dark:text-red-400'
                        : 'bg-card border border-border/50'
                  )}>
                    <div className="prose-sm">
                      {msg.role === 'assistant' ? formatMessageContent(msg.content) : msg.content}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 pt-1.5 border-t border-border/30">
                      <span className="text-[9px] text-muted-foreground font-mono">
                        {msg.model || selectedModelInfo?.name}
                      </span>
                      <span className="text-[9px] text-muted-foreground">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  {msg.role === 'user' && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming content */}
              {streamingContent && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                    <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="max-w-[80%] rounded-xl px-4 py-2.5 text-sm bg-card border border-border/50">
                    <div className="prose-sm">
                      {formatMessageContent(streamingContent)}
                    </div>
                    <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-border/30">
                      <Loader2 className="h-3 w-3 animate-spin text-emerald-500" />
                      <span className="text-[9px] text-emerald-600 dark:text-emerald-400 font-mono">
                        {selectedModelInfo?.name} — streaming...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Loading indicator (non-streaming) */}
              {isLoading && !streamingContent && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                    <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="rounded-xl px-4 py-3 text-sm bg-card border border-border/50">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                      <span className="text-xs text-muted-foreground">
                        {selectedModelInfo?.name} is thinking...
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Error Bar */}
      {error && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 shrink-0">
          <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
          <span className="text-xs text-red-600 dark:text-red-400 flex-1">{error}</span>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 text-xs gap-1 text-red-500 hover:text-red-600"
            onClick={retryLastMessage}
          >
            <RotateCcw className="h-3 w-3" />
            Retry
          </Button>
        </div>
      )}

      {/* Input Area */}
      <div className="flex gap-2 shrink-0">
        <div className="flex-1 relative">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask ${selectedModelInfo?.name || 'AI'} anything...`}
            disabled={isLoading}
            className="pr-10 h-10 text-sm"
          />
        </div>
        <Button
          onClick={() => sendMessage(input)}
          disabled={isLoading || !input.trim()}
          className="h-10 px-4 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Send
        </Button>
      </div>

      {/* Model Info Footer */}
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground shrink-0">
        <span>Model: <span className="font-mono text-foreground">{selectedModelInfo?.name}</span></span>
        <span className="text-border">|</span>
        <span>Tier: <Badge variant="outline" className="h-3 px-1 text-[8px] border-emerald-600/30 text-emerald-600">{selectedModelInfo?.tier}</Badge></span>
        <span className="text-border">|</span>
        <span>Messages: <span className="font-mono text-foreground">{messages.length}</span></span>
        <span className="text-border">|</span>
        <span>All models are open-source via free-tier APIs</span>
      </div>
    </div>
  )
}
