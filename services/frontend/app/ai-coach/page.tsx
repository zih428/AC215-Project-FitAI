'use client'

import { useState, useEffect, useCallback } from 'react'
import { Send, Bot, User as UserIcon, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'
import Link from 'next/link'
import { getPipelineBaseUrl, getRagBaseUrl } from '@/apiConfig'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  source?: 'rag' | 'fallback'
  metadata?: {
    context_chunks_count?: number
    method?: string
  }
}

interface ConnectionStatus {
  status: 'checking' | 'connected' | 'disconnected'
  message: string
}

interface ProfileResponse {
  id: number
  full_name: string
  height_cm: number
  weight_kg: number
  body_type: string
  gender: string
  age_years: number
  training_goal: string
}

const STORAGE_KEY = 'fitai-ai-coach-messages'
const PROFILE_STORAGE_KEY = 'fitai-profile-user-id'
const PROFILE_CACHE_KEY = 'fitai-profile-data'
const AUTH_TOKEN_KEY = 'fitai-auth-token'
const PROFILE_UPDATED_EVENT = 'fitai-profile-updated'
const PIPELINE_BASE_URL = getPipelineBaseUrl()
const RAG_BASE_URL = getRagBaseUrl()

const createDefaultMessages = (): Message[] => [
  {
    id: Date.now().toString(),
    role: 'assistant',
    content:
      "Hello! I'm your AI fitness coach. How can I help you today? You can ask me about workout plans, nutrition advice, or any fitness-related questions.",
    timestamp: new Date(),
    source: 'rag',
  },
]

export default function AICoach() {
  const [messages, setMessages] = useState<Message[]>(createDefaultMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    status: 'checking',
    message: 'Checking RAG service connection...',
  })
  const [showDebug, setShowDebug] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [profile, setProfile] = useState<ProfileResponse | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [collectionsStatus, setCollectionsStatus] = useState<'checking' | 'ready' | 'empty' | 'error'>('checking')
  const collectionsReady = collectionsStatus === 'ready'
  const profileComplete =
    !!profile &&
    profile.full_name &&
    profile.height_cm != null &&
    profile.weight_kg != null &&
    profile.body_type &&
    profile.gender &&
    profile.age_years != null &&
    profile.training_goal

  // Restore chat history from browser storage
  useEffect(() => {
    if (typeof window === 'undefined') return

    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      if (stored) {
        type StoredMessage = Omit<Message, 'timestamp'> & { timestamp: string }
        const parsed = JSON.parse(stored) as StoredMessage[]
        const restored = parsed.map((message) => ({
          ...message,
          timestamp: new Date(message.timestamp),
        }))
        setMessages(restored)
      }
    } catch (error) {
      console.error('Failed to load AI Coach history from storage:', error)
      window.localStorage.removeItem(STORAGE_KEY)
    } finally {
      setIsHydrated(true)
    }
  }, [])

  const fetchProfile = useCallback(
    async ({ userId, token }: { userId?: number | null; token?: string | null }) => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      let url: string | null = null

      if (token) {
        url = `${PIPELINE_BASE_URL}/users/me`
        headers.Authorization = `Bearer ${token}`
      } else if (userId) {
        url = `${PIPELINE_BASE_URL}/users/${userId}`
      }

      if (!url) {
        setProfile(null)
        setProfileError('Profile unavailable. Save your profile to personalize responses.')
        return
      }

      try {
        const response = await fetch(url, { headers })
        if (!response.ok) {
          throw new Error('Unable to load profile.')
        }
        const data: ProfileResponse = await response.json()
        setProfile(data)
        setProfileId(data.id)
        setProfileError(null)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(PROFILE_STORAGE_KEY, data.id.toString())
          window.localStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(data))
          window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
        }
      } catch (error) {
        console.error('Failed to load profile for AI Coach:', error)
        setProfile(null)
        setProfileError('Profile unavailable. Save your profile to personalize responses.')
      }
    },
    []
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    const refreshProfile = () => {
      const token = window.localStorage.getItem(AUTH_TOKEN_KEY)
      const cached = window.localStorage.getItem(PROFILE_CACHE_KEY)
      const storedId = window.localStorage.getItem(PROFILE_STORAGE_KEY)
      const parsedId = storedId ? Number(storedId) : null
      const nextProfileId = Number.isFinite(parsedId) ? parsedId : null

      if (cached) {
        try {
          const parsed = JSON.parse(cached) as ProfileResponse
          setProfile(parsed)
          setProfileId(parsed.id ?? nextProfileId)
          setProfileError(null)
        } catch (error) {
          console.error('Failed to restore cached profile:', error)
          setProfile(null)
        }
      } else {
        setProfileId(nextProfileId)
      }

      if (token) {
        void fetchProfile({ token })
        return
      }

      if (nextProfileId) {
        void fetchProfile({ userId: nextProfileId })
        return
      }

      setProfile(null)
      setProfileError('Profile unavailable. Save your profile to personalize responses.')
    }

    refreshProfile()
    window.addEventListener(PROFILE_UPDATED_EVENT, refreshProfile)
    return () => window.removeEventListener(PROFILE_UPDATED_EVENT, refreshProfile)
  }, [fetchProfile])

  // Persist chat history whenever it changes
  useEffect(() => {
    if (!isHydrated || typeof window === 'undefined') return

    try {
      const serializable = messages.map((message) => ({
        ...message,
        timestamp: message.timestamp.toISOString(),
      }))
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable))
    } catch (error) {
      console.error('Failed to save AI Coach history to storage:', error)
    }
  }, [messages, isHydrated])

  // Check RAG service connection on component mount
  useEffect(() => {
    checkRAGConnection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const checkRAGConnection = async () => {
    try {
      const response = await fetch(`${RAG_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.status === 'ok' && data.service === 'rag-service') {
          setConnectionStatus({
            status: 'connected',
            message: 'Connected to RAG service',
          })
          return
        } else {
          console.error('Invalid response format:', data)
          setConnectionStatus({
            status: 'disconnected',
            message: `RAG service not responding correctly: ${JSON.stringify(data)}`,
          })
          return
        }
      } else {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
    } catch (error) {
      console.error('RAG service connection error:', error)
      const errorMessage = error instanceof Error ? error.message : String(error)
      setConnectionStatus({
        status: 'disconnected',
        message: `Cannot connect to RAG service: ${errorMessage}`,
      })
    }
  }

  // Check if collections exist (gate UI until embeddings are present)
  const checkCollections = useCallback(async () => {
    try {
      const res = await fetch(`${RAG_BASE_URL}/collections`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const list = Array.isArray(data?.collections) ? data.collections : []
      setCollectionsStatus(list.length > 0 ? 'ready' : 'empty')
      return list.length > 0
    } catch {
      setCollectionsStatus('error')
      return false
    }
  }, [])

  useEffect(() => {
    checkCollections()
    const timer = setInterval(checkCollections, 5000)
    return () => clearInterval(timer)
  }, [checkCollections])

  const handleSend = async () => {
    if (!input.trim() || isLoading || !profileComplete) return

    // Double-check collections status before sending
    if (!collectionsReady) {
      console.warn('Cannot send message: collections not ready')
      return
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const userInput = input
    setInput('')
    setIsLoading(true)

    // Call RAG pipeline API
    try {
      const response = await fetch(`${RAG_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userInput,
          method: 'semantic-split',
          n_results: 10,
          user_profile: profile
            ? {
                id: profile.id,
                full_name: profile.full_name,
                height_cm: profile.height_cm,
                weight_kg: profile.weight_kg,
                body_type: profile.body_type,
                gender: profile.gender,
                age_years: profile.age_years,
                training_goal: profile.training_goal,
              }
            : null,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        
        // Verify this is a real RAG response
        if (data.status === 'success' && data.response) {
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: data.response,
            timestamp: new Date(),
            source: 'rag',
            metadata: {
              context_chunks_count: data.context_chunks_count,
              method: data.method,
            },
          }
          setMessages((prev) => [...prev, assistantMessage])
          
          // Update connection status if it was disconnected
          if (connectionStatus.status === 'disconnected') {
            setConnectionStatus({
              status: 'connected',
              message: 'Connected to RAG service',
            })
          }
        } else {
          throw new Error('Invalid response format from RAG service')
        }
      } else {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        
        // Check if error is about missing collection - recheck collections status
        if (errorMessage.includes('not found') || errorMessage.includes('Collection')) {
          // Recheck collections to get actual status (not just check error message)
          const hasCollections = await checkCollections()
          if (!hasCollections) {
            // Collections are actually empty - remove user message silently
            setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id))
            console.warn('Collections not available, message not sent')
            return
          }
        }
        
        throw new Error(errorMessage)
      }
    } catch (error) {
      console.error('RAG service error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      
      // Check if error is about missing collection - recheck collections status
      if (errorMessage.includes('not found') || errorMessage.includes('Collection')) {
        // Recheck collections to get actual status (not just check error message)
        const hasCollections = await checkCollections()
        if (!hasCollections) {
          // Collections are actually empty - remove user message silently
          // Don't update connectionStatus - service is fine, just no collections
          setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id))
          console.warn('Collections not available, message not sent')
          return
        }
      }
      
      // For other errors (not collection-related), update connection status
      // But still don't show error message in chat
      setConnectionStatus({
        status: 'disconnected',
        message: `Connection failed`,
      })
      
      // Remove user message since we can't process it
      setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id))
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClearConversation = () => {
    if (isLoading) return
    const initialMessages = createDefaultMessages()
    setMessages(initialMessages)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(
          initialMessages.map((message) => ({
            ...message,
            timestamp: message.timestamp.toISOString(),
          }))
        )
      )
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-8 border-b border-gray-200 bg-white">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div className="space-y-2">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Coach</h1>
              <p className="text-gray-600">
                Get personalized fitness advice powered by AI & scientific research
              </p>
            </div>
            {profile ? (
              <p className="text-sm text-gray-600">
                Chatting as <span className="font-semibold">{profile.full_name}</span> (
                {profile.age_years} yrs, {profile.body_type}, {profile.weight_kg} kg)
              </p>
            ) : (
              <p className="text-sm text-gray-500">
                Save your{' '}
                <Link className="text-primary-600 underline" href="/profile">
                  profile
                </Link>{' '}
                to personalize responses.
              </p>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleClearConversation}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Clear Conversation
            </button>
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {showDebug ? 'Hide' : 'Show'} Debug
            </button>
          </div>
        </div>
        
        {/* Connection Status */}
        <div className="flex items-center space-x-3">
          {connectionStatus.status === 'connected' ? (
            <div className="flex items-center space-x-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              <span className="text-sm font-medium">{connectionStatus.message}</span>
            </div>
          ) : connectionStatus.status === 'checking' ? (
            <div className="flex items-center space-x-2 text-yellow-600">
              <AlertCircle className="w-5 h-5 animate-pulse" />
              <span className="text-sm font-medium">{connectionStatus.message}</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-red-600">
              <XCircle className="w-5 h-5" />
              <span className="text-sm font-medium">{connectionStatus.message}</span>
            </div>
          )}
          <button
            onClick={checkRAGConnection}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            Recheck
          </button>
        </div>

        {/* Debug Info */}
        {showDebug && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center space-x-2 mb-2">
              <Info className="w-4 h-4 text-gray-600" />
              <span className="text-sm font-semibold text-gray-700">Debug Information</span>
            </div>
            <div className="text-xs text-gray-600 space-y-1 font-mono">
              <div>API Endpoint: <span className="text-blue-600">{`${RAG_BASE_URL}/chat`}</span></div>
              <div>Health Check: <span className="text-blue-600">{`${RAG_BASE_URL}/health`}</span></div>
              <div>Collections: <span className="text-blue-600">{`${RAG_BASE_URL}/collections`}</span></div>
              <div>Status: <span className={connectionStatus.status === 'connected' ? 'text-green-600' : 'text-red-600'}>{connectionStatus.status}</span></div>
              <div>Collections Status: <span className={
                collectionsStatus === 'ready' ? 'text-green-600'
                : collectionsStatus === 'checking' ? 'text-yellow-600'
                : 'text-red-600'
              }>{collectionsStatus}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Profile alerts */}
      {!profile && profileError && (
        <div className="mx-8 mt-4">
          <div className="max-w-4xl mx-auto border border-yellow-200 bg-yellow-50 text-yellow-800 px-4 py-3 rounded-lg text-sm">
            {profileError}{' '}
            <Link href="/profile" className="underline font-medium">
              Update profile
            </Link>
            .
          </div>
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex items-start space-x-4 ${
                message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                  message.role === 'user'
                    ? 'bg-primary-500'
                    : 'bg-blue-500'
                }`}
              >
                {message.role === 'user' ? (
                  <UserIcon className="w-5 h-5 text-white" />
                ) : (
                  <Bot className="w-5 h-5 text-white" />
                )}
              </div>
              <div
                className={`flex-1 rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-white border border-gray-200 text-gray-900'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <div className="flex items-center justify-between mt-2">
                  <p
                    className={`text-xs ${
                      message.role === 'user'
                        ? 'text-primary-100'
                        : 'text-gray-500'
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                  {message.role === 'assistant' && message.metadata && (
                    <div className="flex items-center space-x-2">
                      {message.source === 'rag' ? (
                        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                          ✓ RAG
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full">
                          ⚠ Fallback
                        </span>
                      )}
                      {message.metadata.context_chunks_count !== undefined && (
                        <span className="text-xs text-gray-400">
                          {message.metadata.context_chunks_count} chunks
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 rounded-lg p-4 bg-white border border-gray-200">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-8 border-t border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto">
          {collectionsStatus !== 'ready' && (
            <div className="mb-3 text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2">
              {collectionsStatus === 'checking' && 'Checking knowledge base readiness…'}
              {collectionsStatus === 'empty' && 'Knowledge base is empty. Building embeddings — please wait or trigger ingestion.'}
              {collectionsStatus === 'error' && 'Unable to verify knowledge base. Ensure RAG service is running and collections are available.'}
            </div>
          )}
          {!profileComplete && (
            <div className="mb-3 text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
              Complete your profile to enable chat responses.{' '}
              <Link className="underline font-medium" href="/profile">
                Go to profile
              </Link>
              .
            </div>
          )}
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about fitness, workouts, or nutrition..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                rows={3}
                disabled={!collectionsReady || !profileComplete}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading || !collectionsReady || !profileComplete}
              className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
            >
              <Send className="w-5 h-5" />
              <span>Send</span>
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {profileComplete
              ? 'Press Enter to send, Shift+Enter for new line'
              : 'Fill out your profile to enable chatting.'}
          </p>
        </div>
      </div>
    </div>
  )
}
