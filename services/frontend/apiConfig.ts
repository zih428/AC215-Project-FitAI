const INTERNAL_DOCKER_HOSTS = new Set(['core-etl-api', 'rag-service', 'calendar-agent'])

const removeTrailingSlash = (value: string) => value.replace(/\/$/, '')

const browserOriginForPort = (port: number) => {
  if (typeof window === 'undefined') return null
  const protocol = window.location.protocol || 'http:'
  const hostname = window.location.hostname || 'localhost'
  if (!hostname) return null
  return `${protocol}//${hostname}:${port}`
}

const shouldSwapHostForBrowser = (hostname: string) => {
  if (hostname === 'localhost') {
    if (typeof window === 'undefined') return false
    return window.location.hostname !== 'localhost'
  }
  return INTERNAL_DOCKER_HOSTS.has(hostname)
}

const resolveBaseUrl = (envValue: string | undefined, defaultPort: number) => {
  const trimmedEnv = envValue?.trim()
  const normalizedEnv = trimmedEnv ? removeTrailingSlash(trimmedEnv) : null

  if (typeof window === 'undefined') {
    return normalizedEnv ?? `http://localhost:${defaultPort}`
  }

  if (normalizedEnv) {
    try {
      const parsed = new URL(normalizedEnv)
      if (!shouldSwapHostForBrowser(parsed.hostname)) {
        return parsed.origin
      }
    } catch {
      // ignore invalid env URL
    }
  }

  const browserOrigin = browserOriginForPort(defaultPort)
  if (browserOrigin) {
    return browserOrigin
  }

  return normalizedEnv ?? `http://localhost:${defaultPort}`
}

export const getPipelineBaseUrl = () =>
  resolveBaseUrl(process.env.NEXT_PUBLIC_PIPELINE_URL, 8001)

export const getCalendarAgentBaseUrl = () =>
  resolveBaseUrl(process.env.NEXT_PUBLIC_CALENDAR_AGENT_URL, 8004)

export const getRagBaseUrl = () =>
  resolveBaseUrl(process.env.NEXT_PUBLIC_RAG_URL, 8002)
