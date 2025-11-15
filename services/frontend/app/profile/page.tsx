'use client'

import { useEffect, useState } from 'react'
import { User } from 'lucide-react'

const PROFILE_STORAGE_KEY = 'fitai-profile-user-id'
const PROFILE_CACHE_KEY = 'fitai-profile-data'
const PROFILE_UPDATED_EVENT = 'fitai-profile-updated'
const PIPELINE_BASE_URL =
  process.env.NEXT_PUBLIC_PIPELINE_URL ?? 'http://localhost:8001'

const BODY_TYPES = [
  {
    label: 'Ectomorphic',
    value: 'ectomorphic',
    description: 'Lean builds that typically benefit from higher caloric intake and strength-focused training.',
  },
  {
    label: 'Mesomorphic',
    value: 'mesomorphic',
    description: 'Naturally athletic builds that respond quickly to both strength and conditioning programs.',
  },
  {
    label: 'Endomorphic',
    value: 'endomorphic',
    description: 'Stockier builds that thrive with consistent cardio, strength work, and balanced nutrition.',
  },
] as const

type BodyTypeValue = (typeof BODY_TYPES)[number]['value']

interface ProfileFormState {
  full_name: string
  height_cm: string
  weight_kg: string
  body_type: BodyTypeValue | ''
  gender: string
  age_years: string
  training_goal: string
}

type ProfileErrors = Partial<Record<keyof ProfileFormState, string>>

interface ProfileResponse {
  id: number
  full_name: string
  height_cm: number
  weight_kg: number
  body_type: BodyTypeValue
  gender: string
  age_years: number
  training_goal: string
}

const persistProfileToStorage = (data: ProfileResponse) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(data))
  window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
}

const clearProfileFromStorage = () => {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(PROFILE_CACHE_KEY)
  window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
}

const defaultFormState: ProfileFormState = {
  full_name: '',
  height_cm: '',
  weight_kg: '',
  body_type: '',
  gender: '',
  age_years: '',
  training_goal: '',
}

export default function Profile() {
  const [formData, setFormData] = useState<ProfileFormState>(defaultFormState)
  const [errors, setErrors] = useState<ProfileErrors>({})
  const [profileId, setProfileId] = useState<number | null>(null)
  const [isLocked, setIsLocked] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [hasSavedOnce, setHasSavedOnce] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const storedId = window.localStorage.getItem(PROFILE_STORAGE_KEY)
    if (!storedId) return

    const parsedId = Number(storedId)
    if (!Number.isFinite(parsedId)) {
      window.localStorage.removeItem(PROFILE_STORAGE_KEY)
      clearProfileFromStorage()
      return
    }

    setProfileId(parsedId)
    const fetchProfile = async () => {
      setIsLoading(true)
      try {
        const response = await fetch(`${PIPELINE_BASE_URL}/users/${parsedId}`)
        if (!response.ok) {
          throw new Error('Unable to load saved profile.')
        }
        const data: ProfileResponse = await response.json()
        populateForm(data)
        setIsLocked(true)
        setHasSavedOnce(true)
        persistProfileToStorage(data)
      } catch (error) {
        console.error(error)
        setStatusMessage({
          type: 'error',
          message: 'We could not load your saved profile. Please re-enter your information.',
        })
        window.localStorage.removeItem(PROFILE_STORAGE_KEY)
        clearProfileFromStorage()
        setProfileId(null)
        setIsLocked(false)
      } finally {
        setIsLoading(false)
      }
    }

    fetchProfile()
  }, [])

  const populateForm = (data: ProfileResponse) => {
    setFormData({
      full_name: data.full_name,
      height_cm: data.height_cm?.toString() ?? '',
      weight_kg: data.weight_kg?.toString() ?? '',
      body_type: data.body_type,
      gender: data.gender ?? '',
      age_years: data.age_years?.toString() ?? '',
      training_goal: data.training_goal,
    })
  }

  const handleChange = (field: keyof ProfileFormState, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setErrors((prev) => ({ ...prev, [field]: undefined }))
    setStatusMessage(null)
  }

  const validateForm = () => {
    const validationErrors: ProfileErrors = {}

    if (!formData.full_name.trim()) {
      validationErrors.full_name = 'Full name is required.'
    }

    const parsedHeight = Number(formData.height_cm)
    if (!formData.height_cm.trim()) {
      validationErrors.height_cm = 'Height is required.'
    } else if (Number.isNaN(parsedHeight)) {
      validationErrors.height_cm = 'Height must be a number.'
    } else if (parsedHeight <= 0) {
      validationErrors.height_cm = 'Height must be greater than zero.'
    }

    const parsedWeight = Number(formData.weight_kg)
    if (!formData.weight_kg.trim()) {
      validationErrors.weight_kg = 'Weight is required.'
    } else if (Number.isNaN(parsedWeight)) {
      validationErrors.weight_kg = 'Weight must be a number.'
    } else if (parsedWeight <= 0) {
      validationErrors.weight_kg = 'Weight must be greater than zero.'
    }

    if (!formData.body_type) {
      validationErrors.body_type = 'Body type is required.'
    }

    if (!formData.gender.trim()) {
      validationErrors.gender = 'Gender is required.'
    }

    const parsedAge = Number(formData.age_years)
    if (!formData.age_years.trim()) {
      validationErrors.age_years = 'Age is required.'
    } else if (!Number.isInteger(parsedAge)) {
      validationErrors.age_years = 'Age must be a whole number.'
    } else if (parsedAge <= 0) {
      validationErrors.age_years = 'Age must be greater than zero.'
    }

    if (!formData.training_goal.trim()) {
      validationErrors.training_goal = 'Training goal is required.'
    }

    setErrors(validationErrors)
    const isValid = Object.keys(validationErrors).length === 0
    return {
      isValid,
      payload: isValid
        ? {
            full_name: formData.full_name.trim(),
            height_cm: parsedHeight,
            weight_kg: parsedWeight,
            body_type: formData.body_type as BodyTypeValue,
            gender: formData.gender,
            age_years: parsedAge,
            training_goal: formData.training_goal.trim(),
          }
        : null,
    }
  }

  const handleSave = async () => {
    if (isLocked || isLoading) return

    const { isValid, payload } = validateForm()
    if (!isValid || !payload) return

    setIsLoading(true)
    setStatusMessage(null)

    try {
      const method = profileId ? 'PUT' : 'POST'
      const endpoint = profileId
        ? `${PIPELINE_BASE_URL}/users/${profileId}`
        : `${PIPELINE_BASE_URL}/users`
      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error('Unable to save your profile. Please try again.')
      }

      const data: ProfileResponse = await response.json()
      populateForm(data)
      setProfileId(data.id)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(PROFILE_STORAGE_KEY, data.id.toString())
      }
      persistProfileToStorage(data)
      setIsLocked(true)
      setHasSavedOnce(true)
      setStatusMessage({ type: 'success', message: 'Profile saved successfully.' })
    } catch (error) {
      console.error(error)
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'Something went wrong.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleUnlock = () => {
    setIsLocked(false)
    setHasSavedOnce(false)
    setStatusMessage(null)
  }

  const fieldDisabled = isLocked || isLoading

  return (
    <div className="flex flex-col h-full">
      <div className="p-8 border-b border-gray-200 bg-white">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Profile</h1>
        <p className="text-gray-600">Provide your details so we can personalize your training journey.</p>
      </div>

      <div className="p-8 bg-gray-50 flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
              <div className="flex items-center space-x-4">
                <div className="w-14 h-14 bg-blue-500 rounded-full flex items-center justify-center">
                  <User className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Your Fitness Profile</h2>
                  <p className="text-sm text-gray-600">All fields are required.</p>
                </div>
              </div>
              <button
                onClick={handleUnlock}
                disabled={!isLocked || isLoading}
                className={`px-4 py-2 rounded-lg border text-sm font-medium ${
                  !isLocked || isLoading
                    ? 'border-gray-200 text-gray-400 cursor-not-allowed'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                Unlock for Editing
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => handleChange('full_name', e.target.value)}
                  disabled={fieldDisabled}
                  placeholder="e.g. Jordan Parker"
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.full_name ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                />
                {errors.full_name && <p className="text-sm text-red-500 mt-1">{errors.full_name}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.height_cm}
                  onChange={(e) => handleChange('height_cm', e.target.value)}
                  disabled={fieldDisabled}
                  placeholder="e.g. 175"
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.height_cm ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                />
                {errors.height_cm && <p className="text-sm text-red-500 mt-1">{errors.height_cm}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.weight_kg}
                  onChange={(e) => handleChange('weight_kg', e.target.value)}
                  disabled={fieldDisabled}
                  placeholder="e.g. 70.5"
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.weight_kg ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                />
                {errors.weight_kg && <p className="text-sm text-red-500 mt-1">{errors.weight_kg}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Body type</label>
                <select
                  value={formData.body_type}
                  onChange={(e) => handleChange('body_type', e.target.value)}
                  disabled={fieldDisabled}
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.body_type ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                >
                  <option value="">Select body type</option>
                  {BODY_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {errors.body_type && <p className="text-sm text-red-500 mt-1">{errors.body_type}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                <select
                  value={formData.gender}
                  onChange={(e) => handleChange('gender', e.target.value)}
                  disabled={fieldDisabled}
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.gender ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                >
                  <option value="">Select gender</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="non-binary">Non-binary</option>
                  <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
                {errors.gender && <p className="text-sm text-red-500 mt-1">{errors.gender}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Age (years)</label>
                <input
                  type="number"
                  step="1"
                  value={formData.age_years}
                  onChange={(e) => handleChange('age_years', e.target.value)}
                  disabled={fieldDisabled}
                  placeholder="e.g. 32"
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.age_years ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                />
                {errors.age_years && <p className="text-sm text-red-500 mt-1">{errors.age_years}</p>}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Training goal</label>
                <textarea
                  value={formData.training_goal}
                  onChange={(e) => handleChange('training_goal', e.target.value)}
                  disabled={fieldDisabled}
                  rows={3}
                  placeholder="Describe your main training goal..."
                  className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                    errors.training_goal ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200'
                  } ${fieldDisabled ? 'bg-gray-50 text-gray-500' : ''}`}
                />
                {errors.training_goal && <p className="text-sm text-red-500 mt-1">{errors.training_goal}</p>}
              </div>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <button
                onClick={handleSave}
                disabled={(fieldDisabled && hasSavedOnce) || isLoading}
                className={`px-6 py-2 rounded-lg text-white font-medium ${
                  (fieldDisabled && hasSavedOnce) || isLoading
                    ? 'bg-primary-200 cursor-not-allowed'
                    : 'bg-primary-500 hover:bg-primary-600'
                }`}
              >
                {profileId ? 'Save Changes' : 'Save Profile'}
              </button>
              {statusMessage && (
                <div
                  className={`text-sm px-4 py-2 rounded-lg ${
                    statusMessage.type === 'success'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}
                >
                  {statusMessage.message}
                </div>
              )}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Body Type Guide</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {BODY_TYPES.map((type) => (
                <div key={type.value} className="border border-gray-200 rounded-lg p-4">
                  <p className="font-semibold text-gray-900">{type.label}</p>
                  <p className="text-sm text-gray-600 mt-2">{type.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
