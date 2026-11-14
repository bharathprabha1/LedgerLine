
import { useState } from 'react'
import {
  UserRound,
  Mail,
  LockKeyhole,
  Save,
  Eye,
  EyeOff,
  ShieldCheck,
} from 'lucide-react'

import type { User } from '../types/auth'
import {
  updateUserProfile,
  changeUserPassword,
} from '../services/auth'

import './SettingsPage.css'
interface SettingsPageProps {
  currentUser: User
  onUserUpdated: (user: User) => void
  onPasswordChanged: () => void
}

function getErrorMessage(error: unknown): string {
  const err = error as {
    response?: {
      data?: {
        detail?: string
        message?: string
      }
    }
    message?: string
  }

  return (
    err.response?.data?.detail ||
    err.response?.data?.message ||
    err.message ||
    'Something went wrong. Please try again.'
  )
}

export default function SettingsPage({
  currentUser,
  onUserUpdated,
  onPasswordChanged,
}: SettingsPageProps) {
  const [fullName, setFullName] = useState(currentUser.full_name)
  const [email, setEmail] = useState(currentUser.email)

  const [profileLoading, setProfileLoading] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  const [profileError, setProfileError] = useState('')

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)

  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const handleProfileUpdate = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()
    setProfileMessage('')
    setProfileError('')

    if (fullName.trim().length < 2) {
      setProfileError('Please enter a valid full name.')
      return
    }

    try {
      setProfileLoading(true)

      const updatedUser = await updateUserProfile({
        full_name: fullName.trim(),
        email: email.trim(),
      })

      onUserUpdated(updatedUser)
      setProfileMessage('Your profile has been updated successfully.')
    } catch (error) {
      setProfileError(getErrorMessage(error))
    } finally {
      setProfileLoading(false)
    }
  }

  const handlePasswordChange = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()
    setPasswordMessage('')
    setPasswordError('')

    if (newPassword.length < 12) {
      setPasswordError(
        'Your new password must contain at least 12 characters.',
      )
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('The new passwords do not match.')
      return
    }

    if (currentPassword === newPassword) {
      setPasswordError(
        'Your new password must be different from your current password.',
      )
      return
    }

    try {
      setPasswordLoading(true)

      const result = await changeUserPassword({
        current_password: currentPassword,
        new_password: newPassword,
      })

      setPasswordMessage(
        result.message || 'Password changed successfully.',
      )

      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')

      onPasswordChanged()
    } catch (error) {
      setPasswordError(getErrorMessage(error))
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <section className="settings-page">

      <div className="settings-card">
        <div className="settings-card-heading">
          <div className="settings-icon">
            <UserRound size={19} />
          </div>
          <div>
            <h3>Personal Information</h3>
            <p>Update your account details.</p>
          </div>
        </div>

        <form onSubmit={handleProfileUpdate}>
          <div className="settings-form-grid">
            <label className="settings-field">
              <span>Full name</span>
              <div className="settings-input-wrap">
                <UserRound size={17} />
                <input
                  type="text"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  minLength={2}
                  maxLength={120}
                  required
                  placeholder="Enter your full name"
                />
              </div>
            </label>

            <label className="settings-field">
              <span>Email address</span>
              <div className="settings-input-wrap">
                <Mail size={17} />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  placeholder="Enter your email"
                />
              </div>
            </label>

            <div className="settings-field">
              <span>Account role</span>
              <div className="settings-readonly">
                <ShieldCheck size={17} />
                <span>{currentUser.role.replace('_', ' ')}</span>
              </div>
            </div>

            <div className="settings-field">
              <span>Account status</span>
              <div className="settings-readonly">
                <span
                  className={
                    currentUser.is_active
                      ? 'settings-status-dot active'
                      : 'settings-status-dot inactive'
                  }
                />
                <span>
                  {currentUser.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          {profileError && (
            <div className="settings-alert error" role="alert">
              {profileError}
            </div>
          )}

          {profileMessage && (
            <div className="settings-alert success" role="status">
              {profileMessage}
            </div>
          )}

          <div className="settings-actions">
            <button
              type="submit"
              className="settings-save-button"
              disabled={profileLoading}
            >
              <Save size={16} />
              {profileLoading ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="settings-card">
        <div className="settings-card-heading">
          <div className="settings-icon">
            <LockKeyhole size={19} />
          </div>
          <div>
            <h3>Change Password</h3>
            <p>Keep your LedgerLine account secure.</p>
          </div>
        </div>

        <form onSubmit={handlePasswordChange}>
          <div className="settings-password-grid">
            <label className="settings-field">
              <span>Current password</span>
              <div className="settings-input-wrap">
                <LockKeyhole size={17} />
                <input
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(event) =>
                    setCurrentPassword(event.target.value)
                  }
                  required
                  autoComplete="current-password"
                  placeholder="Enter current password"
                />
                <button
                  type="button"
                  className="settings-eye-button"
                  onClick={() =>
                    setShowCurrentPassword(!showCurrentPassword)
                  }
                  aria-label="Toggle current password visibility"
                >
                  {showCurrentPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}
                </button>
              </div>
            </label>

            <label className="settings-field">
              <span>New password</span>
              <div className="settings-input-wrap">
                <LockKeyhole size={17} />
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={12}
                  maxLength={128}
                  required
                  autoComplete="new-password"
                  placeholder="Minimum 12 characters"
                />
                <button
                  type="button"
                  className="settings-eye-button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  aria-label="Toggle new password visibility"
                >
                  {showNewPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}
                </button>
              </div>
            </label>

            <label className="settings-field">
              <span>Confirm new password</span>
              <div className="settings-input-wrap">
                <LockKeyhole size={17} />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(event.target.value)
                  }
                  minLength={12}
                  maxLength={128}
                  required
                  autoComplete="new-password"
                  placeholder="Confirm your new password"
                />
              </div>
            </label>
          </div>

          <p className="settings-password-hint">
            Your new password must contain at least 12 characters.
          </p>

          {passwordError && (
            <div className="settings-alert error" role="alert">
              {passwordError}
            </div>
          )}

          {passwordMessage && (
            <div className="settings-alert success" role="status">
              {passwordMessage}
            </div>
          )}

          <div className="settings-actions">
            <button
              type="submit"
              className="settings-save-button"
              disabled={passwordLoading}
            >
              <LockKeyhole size={16} />
              {passwordLoading ? 'Updating...' : 'Update password'}
            </button>
          </div>
        </form>
      </div>

      <div className="settings-security-note">
        <ShieldCheck size={19} />
        <div>
          <strong>Your security matters</strong>
          <p>
            Never share your password or account credentials with anyone.
          </p>
        </div>
      </div>
    </section>
  )
}