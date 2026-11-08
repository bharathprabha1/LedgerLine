
import { useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import {
  X,
  Wallet,
  ArrowLeftRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Search,
  UserRound,
  ArrowRight,
  LockKeyhole,
} from 'lucide-react'

import {
  lookupRecipient,
  transferMoney,
} from './services/banking'

import type {
  Account,
  RecipientLookup,
} from './types/banking'

interface TransferModalProps {
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

    const maxSafePaise = BigInt(Number.MAX_SAFE_INTEGER)

    if (totalPaise <= 0n || totalPaise > maxSafePaise) {
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
            detail?: string
          }
        }
      }
    ).response

    if (response?.data?.detail) {
      return response.data.detail
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unable to process your transfer. Please try again.'
}

export default function TransferModal({
  accounts,
  onClose,
  onSuccess,
}: TransferModalProps) {
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

  const [sourceAccountId, setSourceAccountId] = useState(
    eligibleAccounts[0]?.id ?? '',
  )

  const [accountNumber, setAccountNumber] = useState('')
  const [recipient, setRecipient] = useState<RecipientLookup | null>(null)
  const [lookingUp, setLookingUp] = useState(false)

  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('Account transfer')

  const [reviewing, setReviewing] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [error, setError] = useState('')
  const [successReference, setSuccessReference] = useState('')

  const idempotencyRef = useRef<IdempotencyEntry | null>(null)

  const selectedAccount = eligibleAccounts.find(
    (account) => account.id === sourceAccountId,
  )

  const amountPaise = rupeesToPaise(amount)

  const amountError =
    amount.trim() === ''
      ? ''
      : amountPaise === null
        ? 'Enter a valid amount with up to two decimal places.'
        : selectedAccount && amountPaise > selectedAccount.balance_paise
          ? 'Transfer amount exceeds your available balance.'
          : ''

  const recipientAccountNumber = accountNumber.trim()

  const canLookup =
    recipientAccountNumber.length > 0 &&
    !lookingUp &&
    !submitting

  const recipientVerified =
    recipient !== null &&
    recipient.account_number === recipientAccountNumber

  async function handleRecipientLookup() {
    setError('')
    setRecipient(null)
    setReviewing(false)

    if (!recipientAccountNumber) {
      setError('Please enter the recipient account number.')
      return
    }

    if (!selectedAccount) {
      setError('Please select an eligible source account.')
      return
    }

    setLookingUp(true)

    try {
      const result = await lookupRecipient(recipientAccountNumber)

      if (result.id === selectedAccount.id) {
        setError('You cannot transfer money to your own account.')
        return
      }

      if (result.currency !== selectedAccount.currency) {
        setError('Recipient account currency does not match your account.')
        return
      }

      setRecipient(result)
    } catch (err) {
      setError(getApiError(err))
    } finally {
      setLookingUp(false)
    }
  }

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (!selectedAccount) {
      setError('Please select an eligible source account.')
      return
    }

    if (!recipientVerified || !recipient) {
      setError('Please verify the recipient account first.')
      return
    }

    if (recipient.id === selectedAccount.id) {
      setError('You cannot transfer money to your own account.')
      return
    }

    if (amountPaise === null) {
      setError('Please enter a valid transfer amount.')
      return
    }

    if (amountPaise > selectedAccount.balance_paise) {
      setError('Insufficient account balance.')
      return
    }

    if (description.trim().length > 500) {
      setError('Description cannot exceed 500 characters.')
      return
    }

    setReviewing(true)
  }

  async function handleConfirmTransfer() {
    if (!selectedAccount || !recipient || !recipientVerified) {
      setError('Recipient verification is required.')
      setReviewing(false)
      return
    }

    if (amountPaise === null) {
      setError('Please enter a valid transfer amount.')
      setReviewing(false)
      return
    }

    if (amountPaise > selectedAccount.balance_paise) {
      setError('Insufficient account balance.')
      setReviewing(false)
      return
    }

    const request = {
      source_account_id: selectedAccount.id,
      destination_account_id: recipient.id,
      amount_paise: amountPaise,
      description: description.trim() || 'Account transfer',
    }

    const fingerprint = JSON.stringify(request)

    // Reuse the key for an identical retry.
    // A changed request receives a new key.
    if (
      !idempotencyRef.current ||
      idempotencyRef.current.fingerprint !== fingerprint
    ) {
      idempotencyRef.current = {
        fingerprint,
        key: crypto.randomUUID(),
      }
    }

    setSubmitting(true)
    setError('')

    try {
      const result = await transferMoney(
        request,
        idempotencyRef.current.key,
      )

      if (result.status !== 'POSTED') {
        setError(
          `The transfer was not posted. Current status: ${result.status}.`,
        )
        return
      }

      setSuccessReference(result.reference)
      idempotencyRef.current = null

      await onSuccess()
    } catch (err) {
      // Keep the idempotency key after an uncertain response.
      // An identical retry must not create a second transfer.
      setError(getApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  function handleClose() {
    if (!submitting && !lookingUp) {
      onClose()
    }
  }

  return (
    <div
      className="deposit-modal-overlay"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget &&
          !submitting &&
          !lookingUp
        ) {
          onClose()
        }
      }}
    >
      <section
        className="deposit-modal transfer-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transfer-title"
      >
        <div className="deposit-modal-header">
          <div className="deposit-heading-icon transfer-heading-icon">
            <ArrowLeftRight size={21} />
          </div>

          <div className="deposit-heading-text">
            <h2 id="transfer-title">Transfer money</h2>
            <p>Send money securely to another LedgerLine account.</p>
          </div>

          <button
            type="button"
            className="deposit-close-button"
            onClick={handleClose}
            disabled={submitting || lookingUp}
            aria-label="Close transfer window"
          >
            <X size={19} />
          </button>
        </div>

        {successReference ? (
          <div className="deposit-success">
            <div className="deposit-success-icon">
              <CheckCircle2 size={35} />
            </div>

            <h3>Transfer successful!</h3>

            <p>
              Your transfer has been posted successfully.
              The account balances have been updated.
            </p>

            <div className="transfer-success-recipient">
              <span>Sent to</span>
              <strong>{recipient?.holder_name}</strong>
              <small>{recipient?.account_number}</small>
            </div>

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
        ) : reviewing ? (
          <div className="transfer-review">
            <div className="deposit-notice">
              <ShieldCheck size={17} />
              <span>Review carefully before confirming this transfer.</span>
            </div>

            {error && (
              <div className="deposit-error" role="alert">
                <AlertCircle size={17} />
                <span>{error}</span>
              </div>
            )}

            <div className="transfer-review-amount">
              <span>Transfer amount</span>
              <strong>
                {amountPaise !== null ? formatINR(amountPaise) : '—'}
              </strong>
            </div>

            <div className="transfer-party-card">
              <div className="transfer-party">
                <div className="transfer-party-icon">
                  <Wallet size={18} />
                </div>
                <div>
                  <small>FROM</small>
                  <strong>{selectedAccount?.account_number}</strong>
                  <span>Your account</span>
                </div>
              </div>

              <div className="transfer-arrow">
                <ArrowRight size={19} />
              </div>

              <div className="transfer-party">
                <div className="transfer-party-icon recipient-party-icon">
                  <UserRound size={18} />
                </div>
                <div>
                  <small>TO</small>
                  <strong>{recipient?.holder_name}</strong>
                  <span>{recipient?.account_number}</span>
                </div>
              </div>
            </div>

            <div className="deposit-summary">
              <div>
                <span>Current balance</span>
                <strong>
                  {selectedAccount
                    ? formatINR(selectedAccount.balance_paise)
                    : '—'}
                </strong>
              </div>

              <div>
                <span>Transfer amount</span>
                <strong>
                  {amountPaise !== null ? formatINR(amountPaise) : '—'}
                </strong>
              </div>

              <div className="deposit-summary-total">
                <span>Remaining balance</span>
                <strong>
                  {selectedAccount && amountPaise !== null
                    ? formatINR(
                        selectedAccount.balance_paise - amountPaise,
                      )
                    : '—'}
                </strong>
              </div>
            </div>

            <div className="transfer-security-note">
              <LockKeyhole size={16} />
              <span>
                This transfer will be processed as one atomic banking
                transaction. Do not submit it more than once.
              </span>
            </div>

            <div className="deposit-modal-actions">
              <button
                type="button"
                className="deposit-secondary-button"
                onClick={() => setReviewing(false)}
                disabled={submitting}
              >
                Back
              </button>

              <button
                type="button"
                className="deposit-primary-button"
                onClick={() => void handleConfirmTransfer()}
                disabled={submitting}
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
                    <LockKeyhole size={16} />
                    Confirm and send
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleReview}>
            <div className="deposit-notice">
              <ShieldCheck size={17} />
              <span>
                Simulated banking operation. No real money will be
                transferred.
              </span>
            </div>

            {error && (
              <div className="deposit-error" role="alert">
                <AlertCircle size={17} />
                <span>{error}</span>
              </div>
            )}

            <div className="deposit-form-group">
              <label htmlFor="transfer-source-account">
                Transfer from
              </label>

              <select
                id="transfer-source-account"
                value={sourceAccountId}
                onChange={(event) => {
                  setSourceAccountId(event.target.value)
                  setRecipient(null)
                  setReviewing(false)
                  setError('')
                }}
                disabled={submitting || eligibleAccounts.length === 0}
                required
              >
                {eligibleAccounts.length === 0 ? (
                  <option value="">No eligible accounts available</option>
                ) : (
                  eligibleAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
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
                  <span>Available account balance</span>
                  <strong>
                    {formatINR(selectedAccount.balance_paise)}
                  </strong>
                </div>

                <span className="deposit-active-label">ACTIVE</span>
              </div>
            )}

            <div className="deposit-form-group">
              <label htmlFor="transfer-recipient">
                Recipient account number
              </label>

              <div className="transfer-recipient-input">
                <input
                  id="transfer-recipient"
                  type="text"
                  autoComplete="off"
                  placeholder="Enter LedgerLine account number"
                  value={accountNumber}
                  onChange={(event) => {
                    setAccountNumber(event.target.value.trimStart())
                    setRecipient(null)
                    setReviewing(false)
                    setError('')
                  }}
                  disabled={submitting || lookingUp}
                  required
                />

                <button
                  type="button"
                  className="transfer-lookup-button"
                  onClick={() => void handleRecipientLookup()}
                  disabled={!canLookup}
                >
                  {lookingUp ? (
                    <Loader2 size={16} className="transfer-spin" />
                  ) : (
                    <Search size={16} />
                  )}
                  Verify
                </button>
              </div>
            </div>

            {recipientVerified && recipient && (
              <div className="deposit-account-preview transfer-recipient-preview">
                <div className="deposit-preview-icon recipient-party-icon">
                  <UserRound size={19} />
                </div>

                <div>
                  <span>Verified recipient</span>
                  <strong>{recipient.holder_name}</strong>
                  <span>
                    {recipient.account_number} · {recipient.currency}
                  </span>
                </div>

                <span className="deposit-active-label">
                  VERIFIED
                </span>
              </div>
            )}

            <div className="deposit-form-group">
              <label htmlFor="transfer-amount">
                Transfer amount
              </label>

              <div className="deposit-amount-input">
                <span>₹</span>

                <input
                  id="transfer-amount"
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
              <label htmlFor="transfer-description">
                Description{' '}
                <span className="deposit-optional">Optional</span>
              </label>

              <input
                id="transfer-description"
                type="text"
                maxLength={500}
                placeholder="Enter transfer description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
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
                  <span>Transfer amount</span>
                  <strong>{formatINR(amountPaise)}</strong>
                </div>

                <div className="deposit-summary-total">
                  <span>Remaining balance</span>
                  <strong>
                    {amountPaise <= selectedAccount.balance_paise
                      ? formatINR(
                          selectedAccount.balance_paise - amountPaise,
                        )
                      : 'Insufficient balance'}
                  </strong>
                </div>
              </div>
            )}

            <div className="deposit-modal-actions">
              <button
                type="button"
                className="deposit-secondary-button"
                onClick={handleClose}
                disabled={submitting || lookingUp}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="deposit-primary-button"
                disabled={
                  !selectedAccount ||
                  !recipientVerified ||
                  !recipient ||
                  amountPaise === null ||
                  Boolean(amountError) ||
                  submitting ||
                  lookingUp
                }
              >
                <ArrowLeftRight size={17} />
                Review transfer
              </button>
            </div>

            <p className="deposit-notice">
              The recipient is verified against the active account
              records. The backend performs the final authorization,
              balance and transaction checks.
            </p>
          </form>
        )}
      </section>
    </div>
  )
}
