'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Send, Bot, User, Trash2, Loader2, Sparkles, Copy, Check, AlertCircle, RotateCcw, Brain, Zap, Code, Scale } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  model?: string
  error?: boolean
}

const AI_MODELS = [
  // Reasoning tier
  { id: 'glm-4-7-nim', name: 'GLM-4.7 (z-ai)', tier: 'reasoning' },
  { id: 'deepseek-r1-or', name: 'DeepSeek R1 (OpenRouter)', tier: 'reasoning' },
  { id: 'nemotron-4-340b-nim', name: 'Nemotron-4 340B (NVIDIA NIM)', tier: 'reasoning' },
  { id: 'llama-3.1-405b-nim', name: 'Llama 3.1 405B (NVIDIA NIM)', tier: 'reasoning' },
  { id: 'mistral-large-nim', name: 'Mistral Large (NVIDIA NIM)', tier: 'reasoning' },
  { id: 'deepseek-v3-sambanova', name: 'DeepSeek V3 (SambaNova)', tier: 'reasoning' },
  // Balanced tier
  { id: 'llama-3.3-70b-groq', name: 'Llama 3.3 70B (Groq)', tier: 'balanced' },
  { id: 'llama-3.3-70b-cerebras', name: 'Llama 3.3 70B (Cerebras)', tier: 'balanced' },
  { id: 'qwen3-coder-or', name: 'Qwen3 Coder (OpenRouter)', tier: 'balanced' },
  { id: 'trinity-large-or', name: 'Trinity Large (OpenRouter)', tier: 'balanced' },
  { id: 'llama-3.3-70b-sambanova', name: 'Llama 3.3 70B (SambaNova)', tier: 'balanced' },
  { id: 'gpt-4o-mini-openai', name: 'GPT-4o-mini (OpenAI)', tier: 'balanced' },
  { id: 'llama-3.1-70b-fireworks', name: 'Llama 3.1 70B (Fireworks)', tier: 'balanced' },
  { id: 'qwen2.5-72b-fireworks', name: 'Qwen2.5 72B (Fireworks)', tier: 'balanced' },
  { id: 'deepseek-v3-siliconflow', name: 'DeepSeek V3 (SiliconFlow)', tier: 'balanced' },
  { id: 'qwen2.5-72b-siliconflow', name: 'Qwen2.5 72B (SiliconFlow)', tier: 'balanced' },
  { id: 'mistral-medium-mistral', name: 'Mistral Medium (Mistral)', tier: 'balanced' },
  // Fast tier
  { id: 'step-3-5-flash-or', name: 'Step 3.5 Flash (OpenRouter)', tier: 'fast' },
  { id: 'gemma-4-26b-or', name: 'Gemma 4 26B (OpenRouter)', tier: 'fast' },
  { id: 'mixtral-8x7b-groq', name: 'Mixtral 8x7B (Groq)', tier: 'fast' },
  { id: 'gemma-2-9b-groq', name: 'Gemma 2 9B (Groq)', tier: 'fast' },
  { id: 'llama-3.1-8b-cerebras', name: 'Llama 3.1 8B (Cerebras)', tier: 'fast' },
  // Code tier
  { id: 'codestral-codestral', name: 'Codestral (Codestral)', tier: 'code' },
]

const TIER_CONFIG: Record<string, { label: string; icon: typeof Brain; color: string; description: string }> = {
  reasoning: { label: 'Reasoning', icon: Brain, color: 'text-violet-600 dark:text-violet-400', description: 'Best for complex reasoning & analysis' },
  balanced: { label: 'Balanced', icon: Scale, color: 'text-emerald-600 dark:text-emerald-400', description: 'Great quality-to-speed ratio' },
  fast: { label: 'Fast', icon: Zap, color: 'text-amber-600 dark:text-amber-400', description: 'Lowest latency responses' },
  code: { label: 'Code', icon: Code, color: 'text-cyan-600 dark:text-cyan-400', description: 'Optimized for code generation' },
}

const TIER_ORDER = ['reasoning', 'balanced', 'fast', 'code']

let msgCounter = 0
function generateId() {
  msgCounter++
  return `msg-${msgCounter}-${Math.random().toString(36).slice(2, 8)}`
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
  const [thinkingPhase, setThinkingPhase] = useState<'idle' | 'thinking' | 'responding'>('idle')
  const [mounted, setMounted] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Hydration-safe: set mounted flag after first render
  useEffect(() => {
    setMounted(true)
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent, thinkingPhase])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const clearChat = useCallback(() => {
    setMessages([])
    setStreamingContent('')
    setError(null)
    setThinkingPhase('idle')
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

  const regenerateLastResponse = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
    if (lastUserMsg) {
      // Remove the last assistant message
      setMessages(prev => {
        const lastAssistantIdx = [...prev].reverse().findIndex(m => m.role === 'assistant')
        if (lastAssistantIdx !== -1) {
          return prev.slice(0, prev.length - lastAssistantIdx - 1)
        }
        return prev
      })
      setError(null)
      // Re-send after state update
      setTimeout(() => {
        if (lastUserMsg) {
          sendMessage(lastUserMsg.content)
        }
      }, 50)
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
    setThinkingPhase('thinking')

    // Simulate thinking phase for 1.5 seconds before streaming begins
    const thinkingTimer = setTimeout(() => {
      setThinkingPhase('responding')
    }, 1500)

    try {
      // Build messages array for API (filter out system messages)
      const apiMessages = [...messages, userMessage]
        .filter(m => m.role !== 'system' && !m.error)
        .map(m => ({ role: m.role, content: m.content }))

      // Try streaming first
      const response = await fetch('/api/chat?stream=true', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          model: selectedModel,
        }),
      })

      if (!response.ok) {
        // Try non-streaming fallback
        const fallbackResponse = await fetch('/api/chat', {
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
        if (data.error) {
          throw new Error(data.error)
        }
        clearTimeout(thinkingTimer)
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: data.response || 'No response received',
          timestamp: Date.now(),
          model: data.model || selectedModel,
        }
        setMessages(prev => [...prev, assistantMessage])
        setIsLoading(false)
        setThinkingPhase('idle')
        toast.success('Response received', { description: `From ${data.model || selectedModel}` })
        return
      }

      // Process SSE stream
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''
      let firstChunkReceived = false

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
            clearTimeout(thinkingTimer)
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
            setThinkingPhase('idle')
            toast.success('Response received', { description: `From ${selectedModelInfo?.name || 'AI'}` })
            return
          }

          try {
            const parsed = JSON.parse(payload)
            if (parsed.error) {
              setError(parsed.error)
              continue
            }
            if (parsed.content) {
              if (!firstChunkReceived) {
                firstChunkReceived = true
                clearTimeout(thinkingTimer)
                setThinkingPhase('responding')
              }
              accumulated += parsed.content
              setStreamingContent(accumulated)
            }
          } catch {
            // Skip unparseable chunks
          }
        }
      }

      // If we get here without [DONE], save what we have
      clearTimeout(thinkingTimer)
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
      clearTimeout(thinkingTimer)
      const errorMsg = err instanceof Error ? err.message : 'Failed to get response'
      setError(errorMsg)
      toast.error('AI Assistant Error', { description: errorMsg })
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
      setThinkingPhase('idle')
      inputRef.current?.focus()
    }
  }, [messages, selectedModel, isLoading])

  const handleModelChange = useCallback((newModelId: string) => {
    const oldModel = AI_MODELS.find(m => m.id === selectedModel)
    const newModel = AI_MODELS.find(m => m.id === newModelId)
    
    if (newModel && oldModel && newModelId !== selectedModel) {
      // Add system message about model change
      const systemMsg: ChatMessage = {
        id: generateId(),
        role: 'system',
        content: `🔄 Model changed to: ${newModel.name}`,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, systemMsg])
    }
    
    setSelectedModel(newModelId)
  }, [selectedModel])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const selectedModelInfo = AI_MODELS.find(m => m.id === selectedModel)
  const lastAssistantMessageIndex = [...messages].reverse().findIndex(m => m.role === 'assistant')
  const lastAssistantIdx = lastAssistantMessageIndex !== -1 ? messages.length - 1 - lastAssistantMessageIndex : -1

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
          <Select value={selectedModel} onValueChange={handleModelChange}>
            <SelectTrigger className="w-[240px] h-8 text-xs">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {TIER_ORDER.map(tier => {
                const tierModels = AI_MODELS.filter(m => m.tier === tier)
                const tierConfig = TIER_CONFIG[tier]
                const TierIcon = tierConfig.icon
                return (
                  <div key={tier}>
                    <div className="flex items-center gap-1.5 px-2 py-1.5">
                      <TierIcon className={cn('h-3 w-3', tierConfig.color)} />
                      <span className={cn('text-[10px] font-semibold uppercase tracking-wider', tierConfig.color)}>
                        {tierConfig.label}
                      </span>
                      <span className="text-[9px] text-muted-foreground">— {tierConfig.description}</span>
                    </div>
                    {tierModels.map(model => (
                      <SelectItem key={model.id} value={model.id} className="text-xs">
                        <div className="flex items-center gap-2">
                          <span>{model.name}</span>
                          <Badge variant="outline" className={cn(
                            'h-3.5 px-1 text-[8px]',
                            tier === 'reasoning' && 'border-violet-600/30 text-violet-600',
                            tier === 'balanced' && 'border-emerald-600/30 text-emerald-600',
                            tier === 'fast' && 'border-amber-600/30 text-amber-600',
                            tier === 'code' && 'border-cyan-600/30 text-cyan-600',
                          )}>
                            {model.tier}
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </div>
                )
              })}
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

              {messages.map((msg, idx) => {
                // System messages - centered, subtle
                if (msg.role === 'system') {
                  return (
                    <div key={msg.id} className="flex justify-center">
                      <div className="text-[11px] text-muted-foreground/70 bg-muted/30 px-4 py-1.5 rounded-full border border-border/30">
                        {msg.content}
                      </div>
                    </div>
                  )
                }

                const isLastAssistant = msg.role === 'assistant' && idx === lastAssistantIdx && !isLoading

                return (
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
                      'max-w-[80%] rounded-xl px-4 py-2.5 text-sm group',
                      msg.role === 'user'
                        ? 'bg-emerald-600/10 text-foreground border border-emerald-600/20'
                        : msg.error
                          ? 'bg-red-500/5 border border-red-500/20 text-red-600 dark:text-red-400'
                          : 'bg-card border border-border/50'
                    )}>
                      <div className="prose-sm">
                        {msg.role === 'assistant' ? formatMessageContent(msg.content) : msg.content}
                      </div>
                      <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-border/30">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] text-muted-foreground font-mono">
                            {msg.model || selectedModelInfo?.name}
                          </span>
                          <span className="text-[9px] text-muted-foreground">
                            {mounted ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
                          </span>
                        </div>
                        {/* Regenerate button on last assistant message */}
                        {isLastAssistant && !msg.error && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 px-1.5 gap-1 text-[9px] text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={regenerateLastResponse}
                          >
                            <RotateCcw className="h-2.5 w-2.5" />
                            Regenerate
                          </Button>
                        )}
                      </div>
                    </div>

                    {msg.role === 'user' && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <User className="h-4 w-4 text-primary" />
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Thinking phase indicator */}
              {thinkingPhase === 'thinking' && !streamingContent && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-violet-600/10">
                    <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400 animate-pulse" />
                  </div>
                  <div className="rounded-xl px-4 py-3 text-sm bg-card border border-violet-500/20">
                    <div className="flex items-center gap-2">
                      <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400 animate-pulse" />
                      <span className="text-xs text-violet-600 dark:text-violet-400 font-medium">
                        Thinking...
                      </span>
                      <span className="text-[9px] text-muted-foreground font-mono">
                        {selectedModelInfo?.name}
                      </span>
                    </div>
                    <div className="mt-2 flex gap-1">
                      {[0, 1, 2].map(i => (
                        <div
                          key={i}
                          className="h-1 w-4 rounded-full bg-violet-500/30 animate-pulse"
                          style={{ animationDelay: `${i * 0.2}s` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Responding phase - streaming content */}
              {thinkingPhase === 'responding' && streamingContent && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                    <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="max-w-[80%] rounded-xl px-4 py-2.5 text-sm bg-card border border-emerald-500/20">
                    <div className="prose-sm">
                      {formatMessageContent(streamingContent)}
                    </div>
                    <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-border/30">
                      <Loader2 className="h-3 w-3 animate-spin text-emerald-500" />
                      <span className="text-[9px] text-emerald-600 dark:text-emerald-400 font-mono">
                        {selectedModelInfo?.name} — Responding...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Fallback loading indicator (non-streaming, after thinking phase) */}
              {isLoading && thinkingPhase === 'responding' && !streamingContent && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                    <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                  </div>
                  <div className="rounded-xl px-4 py-3 text-sm bg-card border border-border/50">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                      <span className="text-xs text-muted-foreground">
                        {selectedModelInfo?.name} is processing...
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
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground shrink-0 flex-wrap">
        <span>Model: <span className="font-mono text-foreground">{selectedModelInfo?.name}</span></span>
        <span className="text-border">|</span>
        <span>Tier: <Badge variant="outline" className={cn(
          'h-3 px-1 text-[8px]',
          selectedModelInfo?.tier === 'reasoning' && 'border-violet-600/30 text-violet-600',
          selectedModelInfo?.tier === 'balanced' && 'border-emerald-600/30 text-emerald-600',
          selectedModelInfo?.tier === 'fast' && 'border-amber-600/30 text-amber-600',
          selectedModelInfo?.tier === 'code' && 'border-cyan-600/30 text-cyan-600',
        )}>{selectedModelInfo?.tier}</Badge></span>
        <span className="text-border">|</span>
        <span>Messages: <span className="font-mono text-foreground">{messages.filter(m => m.role !== 'system').length}</span></span>
        <span className="text-border">|</span>
        <span>{AI_MODELS.length} models available</span>
      </div>
    </div>
  )
}
