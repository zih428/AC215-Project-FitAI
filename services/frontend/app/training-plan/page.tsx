'use client'

import { useEffect, useState, useCallback, ChangeEvent } from 'react'
import { CalendarClock, FileText, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react'

interface PlannerUser {
  id: number
  full_name: string
  training_goal?: string
}

interface PlannerPlan {
  plan_summary?: string
  training_days?: Array<Record<string, any>>
  recovery_notes?: string
  nutrition_notes?: string
}

interface PlannerResponse {
  user: PlannerUser
  calendar: Record<string, any> | null
  fitness_plan: PlannerPlan
  plan_record?: { id: number; created_at: string | null } | null
}

interface PlanHistoryItem {
  id: number
  created_at: string | null
  plan_json: PlannerPlan
  citations?: Record<string, any> | null
}

const PROFILE_STORAGE_KEY = 'fitai-profile-user-id'
const PROFILE_CACHE_KEY = 'fitai-profile-data'
const PROFILE_UPDATED_EVENT = 'fitai-profile-updated'
const CALENDAR_AGENT_URL =
  process.env.NEXT_PUBLIC_CALENDAR_AGENT_URL ?? 'http://localhost:8004'
const PLAN_CACHE_KEY = 'fitai-training-plan-cache'

export default function TrainingPlan() {
  const [profileId, setProfileId] = useState<number | null>(null)
  const [profileName, setProfileName] = useState<string>('No profile saved')
  const [profileGoal, setProfileGoal] = useState<string>('')
  const [isHydrated, setIsHydrated] = useState(false)

  const [calendarFile, setCalendarFile] = useState<File | null>(null)
  const [calendarError, setCalendarError] = useState<string | null>(null)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [planResponse, setPlanResponse] = useState<PlannerResponse | null>(null)
  const [showCalendarParsed, setShowCalendarParsed] = useState(false)
  const [planHistory, setPlanHistory] = useState<PlanHistoryItem[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)

  const loadProfile = useCallback(() => {
    if (typeof window === 'undefined') return

    const storedId = window.localStorage.getItem(PROFILE_STORAGE_KEY)
    const parsedId = storedId ? Number(storedId) : null
    setProfileId(Number.isFinite(parsedId) ? parsedId : null)

    try {
      const cachedProfile = window.localStorage.getItem(PROFILE_CACHE_KEY)
      if (cachedProfile) {
        const parsed = JSON.parse(cachedProfile) as { full_name?: string; training_goal?: string }
        setProfileName(parsed.full_name || 'No profile saved')
        setProfileGoal(parsed.training_goal || '')
      } else {
        setProfileName('No profile saved')
        setProfileGoal('')
      }
    } catch (err) {
      console.error('Failed to read cached profile data:', err)
      setProfileName('No profile saved')
      setProfileGoal('')
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    loadProfile()
    setIsHydrated(true)
    window.addEventListener(PROFILE_UPDATED_EVENT, loadProfile)
    return () => window.removeEventListener(PROFILE_UPDATED_EVENT, loadProfile)
  }, [loadProfile])

  const fetchPlanHistory = useCallback(
    async (targetProfileId: number | null) => {
      if (!targetProfileId) {
        setPlanHistory([])
        return
      }
      try {
        const response = await fetch(
          `${CALENDAR_AGENT_URL.replace(/\/$/, '')}/planner/history?user_id=${targetProfileId}`
        )
        if (!response.ok) {
          throw new Error(`History fetch failed: ${response.status}`)
        }
        const data = (await response.json()) as { plans?: PlanHistoryItem[] }
        setPlanHistory(data.plans || [])
      } catch (err) {
        console.error('Failed to load plan history:', err)
        setPlanHistory([])
      }
    },
    []
  )

  useEffect(() => {
    fetchPlanHistory(profileId)
  }, [profileId, fetchPlanHistory])

  // Restore cached plan selection/response to avoid losing state when navigating
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const cached = window.localStorage.getItem(PLAN_CACHE_KEY)
      if (!cached) return
      const parsed = JSON.parse(cached) as {
        planResponse?: PlannerResponse
        selectedPlanId?: number | null
      }
      if (parsed.planResponse && (!profileId || parsed.planResponse.user.id === profileId)) {
        setPlanResponse(parsed.planResponse)
        setSelectedPlanId(parsed.selectedPlanId ?? null)
      }
    } catch (err) {
      console.error('Failed to restore cached training plan:', err)
    }
  }, [profileId])

  // Persist plan state so navigating away doesn't clear it
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const payload = JSON.stringify({
        planResponse,
        selectedPlanId,
      })
      window.localStorage.setItem(PLAN_CACHE_KEY, payload)
    } catch (err) {
      console.error('Failed to cache training plan:', err)
    }
  }, [planResponse, selectedPlanId])

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    setStatusMessage(null)
    setPlanResponse(null)
    if (!file) {
      setCalendarFile(null)
      setCalendarError(null)
      return
    }

    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      setCalendarFile(null)
      setCalendarError('Only PNG or JPG files are supported.')
      return
    }

    setCalendarError(null)
    setCalendarFile(file)
  }

  const handleGeneratePlan = async () => {
    if (!profileId) {
      setError('Save your profile first so we know which user to plan for.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    setStatusMessage('Generating training plan...')
    setPlanResponse(null)

    const formData = new FormData()
    formData.append('user_id', profileId.toString())
    if (calendarFile) formData.append('file', calendarFile)

    try {
      const response = await fetch(`${CALENDAR_AGENT_URL.replace(/\/$/, '')}/planner`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || 'Failed to generate plan.')
      }

      const data = (await response.json()) as PlannerResponse
      setPlanResponse({ ...data, plan_record: null })
      setStatusMessage('Plan generated. Save it if you like it.')
    } catch (err) {
      console.error('Planner request failed:', err)
      setError(err instanceof Error ? err.message : 'Unable to generate plan.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSavePlan = async () => {
    if (!planResponse || !profileId) {
      setError('Generate a plan first, and ensure your profile is saved.')
      return
    }
    setIsSaving(true)
    setError(null)
    setStatusMessage('Saving plan...')
    try {
      const response = await fetch(`${CALENDAR_AGENT_URL.replace(/\/$/, '')}/planner/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: profileId,
          plan: planResponse.fitness_plan,
        }),
      })
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || 'Failed to save plan.')
      }
      const data = (await response.json()) as { plan_record?: { id: number; created_at: string | null } }
      setPlanResponse((prev) =>
        prev ? { ...prev, plan_record: data.plan_record ?? null } : prev
      )
      setStatusMessage('Plan saved.')
      fetchPlanHistory(profileId)
    } catch (err) {
      console.error('Save plan failed:', err)
      setError(err instanceof Error ? err.message : 'Unable to save plan.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSelectSavedPlan = (value: string) => {
    if (hasUnsavedPlan) {
      setStatusMessage('Save or discard the current plan before switching.')
      return
    }
    const parsedId = Number(value)
    if (!Number.isFinite(parsedId)) {
      setSelectedPlanId(null)
      return
    }
    setSelectedPlanId(parsedId)
    const chosen = planHistory.find((p) => p.id === parsedId)
    if (chosen && profileId) {
      setPlanResponse({
        user: { id: profileId, full_name: profileName },
        calendar: null,
        fitness_plan: chosen.plan_json,
        plan_record: { id: chosen.id, created_at: chosen.created_at },
      })
      setStatusMessage(`Loaded saved plan #${chosen.id}`)
      setError(null)
    }
  }

  const renderTrainingDay = (day: Record<string, any>, idx: number) => {
    const title = day.date
      ? `${day.day_of_week || 'Training Day'} (${day.date})`
      : day.day_of_week || `Training Day ${idx + 1}`
    const timeBlock = day.scheduled_time_block || null
    const availableBlocks = Array.isArray(day.available_time_blocks) ? day.available_time_blocks : null
    const movements = Array.isArray(day.movements) ? day.movements : []

    return (
      <div key={`${title}-${idx}`} className="border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm text-gray-500">Day {idx + 1}</p>
            <p className="text-lg font-semibold text-gray-900">{title}</p>
          </div>
          {timeBlock && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
              {timeBlock}
            </span>
          )}
        </div>

        {day.workout_focus && (
          <p className="text-sm text-gray-700">
            <span className="font-semibold text-gray-900">Focus:</span> {day.workout_focus}
          </p>
        )}

        {availableBlocks && availableBlocks.length > 0 && (
          <div className="text-sm text-gray-600">
            <span className="font-semibold text-gray-900">Available windows:</span>{' '}
            {availableBlocks.join(', ')}
          </div>
        )}

        {movements.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-gray-900">Movements</p>
            <div className="space-y-2">
              {movements.map((mv, mvIdx) => (
                <div key={`${mv.name}-${mvIdx}`} className="bg-gray-50 rounded-md p-3">
                  <p className="font-medium text-gray-900">{mv.name}</p>
                  {mv.sets_reps && <p className="text-sm text-gray-700">Sets/Reps: {mv.sets_reps}</p>}
                  {mv.equipment && <p className="text-sm text-gray-700">Equipment: {mv.equipment}</p>}
                  {mv.coaching_notes && (
                    <p className="text-sm text-gray-700">Notes: {mv.coaching_notes}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {day.conditioning_or_cardio && (
          <p className="text-sm text-gray-700">
            <span className="font-semibold text-gray-900">Conditioning:</span> {day.conditioning_or_cardio}
          </p>
        )}

        {day.recovery && (
          <p className="text-sm text-gray-700">
            <span className="font-semibold text-gray-900">Recovery:</span> {day.recovery}
          </p>
        )}

        {day.schedule_reason && (
          <p className="text-xs text-gray-500">Reason: {day.schedule_reason}</p>
        )}
      </div>
    )
  }

  const plan = planResponse?.fitness_plan
  const trainingDays = Array.isArray(plan?.training_days) ? plan?.training_days : []
  const hasUnsavedPlan = Boolean(planResponse && !planResponse.plan_record)
  const isPlanSwitchingDisabled = isSubmitting || isSaving || hasUnsavedPlan

  return (
    <div className="flex flex-col h-full">
      <div className="p-8 border-b border-gray-200 bg-white">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Training Plan</h1>
        <p className="text-gray-600">
          Generate a weekly training plan using your profile, with an optional calendar upload to respect your schedule.
        </p>
      </div>

      <div className="p-8 bg-gray-50 flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                  <CalendarClock className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Ready to plan</p>
                  <h2 className="text-xl font-semibold text-gray-900">{profileName}</h2>
                  {profileGoal && <p className="text-sm text-gray-600">Goal: {profileGoal}</p>}
                </div>
              </div>
              <div className="text-right text-sm text-gray-600">
                <p>User ID</p>
                <p className="font-semibold text-gray-900">{profileId ?? 'Not set'}</p>
              </div>
            </div>

            {!isHydrated && (
              <div className="flex items-center text-sm text-gray-600">
                <AlertCircle className="w-4 h-4 mr-2 text-amber-500" />
                Loading profile info...
              </div>
            )}

            {isHydrated && !profileId && (
              <div className="flex items-center text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                <AlertCircle className="w-4 h-4 mr-2" />
                Save your profile first on the <span className="font-semibold mx-1">Profile</span> tab so we can create a plan.
              </div>
            )}

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">Calendar screenshot (optional)</label>
                <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 bg-gray-50">
                  <input
                    type="file"
                    accept="image/png,image/jpeg"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-700"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    PNG or JPG. Leave empty to generate a plan without calendar constraints.
                  </p>
                  {calendarError && <p className="text-sm text-red-600 mt-2">{calendarError}</p>}
                  {calendarFile && !calendarError && (
                    <p className="text-sm text-green-700 mt-2 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-1" /> {calendarFile.name}
                    </p>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">Actions</label>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleGeneratePlan}
                    disabled={isSubmitting || !profileId}
                    className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-white font-medium ${
                      isSubmitting || !profileId
                        ? 'bg-primary-200 cursor-not-allowed'
                        : 'bg-primary-500 hover:bg-primary-600'
                    }`}
                  >
                    {isSubmitting ? 'Generating...' : 'Generate Training Plan'}
                  </button>
                  <button
                    onClick={handleSavePlan}
                    disabled={isSaving || !hasUnsavedPlan || !profileId}
                    className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-white font-medium ${
                      isSaving || !hasUnsavedPlan || !profileId
                        ? 'bg-gray-200 cursor-not-allowed'
                        : 'bg-gray-800 hover:bg-gray-900'
                    }`}
                  >
                    {isSaving ? 'Saving...' : 'Save This Plan'}
                  </button>
                </div>
                {planHistory.length > 0 && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Saved plans</label>
                    <select
                      value={selectedPlanId ?? ''}
                      onChange={(e) => handleSelectSavedPlan(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      disabled={isPlanSwitchingDisabled}
                    >
                      <option value="">Select a saved plan</option>
                      {planHistory.map((item) => {
                        const timestamp = item.created_at
                          ? new Date(item.created_at).toLocaleString()
                          : 'Unknown time'
                        const summary = item.plan_json?.plan_summary
                        const summarySnippet = summary ? ` — ${summary.slice(0, 80)}${summary.length > 80 ? '…' : ''}` : ''
                        return (
                          <option key={item.id} value={item.id}>
                            {`Plan #${item.id} — ${timestamp}${summarySnippet}`}
                          </option>
                        )
                      })}
                    </select>
                    {hasUnsavedPlan && (
                      <p className="text-xs text-amber-700">
                        Save or discard the current plan to switch to another saved plan.
                      </p>
                    )}
                  </div>
                )}
                {statusMessage && (
                  <p className="text-sm text-green-700 flex items-center">
                    <Sparkles className="w-4 h-4 mr-1" /> {statusMessage}
                  </p>
                )}
                {error && (
                  <p className="text-sm text-red-700 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" /> {error}
                  </p>
                )}
              </div>
            </div>
          </div>

          {planResponse && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Plan for</p>
                  <h3 className="text-2xl font-semibold text-gray-900">{planResponse.user.full_name}</h3>
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <FileText className="w-4 h-4 mr-2 text-primary-600" />
                  <span>Fitness plan ready</span>
                </div>
              </div>

              {plan?.plan_summary && (
                <div className="bg-primary-50 border border-primary-100 rounded-lg p-4 text-primary-900 text-sm">
                  {plan.plan_summary}
                </div>
              )}

              {trainingDays.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-lg font-semibold text-gray-900">Training Days</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                    {trainingDays.map((day, idx) => renderTrainingDay(day, idx))}
                  </div>
                </div>
              )}

              {(plan?.recovery_notes || plan?.nutrition_notes) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {plan?.recovery_notes && (
                    <div className="border border-gray-200 rounded-lg p-4">
                      <p className="text-sm font-semibold text-gray-900 mb-2">Recovery Notes</p>
                      <p className="text-sm text-gray-700">{plan.recovery_notes}</p>
                    </div>
                  )}
                  {plan?.nutrition_notes && (
                    <div className="border border-gray-200 rounded-lg p-4">
                      <p className="text-sm font-semibold text-gray-900 mb-2">Nutrition Notes</p>
                      <p className="text-sm text-gray-700">{plan.nutrition_notes}</p>
                    </div>
                  )}
                </div>
              )}

              {planResponse.calendar && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    type="button"
                    onClick={() => setShowCalendarParsed((prev) => !prev)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900"
                  >
                    <span>Calendar parsed</span>
                    <span className="text-xs text-gray-500">{showCalendarParsed ? 'Hide' : 'Show'}</span>
                  </button>
                  {showCalendarParsed && (
                    <pre className="text-xs bg-gray-50 border-t border-gray-100 rounded-b-lg p-3 overflow-x-auto">
                      {JSON.stringify(planResponse.calendar, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
