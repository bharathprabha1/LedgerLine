
import { useState, type FormEvent } from 'react'
import {
  Wallet,
  Mail,
  Lock,
  User as UserIcon,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react'

import {
  loginUser,
  registerUser,
} from './services/auth'

import type {
  LoginRequest,
  RegisterRequest,
  User,
} from './types/auth'

import './AuthScreen.css'

// Props received from App.tsx
type AuthScreenProps = {
  onAuthenticated: (user: User) => void
}

function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setError('')
    setLoading(true)

    try {
      let authenticatedUser: User

      if (mode === 'register') {
        const details: RegisterRequest = {
          full_name: fullName.trim(),
          email: email.trim(),
          password,
        }

        // Register the new account.
        await registerUser(details)

        // Automatically log in after registration.
        const result = await loginUser({
          email: details.email,
          password,
        })

        authenticatedUser = result.user
      } else {
        const credentials: LoginRequest = {
          email: email.trim(),
          password,
        }

        // Authenticate existing user.
        const result = await loginUser(credentials)

        authenticatedUser = result.user
      }

      // Send authenticated user to App.tsx.
      onAuthenticated(authenticatedUser)

    } catch (err: unknown) {
      const message =
        typeof err === 'object' &&
        err !== null &&
        'response' in err
          ? (
              err as {
                response?: {
                  data?: {
                    detail?: string | { msg?: string }[]
                  }
                }
              }
            ).response?.data?.detail
          : undefined

      let errorMessage =
        'Unable to connect. Please check your details and try again.'

      if (typeof message === 'string') {
        errorMessage = message
      } else if (Array.isArray(message)) {
        errorMessage = message
          .map((item) => item.msg ?? 'Invalid input')
          .join(', ')
      }

      setError(errorMessage)

    } finally {
      setLoading(false)
    }
  }

  function switchMode(nextMode: 'login' | 'register') {
    setMode(nextMode)
    setError('')
  }

  return (
    <main className="auth-page">

      {/* Branding section */}
      <section className="auth-brand-panel">

        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Wallet size={24} />
          </div>

          <span>
            Ledger<span>Line</span>
          </span>
        </div>

        <div className="auth-brand-content">

          <span className="auth-eyebrow">
            YOUR FINANCES, SIMPLIFIED
          </span>

          <h1>
            Banking built around clarity and control.
          </h1>

          <p>
            Manage accounts, track transactions and maintain a transparent
            record of your financial activity.
          </p>

          <div className="auth-feature">
            <ShieldCheck size={21} />

            <div>
              <strong>Security-focused access</strong>

              <span>
                Protected authentication and account controls.
              </span>
            </div>
          </div>

        </div>

        <p className="auth-brand-footer">
          © 2026 LedgerLine. Secure financial workspace.
        </p>

      </section>

      {/* Authentication form */}
      <section className="auth-form-panel">

        <div className="auth-form-container">

          <div className="auth-mobile-brand">
            <div className="auth-brand-icon">
              <Wallet size={22} />
            </div>

            <strong>LedgerLine</strong>
          </div>

          <span className="auth-eyebrow">
            {mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}
          </span>

          <h2>
            {mode === 'login'
              ? 'Sign in to LedgerLine'
              : 'Create your account'}
          </h2>

          <p className="auth-subtitle">
            {mode === 'login'
              ? 'Enter your credentials to access your workspace.'
              : 'Create an account to get started with LedgerLine.'}
          </p>

          {/* Login / Register tabs */}
          <div className="auth-tabs">

            <button
              type="button"
              className={
                mode === 'login'
                  ? 'auth-tab active'
                  : 'auth-tab'
              }
              onClick={() => switchMode('login')}
              disabled={loading}
            >
              Sign in
            </button>

            <button
              type="button"
              className={
                mode === 'register'
                  ? 'auth-tab active'
                  : 'auth-tab'
              }
              onClick={() => switchMode('register')}
              disabled={loading}
            >
              Register
            </button>

          </div>

          <form
            onSubmit={handleSubmit}
            className="auth-form"
          >

            {/* Full name - Registration only */}
            {mode === 'register' && (
              <label className="auth-field">

                <span>Full name</span>

                <div className="auth-input-wrap">
                  <UserIcon size={18} />

                  <input
                    type="text"
                    placeholder="Enter your full name"
                    value={fullName}
                    onChange={(event) =>
                      setFullName(event.target.value)
                    }
                    minLength={2}
                    maxLength={120}
                    autoComplete="name"
                    required
                    disabled={loading}
                  />
                </div>

              </label>
            )}

            {/* Email */}
            <label className="auth-field">

              <span>Email address</span>

              <div className="auth-input-wrap">
                <Mail size={18} />

                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  autoComplete="email"
                  required
                  disabled={loading}
                />
              </div>

            </label>

            {/* Password */}
            <label className="auth-field">

              <span>Password</span>

              <div className="auth-input-wrap">
                <Lock size={18} />

                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  minLength={mode === 'register' ? 12 : 1}
                  maxLength={128}
                  autoComplete={
                    mode === 'login'
                      ? 'current-password'
                      : 'new-password'
                  }
                  required
                  disabled={loading}
                />
              </div>

              {mode === 'register' && (
                <small>
                  Use at least 12 characters.
                </small>
              )}

            </label>

            {/* Error message */}
            {error && (
              <div
                className="auth-error"
                role="alert"
              >
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              className="auth-submit"
              disabled={loading}
            >
              {loading
                ? 'Please wait...'
                : mode === 'login'
                  ? 'Sign in'
                  : 'Create account'}

              {!loading && <ArrowRight size={18} />}
            </button>

          </form>

          {/* Security information */}
          <div className="auth-secure-note">
            <ShieldCheck size={16} />

            <span>
              Your credentials are securely processed by LedgerLine.
            </span>
          </div>

        </div>

      </section>

    </main>
  )
}

export default AuthScreen
