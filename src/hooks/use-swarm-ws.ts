'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'

// ─── Event Types ───

export interface WorkerUpdate {
  workerId: string
  status: 'busy' | 'idle' | 'error'
  task: string | null
  progress: number
  tokens: number
  domain?: string | null
}

export interface TaskComplete {
  taskId: string
  workerId: string
  result: 'success' | 'failure'
  duration: string
  tokens: number
}

export interface TaskQueued {
  taskId: string
  domain: string
  priority: 'high' | 'medium' | 'low'
  submittedBy: string
}

export interface SwarmMetrics {
  throughput: number
  avgDuration: number
  successRate: number
  utilization: number
  totalTokens: number
}

export interface NexusActivity {
  type: 'info' | 'success' | 'warning' | 'error'
  source: string
  message: string
  timestamp: number
}

export interface SwarmWSState {
  connected: boolean
  workers: Record<string, WorkerUpdate>
  recentCompletions: TaskComplete[]
  taskQueue: TaskQueued[]
  metrics: SwarmMetrics | null
  activities: NexusActivity[]
  lastUpdate: number | null
}

const INITIAL_STATE: SwarmWSState = {
  connected: false,
  workers: {},
  recentCompletions: [],
  taskQueue: [],
  metrics: null,
  activities: [],
  lastUpdate: null,
}

export function useSwarmWS() {
  const [state, setState] = useState<SwarmWSState>(INITIAL_STATE)
  const socketRef = useRef<Socket | null>(null)
  const reconnectAttemptRef = useRef(0)

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return

    const socket = io('/?XTransformPort=3003', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 10000,
      timeout: 10000,
    })

    socket.on('connect', () => {
      reconnectAttemptRef.current = 0
      setState(prev => ({ ...prev, connected: true }))
    })

    socket.on('disconnect', () => {
      setState(prev => ({ ...prev, connected: false }))
    })

    socket.on('connect_error', () => {
      reconnectAttemptRef.current++
    })

    socket.on('swarm:worker-update', (data: WorkerUpdate) => {
      setState(prev => ({
        ...prev,
        workers: { ...prev.workers, [data.workerId]: data },
        lastUpdate: Date.now(),
      }))
    })

    socket.on('swarm:task-complete', (data: TaskComplete) => {
      setState(prev => ({
        ...prev,
        recentCompletions: [data, ...prev.recentCompletions].slice(0, 20),
        lastUpdate: Date.now(),
      }))
    })

    socket.on('swarm:task-queued', (data: TaskQueued) => {
      setState(prev => ({
        ...prev,
        taskQueue: [...prev.taskQueue, data].slice(-15),
        lastUpdate: Date.now(),
      }))
    })

    socket.on('swarm:metrics', (data: SwarmMetrics) => {
      setState(prev => ({
        ...prev,
        metrics: data,
        lastUpdate: Date.now(),
      }))
    })

    socket.on('nexus:activity', (data: NexusActivity) => {
      setState(prev => ({
        ...prev,
        activities: [data, ...prev.activities].slice(0, 30),
        lastUpdate: Date.now(),
      }))
    })

    socketRef.current = socket
  }, [])

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect()
    socketRef.current = null
  }, [])

  const assignTask = useCallback((taskId: string, workerId: string) => {
    if (!socketRef.current?.connected) return false
    socketRef.current.emit('swarm:assign-task', { taskId, workerId })
    return true
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    ...state,
    assignTask,
    reconnect: connect,
  }
}
