'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { LogIn, UserPlus, ShieldCheck, LogOut, User } from 'lucide-react'
import { useEffect } from 'react'

const PIPELINE_BASE_URL =
  process.env.NEXT_PUBLIC_PIPELINE_URL ?? 'http://localhost:8001'
const AUTH_TOKEN_KEY = 'fitai-auth-token'
const PROFILE_STORAGE_KEY = 'fitai-profile-user-id'
const PROFILE_CACHE_KEY = 'fitai-profile-data'
const PROFILE_UPDATED_EVENT = 'fitai-profile-updated'

type Mode = 'login' | 'register'

interface RegisterForm {
  email: string
  password: string
  full_name: string
}

const emptyRegisterForm: RegisterForm = {
  email: '',
  password: '',
  full_name: '',
}

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [registerForm, setRegisterForm] = useState<RegisterForm>(emptyRegisterForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [session, setSession] = useState<{ email?: string; full_name?: string } | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem(AUTH_TOKEN_KEY)
    const cached = window.localStorage.getItem(PROFILE_CACHE_KEY)
    if (token && cached) {
      try {
        const parsed = JSON.parse(cached) as { email?: string; full_name?: string }
        setSession({ email: parsed.email, full_name: parsed.full_name })
      } catch {
        setSession(null)
      }
    } else {
      setSession(null)
    }
  }, [])

  const persistSession = (token: string, user: { id: number } & Record<string, any>) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(AUTH_TOKEN_KEY, token)
    window.localStorage.setItem(PROFILE_STORAGE_KEY, user.id.toString())
    window.localStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(user))
    // Also set a cookie so the API can read it if the Authorization header is ever stripped
    document.cookie = `access_token=${token}; path=/; SameSite=Lax`
    window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
    setSession({ email: user.email, full_name: user.full_name })
  }

  const handleLogout = () => {
    if (typeof window === 'undefined') return
    window.localStorage.removeItem(AUTH_TOKEN_KEY)
    window.localStorage.removeItem(PROFILE_STORAGE_KEY)
    window.localStorage.removeItem(PROFILE_CACHE_KEY)
    document.cookie = 'access_token=; Max-Age=0; path=/; SameSite=Lax'
    window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
    setSession(null)
    setEmail('')
    setPassword('')
    setRegisterForm(emptyRegisterForm)
  }

  const handleLogin = async () => {
    setIsSubmitting(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await fetch(`${PIPELINE_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      })
      if (!response.ok) {
        throw new Error('Login failed. Please check your credentials.')
      }
      const data = await response.json()
      persistSession(data.access_token, data.user)
      setSuccess('Logged in successfully. Redirecting to your profile...')
      router.push('/profile')
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRegister = async () => {
    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    if (!registerForm.email.trim() || !registerForm.password.trim()) {
      setError('Email and password are required.')
      setIsSubmitting(false)
      return
    }

    try {
      const response = await fetch(`${PIPELINE_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: registerForm.email.trim(),
          password: registerForm.password,
          full_name: registerForm.full_name.trim(),
        }),
      })
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || 'Registration failed. Please check your inputs.')
      }
      const data = await response.json()
      persistSession(data.access_token, data.user)
      setSuccess('Account created. Redirecting to your profile...')
      router.push('/profile')
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Registration failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (session) {
    const displayName = session.full_name || session.email || 'Fitness User'
    return (
      <div className="flex min-h-screen bg-gray-50">
        <div className="flex-1 flex items-center justify-center p-10">
          <div className="max-w-xl w-full bg-white border border-gray-200 rounded-2xl shadow-md p-8 space-y-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-primary-500 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">You’re signed in</h1>
                <p className="text-sm text-gray-600">
                  Signed in as <span className="font-medium">{displayName}</span>
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <button
                onClick={() => router.push('/profile')}
                className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition"
              >
                Go to Profile
              </button>
              <button
                onClick={() => router.push('/ai-coach')}
                className="w-full py-2.5 bg-white border border-gray-300 text-gray-800 rounded-lg font-semibold hover:bg-gray-50 transition"
              >
                Go to Dashboard
              </button>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-600 border-t border-gray-200 pt-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Your profile and plans stay linked to your account.</span>
              </div>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium"
              >
                <LogOut className="w-4 h-4" /> Log out
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <div className="flex-1 flex items-center justify-center p-10">
        <div className="max-w-2xl w-full bg-white border border-gray-200 rounded-2xl shadow-md p-8 space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-primary-500 rounded-full flex items-center justify-center">
                {mode === 'login' ? (
                  <LogIn className="w-6 h-6 text-white" />
                ) : (
                  <UserPlus className="w-6 h-6 text-white" />
                )}
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {mode === 'login' ? 'Welcome back' : 'Create your account'}
                </h1>
                <p className="text-sm text-gray-600">
                  {mode === 'login'
                    ? 'Log in to access your profile and saved plans.'
                    : 'Register once to save your profile and plans.'}
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login')
                setError(null)
                setSuccess(null)
              }}
              className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              {mode === 'login' ? 'Need an account?' : 'Have an account?'}
            </button>
          </div>

          {mode === 'login' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-200"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-200"
                  placeholder="Minimum 8 characters"
                  autoComplete="current-password"
                />
              </div>
              <button
                onClick={handleLogin}
                disabled={isSubmitting}
                className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition disabled:opacity-60"
              >
                {isSubmitting ? 'Logging in...' : 'Log In'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-200"
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                  <input
                    type="password"
                    value={registerForm.password}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-200"
                    placeholder="Minimum 8 characters"
                    autoComplete="new-password"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={registerForm.full_name}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, full_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-200"
                    placeholder="e.g. Jordan Parker"
                  />
                </div>
              </div>
              <button
                onClick={handleRegister}
                disabled={isSubmitting}
                className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition disabled:opacity-60"
              >
                {isSubmitting ? 'Creating account...' : 'Create account'}
              </button>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}

          <div className="flex items-center gap-2 text-sm text-gray-500">
            <ShieldCheck className="w-4 h-4" />
            <p>Your profile and plans stay linked to your account. Logging out will not delete them.</p>
          </div>
          <div className="text-sm text-gray-600">
            <Link className="text-primary-600 underline" href="/profile">
              Go to profile
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
