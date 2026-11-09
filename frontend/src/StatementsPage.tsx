
import { useCallback, useEffect, useState } from 'react'
import {
  RefreshCw,
  FileText,
  AlertCircle,
} from 'lucide-react'

import { getAccountStatement } from './services/banking'
import type {
  Account,
  AccountStatement,
  StatementItem,
} from './types/banking'

import './StatementsPage.css'

interface StatementsPageProps {
  accounts: Account[]
}

const formatINR = (paise: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(paise / 100)

const formatDate = (value: string) => {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const statusLabel = (status: StatementItem['status']) => {
  switch (status) {
    case 'POSTED':
      return 'Completed'
    case 'PENDING':
      return 'Pending'
    case 'REJECTED':
      return 'Rejected'
  }
}

function getError(error: unknown): string {
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

  return 'Unable to load the account statement. Please try again.'
}

export default function StatementsPage({
  accounts,
}: StatementsPageProps) {
  const eligibleAccounts = accounts.filter(
    (account) => !account.is_system,
  )

  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [statement, setStatement] = useState<AccountStatement | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  // Use the selected account if it still exists.
  // Otherwise, automatically use the first available customer account.
  const effectiveAccountId = eligibleAccounts.some(
    (account) => account.id === selectedAccountId,
  )
    ? selectedAccountId
    : (eligibleAccounts[0]?.id ?? '')

  const loadStatement = useCallback(
    async (accountId: string, refresh = false) => {
      if (!accountId) return

      if (refresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      setError('')

      try {
        const result = await getAccountStatement(accountId)
        setStatement(result)
      } catch (err) {
        setStatement(null)
        setError(getError(err))
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [],
  )

  // Automatically load the statement whenever the effective account changes.
  useEffect(() => {
    if (!effectiveAccountId) {
      return
    }

    let active = true

    async function fetchStatement() {
      setLoading(true)
      setError('')
      setStatement(null)

      try {
        const result = await getAccountStatement(effectiveAccountId)

        if (active) {
          setStatement(result)
        }
      } catch (err) {
        if (active) {
          setError(getError(err))
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void fetchStatement()

    return () => {
      active = false
    }
  }, [effectiveAccountId])

  const totalDebitPaise =
    statement?.items.reduce(
      (total, item) =>
        total +
        (item.status === 'REJECTED'
          ? item.attempted_debit_paise
          : item.debit_paise),
      0,
    ) ?? 0

  const totalCreditPaise =
    statement?.items.reduce(
      (total, item) =>
        total +
        (item.status === 'REJECTED'
          ? item.attempted_credit_paise
          : item.credit_paise),
      0,
    ) ?? 0

  return (
    <div className="statements-page">
      <section className="statements-heading">
        <div>
          <h2>Account statements</h2>
          <p>
            Review account activity, ledger entries and running balances.
          </p>
        </div>

        <button
          type="button"
          className="outline-button"
          onClick={() => void loadStatement(effectiveAccountId, true)}
          disabled={!effectiveAccountId || loading || refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? 'refresh-spinning' : ''}
          />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </section>

      {eligibleAccounts.length === 0 ? (
        <div className="panel statements-empty">
          <FileText size={30} />
          <h3>No accounts available</h3>
          <p>
            There are no customer accounts available for statements.
          </p>
        </div>
      ) : (
        <>
          <section className="panel statements-account-selector">
            <label htmlFor="statement-account">
              Select account
            </label>

            <select
              id="statement-account"
              value={effectiveAccountId}
              onChange={(event) =>
                setSelectedAccountId(event.target.value)
              }
            >
              {eligibleAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.account_number} — {account.currency}
                </option>
              ))}
            </select>
          </section>

          {error && (
            <div className="statements-alert" role="alert">
              <AlertCircle size={17} />
              <span>{error}</span>
              <button
                type="button"
                onClick={() =>
                  void loadStatement(effectiveAccountId)
                }
              >
                Retry
              </button>
            </div>
          )}

          {loading ? (
            <div className="panel statements-empty">
              <RefreshCw
                className="refresh-spinning"
                size={25}
              />
              <h3>Loading statement</h3>
              <p>
                Please wait while we retrieve account activity.
              </p>
            </div>
          ) : statement ? (
            <>
              <section className="statements-summary">
                <article className="statements-summary-card">
                  <span>Opening balance</span>
                  <strong>
                    {formatINR(statement.opening_balance_paise)}
                  </strong>
                </article>

                <article className="statements-summary-card">
                  <span>Total debit</span>
                  <strong className="statement-debit">
                    {formatINR(totalDebitPaise)}
                  </strong>
                </article>

                <article className="statements-summary-card">
                  <span>Total credit</span>
                  <strong className="statement-credit">
                    {formatINR(totalCreditPaise)}
                  </strong>
                </article>

                <article className="statements-summary-card closing">
                  <span>Closing balance</span>
                  <strong>
                    {formatINR(statement.closing_balance_paise)}
                  </strong>
                </article>
              </section>

              <section className="panel statements-table-panel">
                <div className="statements-panel-heading">
                  <div>
                    <h3>Ledger activity</h3>
                    <p>
                      Account {statement.account_number} ·{' '}
                      {statement.items.length} records
                    </p>
                  </div>
                </div>

                {statement.items.length === 0 ? (
                  <div className="statements-empty">
                    <FileText size={27} />
                    <h3>No statement entries</h3>
                    <p>
                      Transactions for this account will appear here.
                    </p>
                  </div>
                ) : (
                  <div className="statements-table-wrapper">
                    <table className="statements-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Reference</th>
                          <th>Type</th>
                          <th>Status</th>
                          <th>Debit</th>
                          <th>Credit</th>
                          <th>Running balance</th>
                        </tr>
                      </thead>

                      <tbody>
                        {statement.items.map((item) => {
                          const debit =
                            item.status === 'REJECTED'
                              ? item.attempted_debit_paise
                              : item.debit_paise

                          const credit =
                            item.status === 'REJECTED'
                              ? item.attempted_credit_paise
                              : item.credit_paise

                          return (
                            <tr key={item.transaction_id}>
                              <td className="statement-date">
                                {formatDate(item.created_at)}
                              </td>

                              <td>
                                <strong>{item.reference}</strong>
                                <small className="statement-description">
                                  {item.description ||
                                    'Banking transaction'}
                                </small>
                              </td>

                              <td>
                                <span className="statement-type">
                                  {item.transaction_type}
                                </span>
                              </td>

                              <td>
                                <span
                                  className={`transactions-status status-${item.status.toLowerCase()}`}
                                >
                                  {statusLabel(item.status)}
                                </span>
                              </td>

                              <td className="statement-debit">
                                {debit > 0 ? formatINR(debit) : '—'}
                              </td>

                              <td className="statement-credit">
                                {credit > 0 ? formatINR(credit) : '—'}
                              </td>

                              <td>
                                <strong>
                                  {formatINR(
                                    item.running_balance_paise,
                                  )}
                                </strong>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                <p className="statements-note">
                  Rejected entries display attempted debit or credit
                  amounts. They do not represent posted changes to
                  the account balance.
                </p>
              </section>
            </>
          ) : null}
        </>
      )}
    </div>
  )
}
