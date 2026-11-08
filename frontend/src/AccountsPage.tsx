
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  RefreshCw,
  Search,
  Wallet,
  CreditCard,
  IndianRupee,
  Eye,
  Plus,
  X,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react'

import api from './lib/api'
import type { Account, AccountStatus } from './types/banking'
import type { User } from './types/auth'

type AccountsPageProps = {
  currentUser: User
}

type AccountHolderOption = {
  id: string
  full_name: string
  email: string
}

const formatINR = (paise: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(paise / 100)

const formatDate = (date: string) =>
  new Date(date).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

function getErrorMessage(error: unknown): string {
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
          status?: number
        }
      }
    ).response

    const detail = response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      return detail.map((item: unknown) => {
        if (
          typeof item === 'object' &&
          item !== null &&
          'msg' in item
        ) {
          const message = String(item.msg)
          const location =
            'loc' in item && Array.isArray(item.loc)
              ? item.loc.join(' → ')
              : ''

          return location ? `${location}: ${message}` : message
        }

        return String(item)
      }).join('; ')
    }

    if (detail !== undefined && detail !== null) {
      return String(detail)
    }

    if (response?.status === 401) {
      return 'Your session has expired. Please sign in again.'
    }

    if (response?.status === 403) {
      return 'You do not have permission to perform this action.'
    }

    if (response?.status === 404) {
      return 'The requested resource was not found.'
    }

    if (response?.status === 422) {
      return 'The submitted information is invalid.'
    }

    if (response?.status && response.status >= 500) {
      return 'A server error occurred. Please try again later.'
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong. Please try again.'
}

export default function AccountsPage({
  currentUser,
}: AccountsPageProps) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')

  const [selectedAccount, setSelectedAccount] =
    useState<Account | null>(null)

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [holders, setHolders] = useState<AccountHolderOption[]>([])
  const [selectedHolderId, setSelectedHolderId] = useState('')
  const [loadingHolders, setLoadingHolders] = useState(false)
  const [creating, setCreating] = useState(false)

  const [updatingId, setUpdatingId] = useState<string | null>(null)

  const isAdmin = currentUser.role === 'ADMIN'

  // Load accounts
  const loadAccounts = useCallback(async () => {
    const response = await api.get<Account[]>('/accounts')
    setAccounts(response.data)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function fetchAccounts() {
      try {
        const response = await api.get<Account[]>('/accounts')

        if (!cancelled) {
          setAccounts(response.data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(getErrorMessage(err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void fetchAccounts()

    return () => {
      cancelled = true
    }
  }, [])

  // Load eligible customers when admin opens create form
  useEffect(() => {
    if (!isAdmin || !showCreateForm) {
      return
    }

    let cancelled = false

    async function fetchEligibleHolders() {
      setLoadingHolders(true)
      setError('')

      try {
        const response = await api.get<AccountHolderOption[]>(
          '/accounts/eligible-holders',
        )

        if (!cancelled) {
          setHolders(response.data)

          setSelectedHolderId((current) => {
            if (
              current &&
              response.data.some((holder) => holder.id === current)
            ) {
              return current
            }

            return ''
          })
        }
      } catch (err) {
        if (!cancelled) {
          setError(getErrorMessage(err))
        }
      } finally {
        if (!cancelled) {
          setLoadingHolders(false)
        }
      }
    }

    void fetchEligibleHolders()

    return () => {
      cancelled = true
    }
  }, [isAdmin, showCreateForm])

  // Refresh account information
  const handleRefresh = async () => {
    setRefreshing(true)
    setError('')

    try {
      await loadAccounts()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRefreshing(false)
    }
  }

  // Search and filter
  const filteredAccounts = useMemo(() => {
    const query = search.trim().toLowerCase()

    return accounts.filter((account) => {
      const matchesSearch =
        !query ||
        account.account_number.toLowerCase().includes(query) ||
        account.owner_id.toLowerCase().includes(query) ||
        account.id.toLowerCase().includes(query)

      const matchesStatus =
        statusFilter === 'ALL' ||
        account.status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [accounts, search, statusFilter])

  const activeCount = accounts.filter(
    (account) => account.status === 'ACTIVE',
  ).length

  const systemAccountCount = accounts.filter(
    (account) => account.is_system,
  ).length

  const totalBalance = accounts.reduce(
    (total, account) => total + account.balance_paise,
    0,
  )

  // Create account using selected customer's UUID internally
  async function handleCreateAccount(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!selectedHolderId) {
      setError('Please select an account holder.')
      return
    }

    setCreating(true)
    setError('')
    setSuccess('')

    try {
      await api.post('/accounts', {
        owner_id: selectedHolderId,
      })

      const selectedHolder = holders.find(
        (holder) => holder.id === selectedHolderId,
      )

      setShowCreateForm(false)
      setSelectedHolderId('')

      setSuccess(
        `Account created successfully for ${selectedHolder?.full_name ?? 'the selected customer'}.`,
      )

      await loadAccounts()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setCreating(false)
    }
  }

  // Update account status
  async function handleStatusChange(
    account: Account,
    newStatus: AccountStatus,
  ) {
    if (account.is_system) {
      setError('System account status cannot be changed here.')
      return
    }

    const confirmed = window.confirm(
      `Change account ${account.account_number} to ${newStatus}?`,
    )

    if (!confirmed) return

    setUpdatingId(account.id)
    setError('')
    setSuccess('')

    try {
      const response = await api.patch<Account>(
        `/accounts/${account.id}/status`,
        { status: newStatus },
      )

      setAccounts((previous) =>
        previous.map((item) =>
          item.id === account.id ? response.data : item,
        ),
      )

      setSelectedAccount((previous) =>
        previous?.id === account.id ? response.data : previous,
      )

      setSuccess(`Account status changed to ${newStatus}.`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="accounts-page">
      {/* Page heading */}
      <section className="welcome-section">
        <div>
          <div className="date-label">
            {new Date()
              .toLocaleDateString('en-IN', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })
              .toUpperCase()}
          </div>

          <h1>Accounts</h1>
          <p>Manage and review your account information.</p>
        </div>

        <div className="accounts-header-actions">
          <button
            className="outline-button"
            onClick={() => void handleRefresh()}
            disabled={refreshing || loading}
          >
            <RefreshCw
              size={14}
              className={refreshing ? 'refresh-spinning' : ''}
            />
            <span>
              {refreshing ? 'Refreshing...' : 'Refresh data'}
            </span>
          </button>

          {isAdmin && (
            <button
              className="accounts-primary-button"
              onClick={() => {
                setError('')
                setSuccess('')
                setShowCreateForm((value) => !value)
              }}
            >
              {showCreateForm ? <X size={15} /> : <Plus size={15} />}
              {showCreateForm ? 'Cancel' : 'Create account'}
            </button>
          )}
        </div>
      </section>

      {/* Error message */}
      {error && (
        <div className="accounts-alert accounts-alert-error" role="alert">
          <AlertCircle size={17} />
          <span>{error}</span>
          <button onClick={() => setError('')} aria-label="Dismiss error">
            <X size={15} />
          </button>
        </div>
      )}

      {/* Success message */}
      {success && (
        <div className="accounts-alert accounts-alert-success">
          <CheckCircle2 size={17} />
          <span>{success}</span>
          <button onClick={() => setSuccess('')} aria-label="Dismiss message">
            <X size={15} />
          </button>
        </div>
      )}

      {/* Create account */}
      {showCreateForm && isAdmin && (
        <section className="panel accounts-create-panel">
          <div className="panel-heading">
            <div>
              <h2>Create a new account</h2>
              <p>Select an existing active account holder.</p>
            </div>
          </div>

          <form onSubmit={handleCreateAccount}>
            <label htmlFor="account-holder">
              Select account holder
            </label>

            <div className="accounts-create-row">
              <select
                id="account-holder"
                value={selectedHolderId}
                onChange={(event) =>
                  setSelectedHolderId(event.target.value)
                }
                disabled={loadingHolders || creating}
                required
              >
                <option value="">
                  {loadingHolders
                    ? 'Loading account holders...'
                    : holders.length === 0
                      ? 'No eligible account holders found'
                      : 'Choose a customer'}
                </option>

                {holders.map((holder) => (
                  <option key={holder.id} value={holder.id}>
                    {holder.full_name} — {holder.email}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                className="accounts-primary-button"
                disabled={
                  creating ||
                  loadingHolders ||
                  !selectedHolderId
                }
              >
                {creating ? 'Creating...' : 'Create account'}
              </button>
            </div>

            {selectedHolderId && (
              <div className="accounts-selected-holder">
                <CheckCircle2 size={15} />
                <span>
                  Selected:{' '}
                  <strong>
                    {holders.find(
                      (holder) => holder.id === selectedHolderId,
                    )?.full_name}
                  </strong>
                </span>
              </div>
            )}

            <p className="accounts-form-hint">
              The account number will be generated automatically.
              Only active Account Holders are available for selection.
            </p>
          </form>
        </section>
      )}

      {/* Summary cards */}
      <section className="accounts-stats-grid">
        <div className="stat-card">
          <div className="stat-top">
            Total accounts
            <span className="stat-icon accounts-icon">
              <Wallet size={17} />
            </span>
          </div>
          <div className="stat-amount">{accounts.length}</div>
          <div className="stat-foot">
            Accounts retrieved from LedgerLine
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            Active accounts
            <span className="stat-icon income-icon">
              <CheckCircle2 size={17} />
            </span>
          </div>
          <div className="stat-amount">{activeCount}</div>
          <div className="stat-foot">Currently active</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            Total balance
            <span className="stat-icon accounts-icon">
              <IndianRupee size={17} />
            </span>
          </div>
          <div className="stat-amount">{formatINR(totalBalance)}</div>
          <div className="stat-foot">
            Combined listed account balances
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            System accounts
            <span className="stat-icon expense-icon">
              <ShieldCheck size={17} />
            </span>
          </div>
          <div className="stat-amount">{systemAccountCount}</div>
          <div className="stat-foot">
            Internal LedgerLine accounts
          </div>
        </div>
      </section>

      {/* Accounts table */}
      <section className="panel accounts-table-panel">
        <div className="panel-heading accounts-table-heading">
          <div>
            <h2>All accounts</h2>
            <p>
              {filteredAccounts.length} of {accounts.length} accounts displayed
            </p>
          </div>
        </div>

        <div className="accounts-toolbar">
          <div className="accounts-search">
            <Search size={16} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search account number or owner ID..."
            />
          </div>

          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter accounts by status"
          >
            <option value="ALL">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="FROZEN">Frozen</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>

        {loading ? (
          <div className="accounts-empty-state">
            <RefreshCw size={22} className="refresh-spinning" />
            <p>Loading accounts...</p>
          </div>
        ) : filteredAccounts.length === 0 ? (
          <div className="accounts-empty-state">
            <CreditCard size={30} />
            <h3>No accounts found</h3>
            <p>
              {accounts.length === 0
                ? 'There are no accounts available for this user.'
                : 'Try changing your search or status filter.'}
            </p>
          </div>
        ) : (
          <div className="accounts-table-wrapper">
            <table className="accounts-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Account holder ID</th>
                  <th>Balance</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredAccounts.map((account) => (
                  <tr key={account.id}>
                    <td>
                      <div className="accounts-number-cell">
                        <span className="accounts-row-icon">
                          {account.is_system ? (
                            <ShieldCheck size={17} />
                          ) : (
                            <CreditCard size={17} />
                          )}
                        </span>

                        <div>
                          <strong>{account.account_number}</strong>
                          <small>
                            {account.is_system
                              ? 'System account'
                              : 'Customer account'}
                          </small>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="accounts-owner-id">
                        {account.owner_id}
                      </span>
                    </td>

                    <td>
                      <strong>{formatINR(account.balance_paise)}</strong>
                    </td>

                    <td>
                      <span
                        className={`accounts-status accounts-status-${account.status.toLowerCase()}`}
                      >
                        {account.status}
                      </span>
                    </td>

                    <td>{formatDate(account.created_at)}</td>

                    <td>
                      <div className="accounts-row-actions">
                        <button
                          className="accounts-icon-action"
                          title="View account details"
                          onClick={() => setSelectedAccount(account)}
                        >
                          <Eye size={16} />
                        </button>

                        {isAdmin &&
                          !account.is_system &&
                          account.status !== 'CLOSED' && (
                            <select
                              aria-label={`Change status for ${account.account_number}`}
                              value={account.status}
                              disabled={updatingId === account.id}
                              onChange={(event) =>
                                void handleStatusChange(
                                  account,
                                  event.target.value as AccountStatus,
                                )
                              }
                            >
                              <option value="ACTIVE">Active</option>
                              <option value="FROZEN">Frozen</option>
                              <option value="CLOSED">Closed</option>
                            </select>
                          )}

                        {account.is_system && (
                          <span className="accounts-system-label">
                            Protected
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Account details modal */}
      {selectedAccount && (
        <div
          className="accounts-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedAccount(null)
            }
          }}
        >
          <section
            className="accounts-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="account-detail-title"
          >
            <div className="accounts-modal-header">
              <div>
                <span className="date-label">
                  {selectedAccount.is_system
                    ? 'SYSTEM ACCOUNT'
                    : 'CUSTOMER ACCOUNT'}
                </span>
                <h2 id="account-detail-title">Account details</h2>
              </div>

              <button
                className="accounts-icon-action"
                onClick={() => setSelectedAccount(null)}
                aria-label="Close account details"
              >
                <X size={18} />
              </button>
            </div>

            <div className="accounts-detail-balance">
              <span>Current balance</span>
              <strong>
                {formatINR(selectedAccount.balance_paise)}
              </strong>
            </div>

            <dl className="accounts-detail-list">
              <div>
                <dt>Account number</dt>
                <dd>{selectedAccount.account_number}</dd>
              </div>

              <div>
                <dt>Account ID</dt>
                <dd>{selectedAccount.id}</dd>
              </div>

              <div>
                <dt>Owner ID</dt>
                <dd>{selectedAccount.owner_id}</dd>
              </div>

              <div>
                <dt>Currency</dt>
                <dd>{selectedAccount.currency}</dd>
              </div>

              <div>
                <dt>Status</dt>
                <dd>{selectedAccount.status}</dd>
              </div>

              <div>
                <dt>Account type</dt>
                <dd>
                  {selectedAccount.is_system
                    ? 'System account'
                    : 'Customer account'}
                </dd>
              </div>

              <div>
                <dt>Created</dt>
                <dd>{formatDate(selectedAccount.created_at)}</dd>
              </div>
            </dl>
          </section>
        </div>
      )}
    </div>
  )
}
