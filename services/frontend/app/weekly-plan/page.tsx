'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  CalendarDays,
  Download,
  FileImage,
  Loader2,
  Upload,
  History,
} from 'lucide-react'

const PROFILE_STORAGE_KEY = 'fitai-profile-user-id'
const CALENDAR_AGENT_URL =
  process.env.NEXT_PUBLIC_CALENDAR_AGENT_URL ?? 'http://localhost:8004'
const CORE_API_URL =
  process.env.NEXT_PUBLIC_PIPELINE_URL ?? 'http://localhost:8001'
const PLAN_HISTORY_LIMIT = 10

interface TrainingPlanEvent {
  id?: number
  day_date: string
  title: string
  start_time: string
  end_time: string
  location?: string | null
  notes?: string | null
  raw_payload?: Record<string, unknown> | null
}

interface ParsedCalendarEvent {
  title?: string
  date?: string
  day_date?: string
  start?: string
  end?: string
  start_time?: string
  end_time?: string
  location?: string | null
  notes?: string | null
  raw_text?: string | null
}

interface ParsedCalendarPayload {
  events?: ParsedCalendarEvent[]
  metadata?: Record<string, unknown>
}

interface TrainingPlanMetadata {
  source?: string
  mode?: string
  busy_events?: ParsedCalendarEvent[]
  busy_events_aligned?: ParsedCalendarEvent[]
  parsed_calendar?: ParsedCalendarPayload | string | null
  planner_model?: string
  used_fallback?: boolean
  planner_error?: string | null
  week_dates?: string[]
  calendar_summary?: string
  planner_notes?: string
}

interface TrainingPlanResponse {
  id: number
  week_start: string
  summary?: string | null
  events: TrainingPlanEvent[]
  metadata?: TrainingPlanMetadata | null
  created_at: string
  ics_content?: string | null
}

interface PlannerApiResponse {
  plan_id: number
  week_start: string
  summary: string
  events: TrainingPlanEvent[]
  ics_download_url: string
  ics_base64?: string
  metadata?: TrainingPlanMetadata
  created_at: string
}

interface CalendarDay {
  label: string
  date: string
  displayDate: string
  events: TrainingPlanEvent[]
}

const formatWeekDay = (date: Date) =>
  date.toLocaleDateString(undefined, { weekday: 'short' })

const formatDateLabel = (date: Date) =>
  date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

const getWeekDates = (weekStart?: string) => {
  const baseDate = weekStart ? new Date(weekStart) : getMonday(new Date())
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(baseDate)
    day.setDate(baseDate.getDate() + index)
    return day
  })
}

const getMonday = (input: Date) => {
  const date = new Date(input)
  const day = date.getDay()
  const diff = (day === 0 ? -6 : 1) - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

const groupEventsByDay = (
  events: TrainingPlanEvent[] | undefined,
  weekStart?: string,
): CalendarDay[] => {
  const weekDates = getWeekDates(weekStart)
  const byDate = (events ?? []).reduce<Record<string, TrainingPlanEvent[]>>(
    (acc, event) => {
      if (!acc[event.day_date]) {
        acc[event.day_date] = []
      }
      acc[event.day_date].push(event)
      return acc
    },
    {},
  )

  return weekDates.map((date) => {
    const iso = date.toISOString().slice(0, 10)
    const dayEvents =
      (byDate[iso] ?? []).sort((a, b) =>
        a.start_time.localeCompare(b.start_time),
      )
    return {
      label: formatWeekDay(date),
      date: iso,
      displayDate: formatDateLabel(date),
      events: dayEvents,
    }
  })
}

const decodeBase64ToBlobUrl = (data: string) => {
  const binary = typeof window !== 'undefined' ? window.atob(data) : atob(data)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  const blob = new Blob([bytes], { type: 'text/calendar' })
  return URL.createObjectURL(blob)
}

const parseMaybeJSON = (value: unknown) => {
  if (!value) return null
  if (typeof value === 'string') {
    try {
      return JSON.parse(value) as ParsedCalendarPayload
    } catch {
      return null
    }
  }
  if (typeof value === 'object') {
    return value as ParsedCalendarPayload
  }
  return null
}

const formatEasternDate = (
  value: string,
  options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' },
) => {
  try {
    return new Intl.DateTimeFormat('en-US', {
      ...options,
      timeZone: 'America/New_York',
    }).format(new Date(value))
  } catch {
    return value
  }
}

const formatEasternDateTime = (value: string) =>
  formatEasternDate(value, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  })

const describeWeekLabel = (weekStart: string) =>
  `Week of ${formatEasternDate(weekStart)}`

export default function WeeklyPlanPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [plan, setPlan] = useState<TrainingPlanResponse | null>(null)
  const [plans, setPlans] = useState<TrainingPlanResponse[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [plansLoading, setPlansLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [icsDownloadUrl, setIcsDownloadUrl] = useState<string | null>(null)
  const [icsBlobUrl, setIcsBlobUrl] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [userInstruction, setUserInstruction] = useState('')

  const clearIcsBlob = useCallback(() => {
    setIcsBlobUrl((prev) => {
      if (prev) {
        URL.revokeObjectURL(prev)
      }
      return null
    })
  }, [])

  const clearSelectedFile = useCallback(() => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = window.localStorage.getItem(PROFILE_STORAGE_KEY)
    if (stored) {
      setUserId(stored)
    } else {
      setUserId(null)
    }
  }, [])

  useEffect(() => {
    return () => {
      clearIcsBlob()
    }
  }, [clearIcsBlob])

  const fetchPlanHistory = useCallback(
    async (preferredPlanId?: number) => {
      if (!userId) return
      setPlansLoading(true)
      setHistoryError(null)
      try {
        const response = await fetch(
          `${CORE_API_URL}/training-plans?user_id=${userId}&limit=${PLAN_HISTORY_LIMIT}`,
        )
        if (!response.ok) {
          if (response.status === 404) {
            setPlans([])
            setPlan(null)
            setSelectedPlanId(null)
            return
          }
          throw new Error('Unable to load saved plans.')
        }
        const data: TrainingPlanResponse[] = await response.json()
        setPlans(data)
        if (data.length === 0) {
          setPlan(null)
          setSelectedPlanId(null)
          setIcsDownloadUrl(null)
          clearIcsBlob()
          return
        }
        const nextPlanId = preferredPlanId ?? data[0].id
        const selectedPlan =
          data.find((entry) => entry.id === nextPlanId) ?? data[0]
        setPlan(selectedPlan)
        setSelectedPlanId(selectedPlan.id)
        setIcsDownloadUrl(`${CORE_API_URL}/training-plans/${selectedPlan.id}/ics`)
        clearIcsBlob()
      } catch (fetchError) {
        console.error(fetchError)
        setHistoryError(
          fetchError instanceof Error
            ? fetchError.message
            : 'Unable to load saved plans.',
        )
      } finally {
        setPlansLoading(false)
      }
    },
    [userId, clearIcsBlob],
  )

  useEffect(() => {
    if (userId) {
      fetchPlanHistory()
    } else {
      setPlans([])
      setPlan(null)
      setSelectedPlanId(null)
    }
  }, [userId, fetchPlanHistory])

  const calendarDays = useMemo(
    () => groupEventsByDay(plan?.events, plan?.week_start),
    [plan],
  )

  const parsedCalendar = useMemo(() => {
    if (!plan?.metadata?.parsed_calendar) return null
    return parseMaybeJSON(plan.metadata.parsed_calendar)
  }, [plan])

  const parsedCalendarEvents = parsedCalendar?.events ?? []
  const busyEventsForDisplay =
    plan?.metadata?.busy_events_aligned ??
    plan?.metadata?.busy_events ??
    parsedCalendarEvents

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    } else {
      clearSelectedFile()
    }
  }

  const handlePlanSelection = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const planId = Number(event.target.value)
    setSelectedPlanId(planId)
    const selected = plans.find((entry) => entry.id === planId) ?? null
    setPlan(selected)
    setSuccess(null)
    setError(null)
    clearIcsBlob()
    if (selected) {
      setIcsDownloadUrl(`${CORE_API_URL}/training-plans/${selected.id}/ics`)
    } else {
      setIcsDownloadUrl(null)
    }
  }

  const triggerPlanGeneration = async () => {
    if (!userId) {
      setError('Save your profile first so we know whose calendar to personalize.')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)
    const formData = new FormData()
    formData.append('user_id', userId)
    formData.append('mode', selectedFile ? 'upload' : 'empty')
    if (selectedFile) {
      formData.append('file', selectedFile)
    }
    if (userInstruction.trim().length > 0) {
      formData.append('extra', userInstruction.trim())
    }

    try {
      const response = await fetch(`${CALENDAR_AGENT_URL}/planner`, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || 'Planner request failed.')
      }
      const data: PlannerApiResponse = await response.json()
      const newPlan: TrainingPlanResponse = {
        id: data.plan_id,
        week_start: data.week_start,
        summary: data.summary,
        events: data.events,
        metadata: data.metadata,
        created_at: data.created_at,
      }
      setPlan(newPlan)
      setSelectedPlanId(newPlan.id)
      setIcsDownloadUrl(data.ics_download_url)
      clearIcsBlob()
      if (data.ics_base64) {
        setIcsBlobUrl(decodeBase64ToBlobUrl(data.ics_base64))
      }
      clearSelectedFile()
      setSuccess('Weekly plan created and saved successfully!')
      await fetchPlanHistory(newPlan.id)
    } catch (planError) {
      console.error(planError)
      setError(
        planError instanceof Error
          ? planError.message
          : 'Failed to create plan.',
      )
    } finally {
      setLoading(false)
    }
  }

  const plannerNotes = plan?.metadata?.planner_notes
  const calendarSummary =
    plan?.metadata?.calendar_summary ||
    (busyEventsForDisplay.length > 0
      ? 'Busy slots extracted from your upload are listed below.'
      : 'No busy slots were provided, so the planner filled the entire week from scratch.')

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
          <CalendarDays className="w-6 h-6 text-primary-600" />
          Weekly Training Plan
        </h1>
        <p className="text-gray-600 text-sm md:text-base">
          Upload your weekly calendar screenshot (optional) and let FitAI craft a
          personalized 7-day training schedule. Plans are saved so you can revisit
          and download them anytime.
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4 shadow-sm">
        <div className="grid md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-2 space-y-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">
                Weekly calendar screenshot (PNG or JPG, optional)
              </label>
              <div className="flex items-center gap-3">
                <label className="flex-1 cursor-pointer border border-dashed border-gray-300 rounded-lg p-3 flex items-center gap-3 text-gray-600 hover:bg-gray-50">
                  <FileImage className="w-5 h-5" />
                  <span className="text-sm truncate">
                    {selectedFile ? selectedFile.name : 'Choose a file'}
                  </span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                  />
                </label>
                {selectedFile && (
                  <button
                    type="button"
                    onClick={clearSelectedFile}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">
                Additional instruction (optional)
              </label>
              <textarea
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-200"
                placeholder="e.g., Please avoid morning workouts before 10am."
                value={userInstruction}
                onChange={(event) => setUserInstruction(event.target.value)}
                rows={2}
              />
              <p className="text-xs text-gray-400">
                The planner will consider this preference alongside your calendar.
              </p>
            </div>

            {plans.length > 0 && (
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <History className="w-4 h-4 text-gray-500" />
                  View previous plans
                </label>
                <select
                  value={selectedPlanId ?? ''}
                  onChange={handlePlanSelection}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  {plans.map((historyPlan) => (
                    <option key={historyPlan.id} value={historyPlan.id}>
                      {describeWeekLabel(historyPlan.week_start)} · created at{' '}
                      {formatEasternDateTime(historyPlan.created_at)} ET
                    </option>
                  ))}
                </select>
                {plansLoading && (
                  <p className="text-xs text-gray-500">Refreshing history...</p>
                )}
              </div>
            )}
            {historyError && (
              <p className="text-xs text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {historyError}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={triggerPlanGeneration}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg font-medium shadow hover:bg-primary-500 disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Create Training Plan
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
            {error}
          </div>
        )}
        {success && (
          <div className="text-sm text-green-600 bg-green-50 border border-green-200 rounded-lg p-3">
            {success}
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {icsBlobUrl && (
            <a
              href={icsBlobUrl}
              download="fitai-weekly-plan.ics"
              className="inline-flex items-center gap-2 text-primary-600 text-sm font-medium hover:underline"
            >
              <Download className="w-4 h-4" />
              Download calendar file
            </a>
          )}
          {!icsBlobUrl && icsDownloadUrl && (
            <a
              href={icsDownloadUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-primary-600 text-sm font-medium hover:underline"
            >
              <Download className="w-4 h-4" />
              Download calendar file
            </a>
          )}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Weekly overview
            </h2>
            <p className="text-sm text-gray-500">
              {plan
                ? `Starting ${formatEasternDate(plan.week_start)}`
                : 'Create a plan to view your schedule'}
            </p>
          </div>
          <div className="text-sm text-gray-500 flex flex-col items-start md:items-end">
            {plan?.created_at && (
              <span>
                Created:{' '}
                <strong className="text-gray-700">
                  {formatEasternDateTime(plan.created_at)} ET
                </strong>
              </span>
            )}
            {plan?.metadata?.mode && (
              <span className="text-xs text-gray-400">
                Source: {plan.metadata.mode === 'upload' ? 'Calendar upload' : 'Blank calendar'}
              </span>
            )}
          </div>
        </div>

        {plan?.summary && (
          <div className="bg-primary-50 border border-primary-100 rounded-lg p-3 text-sm text-primary-900">
            {plan.summary}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-2">
            <p className="text-sm font-semibold text-gray-700">Planner insights</p>
            <p className="text-sm text-gray-600">
              {plannerNotes ||
                'The planner matched your current goal with evenly spaced workouts across the week.'}
            </p>
            {plan?.metadata?.used_fallback && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                The AI planner was temporarily unavailable so a deterministic fallback plan was used.
              </p>
            )}
          </div>
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-2">
            <p className="text-sm font-semibold text-gray-700">Calendar cues</p>
            <p className="text-sm text-gray-600">{calendarSummary}</p>
            <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
              {busyEventsForDisplay.length === 0 ? (
                <p className="text-xs text-gray-500">
                  No busy events were extracted from the upload.
                </p>
              ) : (
                busyEventsForDisplay.map((event, idx) => {
                  const startLabel =
                    event.start_time ?? event.start ?? '—'
                  const endLabel = event.end_time ?? event.end ?? '—'
                  const displayDate =
                    (event as any).aligned_date ??
                    event.day_date ??
                    event.date ??
                    'Unknown date'
                  return (
                    <div
                      key={`${event.title ?? 'busy'}-${displayDate}-${idx}`}
                      className="text-xs text-gray-600 border border-gray-200 rounded-md p-2 bg-white"
                    >
                      <p className="font-medium text-gray-800">
                        {event.title || 'Busy'}
                      </p>
                      <p>
                        {typeof displayDate === 'string'
                          ? `${formatEasternDate(displayDate)}`
                          : 'Unknown date'}{' '}
                        · {startLabel} - {endLabel}
                      </p>
                      {event.notes && <p className="text-gray-500">{event.notes}</p>}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {calendarDays.map((day) => (
            <div
              key={day.date}
              className="border border-gray-200 rounded-lg p-3 bg-gray-50 min-h-[150px] flex flex-col"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase text-gray-500 font-medium">
                  {day.label}
                </span>
                <span className="text-xs text-gray-400">{day.displayDate}</span>
              </div>
              <div className="space-y-2 flex-1">
                {day.events.length === 0 ? (
                  <p className="text-xs text-gray-400">
                    No session scheduled.
                  </p>
                ) : (
                  day.events.map((event) => (
                    <div
                      key={`${event.title}-${event.start_time}-${event.day_date}`}
                      className="bg-white rounded-md border border-primary-100 p-2"
                    >
                      <p className="text-sm font-semibold text-gray-800">
                        {event.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {event.start_time} - {event.end_time}
                      </p>
                      {event.notes && (
                        <p className="text-xs text-gray-500 mt-1">
                          {event.notes}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
