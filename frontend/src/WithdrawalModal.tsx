
import { useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import {
  X,
  Wallet,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'

import { withdrawMoney } from './services/banking'
import type { Account } from './types/banking'

import './DepositModal.css'

interface WithdrawalModalProps {
  accounts: Account[]
  onClose: () => void
  onSuccess: () => Promise<void>
}

interface IdempotencyEntry {
  fingerprint: string
  key: string
}

function formatINR(paise: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(paise / 100)
}

function rupeesToPaise(value: string): number | null {
  const normalized = value.trim()

  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null
  }

  try {
    const [rupees, paise = ''] = normalized.split('.')

    const totalPaise =
      BigInt(rupees) * 100n +
      BigInt(paise.padEnd(2, '0') || '0')

    if (
      totalPaise <= 0n ||
      totalPaise > BigInt(Number.MAX_SAFE_INTEGER)
    ) {
      return null
    }

    return Number(totalPaise)
  } catch {
    return null
  }
}

function getApiError(error: unknown): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error
  ) {
    const response = (
      error as {
        response?: {
          data?: {
            detail?: unknown
          }
        }
      }
    ).response

    const detail = response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === 'object' &&
          item !== null &&
          'msg' in item
            ? String(item.msg)
            : String(item),
        )
        .join(', ')
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unable to process your withdrawal. Please try again.'
}

export default function WithdrawalModal({
  accounts,
  onClose,
  onSuccess,
}: WithdrawalModalProps) {
  const eligibleAccounts = useMemo(
    () =>
      accounts.filter(
        (account) =>
          account.status === 'ACTIVE' &&
          !account.is_system &&
          account.currency === 'INR',
      ),
    [accounts],
  )

  const [accountId, setAccountId] = useState(
    eligibleAccounts[0]?.id ?? '',
  )

  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState(
    'Account withdrawal',
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successReference, setSuccessReference] = useState('')

  const idempotencyRef = useRef<IdempotencyEntry | null>(null)

  const selectedAccount = eligibleAccounts.find(
    (account) => account.id === accountId,
  )

  const amountPaise = rupeesToPaise(amount)

  const amountError =
    amount.trim() === ''
      ? ''
      : amountPaise === null
        ? 'Enter a valid amount with up to two decimal places.'
        : selectedAccount &&
            amountPaise > selectedAccount.balance_paise
          ? 'Withdrawal amount exceeds the available balance.'
          : ''

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    setError('')

    if (!selectedAccount) {
      setError('Please select an eligible active account.')
      return
    }

    if (amountPaise === null) {
      setError('Please enter a valid withdrawal amount.')
      return
    }

    if (amountPaise > selectedAccount.balance_paise) {
      setError('Insufficient available balance.')
      return
    }

    if (description.trim().length > 500) {
      setError('Description cannot exceed 500 characters.')
      return
    }

    const request = {
      account_id: selectedAccount.id,
      amount_paise: amountPaise,
      description:
        description.trim() || 'Account withdrawal',
    }

    const fingerprint = JSON.stringify(request)

    if (
      !idempotencyRef.current ||
      idempotencyRef.current.fingerprint !== fingerprint
    ) {
      idempotencyRef.current = {
        fingerprint,
        key: crypto.randomUUID(),
      }
    }

    const idempotencyKey = idempotencyRef.current.key

    setSubmitting(true)

    try {
      const result = await withdrawMoney(
        request,
        idempotencyKey,
      )

      if (result.status !== 'POSTED') {
        setError(
          `The withdrawal was not posted. Current status: ${result.status}.`,
        )
        return
      }

      setSuccessReference(result.reference)

      idempotencyRef.current = null

      await onSuccess()
    } catch (err) {
      // Retain the key for an identical retry.
      setError(getApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="deposit-modal-overlay"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget &&
          !submitting
        ) {
          onClose()
        }
      }}
    >
      <section
        className="deposit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="withdrawal-title"
      >
        <div className="deposit-modal-header">
          <div className="deposit-heading-icon">
            <ArrowUpRight size={21} />
          </div>

          <div className="deposit-heading-text">
            <h2 id="withdrawal-title">
              Withdraw money
            </h2>
            <p>
              Withdraw funds from your available account balance.
            </p>
          </div>

          <button
            type="button"
            className="deposit-close-button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close withdrawal window"
          >
            <X size={19} />
          </button>
        </div>

        {successReference ? (
          <div className="deposit-success">
            <div className="deposit-success-icon">
              <CheckCircle2 size={35} />
            </div>

            <h3>Withdrawal successful!</h3>

            <p>
              Your withdrawal has been posted successfully.
            </p>

            <div className="deposit-reference">
              <span>Transaction reference</span>
              <strong>{successReference}</strong>
            </div>

            <button
              type="button"
              className="deposit-primary-button"
              onClick={onClose}
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="deposit-notice">
              <ShieldCheck size={17} />
              <span>
                Simulated banking operation. This withdrawal
                does not involve an actual cash payment.
              </span>
            </div>

            {error && (
              <div className="deposit-error" role="alert">
                <AlertCircle size={17} />
                <span>{error}</span>
              </div>
            )}

            <div className="deposit-form-group">
              <label htmlFor="withdrawal-account">
                Select account
              </label>

              <select
                id="withdrawal-account"
                value={accountId}
                onChange={(event) => {
                  setAccountId(event.target.value)
                  setError('')
                }}
                disabled={submitting}
                required
              >
                {eligibleAccounts.length === 0 ? (
                  <option value="">
                    No eligible accounts available
                  </option>
                ) : (
                  eligibleAccounts.map((account) => (
                    <option
                      key={account.id}
                      value={account.id}
                    >
                      {account.account_number} · {account.currency}
                    </option>
                  ))
                )}
              </select>
            </div>

            {selectedAccount && (
              <div className="deposit-account-preview">
                <div className="deposit-preview-icon">
                  <Wallet size={19} />
                </div>

                <div>
                  <span>Available balance</span>
                  <strong>
                    {formatINR(selectedAccount.balance_paise)}
                  </strong>
                </div>

                <span className="deposit-active-label">
                  ACTIVE
                </span>
              </div>
            )}

            <div className="deposit-form-group">
              <label htmlFor="withdrawal-amount">
                Withdrawal amount
              </label>

              <div className="deposit-amount-input">
                <span>₹</span>

                <input
                  id="withdrawal-amount"
                  type="text"
                  inputMode="decimal"
                  autoComplete="off"
                  placeholder="0.00"
                  value={amount}
                  onChange={(event) => {
                    setAmount(event.target.value)
                    setError('')
                  }}
                  disabled={submitting}
                  required
                />
              </div>

              {amountError && (
                <small className="deposit-field-error">
                  {amountError}
                </small>
              )}
            </div>

            <div className="deposit-form-group">
              <label htmlFor="withdrawal-description">
                Description
                <span className="deposit-optional">
                  {' '}Optional
                </span>
              </label>

              <input
                id="withdrawal-description"
                type="text"
                maxLength={500}
                placeholder="Enter withdrawal description"
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                disabled={submitting}
              />
            </div>

            {amountPaise !== null && selectedAccount && (
              <div className="deposit-summary">
                <div>
                  <span>Current balance</span>
                  <strong>
                    {formatINR(selectedAccount.balance_paise)}
                  </strong>
                </div>

                <div>
                  <span>Withdrawal amount</span>
                  <strong>{formatINR(amountPaise)}</strong>
                </div>

                <div className="deposit-summary-total">
                  <span>Remaining balance</span>
                  <strong>
                    {formatINR(
                      selectedAccount.balance_paise -
                        amountPaise,
                    )}
                  </strong>
                </div>
              </div>
            )}

            <div className="deposit-modal-actions">
              <button
                type="button"
                className="deposit-secondary-button"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="deposit-primary-button"
                disabled={
                  submitting ||
                  !selectedAccount ||
                  amountPaise === null ||
                  Boolean(amountError)
                }
              >
                {submitting ? (
                  <>
                    <Loader2
                      size={17}
                      className="deposit-spinner"
                    />
                    Processing...
                  </>
                ) : (
                  <>
                    <ArrowUpRight size={17} />
                    Confirm withdrawal
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
