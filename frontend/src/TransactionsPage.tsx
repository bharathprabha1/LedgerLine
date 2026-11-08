import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Search,
  RefreshCw,
  ArrowDownLeft,
  ArrowUpRight,
  ArrowLeftRight,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  FileText,
  AlertCircle,
} from 'lucide-react'

import api from './lib/api'
import { getTransactions } from './services/banking'
import type {
  Transaction,
  TransactionType,
  TransactionStatus,
  TransactionHistory,
} from './types/banking'

import './TransactionsPage.css'

type Filter = 'ALL' | TransactionType
type StatusFilter = 'ALL' | TransactionStatus

const PAGE_SIZE = 10

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

const statusLabel = (status: TransactionStatus) => {
  switch (status) {
    case 'POSTED':
      return 'Completed'
    case 'PENDING':
      return 'Pending'
    case 'REJECTED':
      return 'Rejected'
  }
}

const typeLabel = (type: TransactionType) =>
  type.charAt(0) + type.slice(1).toLowerCase()

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

  return 'Unable to load transactions. Please try again.'
}

export default function TransactionsPage() {
  const [history, setHistory] = useState<TransactionHistory>({
    items: [],
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
  })

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('ALL')
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>('ALL')

  const [page, setPage] = useState(0)

  const [selected, setSelected] =
    useState<Transaction | null>(null)

  const [detailLoading, setDetailLoading] = useState(false)

  // Load transaction history.
  const loadTransactions = useCallback(
    async (currentPage: number, isRefresh = false) => {
      if (isRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      setError('')

      try {
        const result = await getTransactions(
          PAGE_SIZE,
          currentPage * PAGE_SIZE,
        )

        setHistory(result)
      } catch (err) {
        setError(getError(err))
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [],
  )

  // Fetch transactions whenever the page changes.
  useEffect(() => {
    let active = true

    async function fetchHistory() {
      setLoading(true)
      setError('')

      try {
        const result = await getTransactions(
          PAGE_SIZE,
          page * PAGE_SIZE,
        )

        if (active) {
          setHistory(result)
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

    void fetchHistory()

    return () => {
      active = false
    }
  }, [page])

  // Search and filter the currently loaded page.
  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase()

    return history.items.filter((item) => {
      const matchesType =
        filter === 'ALL' ||
        item.transaction_type === filter

      const matchesStatus =
        statusFilter === 'ALL' ||
        item.status === statusFilter

      const matchesSearch =
        !query ||
        item.reference.toLowerCase().includes(query) ||
        (item.description ?? '').toLowerCase().includes(query) ||
        item.id.toLowerCase().includes(query)

      return (
        matchesType &&
        matchesStatus &&
        matchesSearch
      )
    })
  }, [history.items, filter, statusFilter, search])

  // Statistics.
  const totalPages = Math.max(
    1,
    Math.ceil(history.total / PAGE_SIZE),
  )

  const postedCount = history.items.filter(
    (item) => item.status === 'POSTED',
  ).length

  const pendingCount = history.items.filter(
    (item) => item.status === 'PENDING',
  ).length

  const rejectedCount = history.items.filter(
    (item) => item.status === 'REJECTED',
  ).length

  // Open transaction details.
  const openDetails = async (item: Transaction) => {
    setSelected(item)
    setDetailLoading(true)
    setError('')

    try {
      const response = await api.get<Transaction>(
        `/transactions/${encodeURIComponent(item.id)}`,
      )

      setSelected(response.data)
    } catch (err) {
      setError(getError(err))
    } finally {
      setDetailLoading(false)
    }
  }

  const closeDetails = () => {
    setSelected(null)
    setDetailLoading(false)
  }

  // Transaction icons.
  const iconForType = (type: TransactionType) => {
    switch (type) {
      case 'DEPOSIT':
        return <ArrowDownLeft size={18} />

      case 'WITHDRAWAL':
        return <ArrowUpRight size={18} />

      case 'TRANSFER':
        return <ArrowLeftRight size={18} />
    }
  }

  return (
    <div className="transactions-page">

      {/* Statistics */}
      <section className="transactions-stats">

        <article className="transactions-stat-card">
          <div className="transactions-stat-heading">
            <span>Total transactions</span>

            <span className="transactions-stat-icon total">
              <FileText size={18} />
            </span>
          </div>

          <strong className="transactions-stat-value">
            {history.total}
          </strong>

          <span className="transactions-stat-caption">
            All recorded activity
          </span>
        </article>

        <article className="transactions-stat-card">
          <div className="transactions-stat-heading">
            <span>Completed on this page</span>

            <span className="transactions-stat-icon completed">
              <ArrowDownLeft size={18} />
            </span>
          </div>

          <strong className="transactions-stat-value">
            {postedCount}
          </strong>

          <span className="transactions-stat-caption">
            Successfully posted
          </span>
        </article>

        <article className="transactions-stat-card">
          <div className="transactions-stat-heading">
            <span>Pending on this page</span>

            <span className="transactions-stat-icon pending">
              <RefreshCw size={18} />
            </span>
          </div>

          <strong className="transactions-stat-value">
            {pendingCount}
          </strong>

          <span className="transactions-stat-caption">
            {rejectedCount} rejected on this page
          </span>
        </article>

      </section>

      {/* Error message */}
      {error && (
        <div className="transactions-alert" role="alert">
          <AlertCircle size={17} />

          <span>{error}</span>

          <button
            type="button"
            onClick={() => setError('')}
            aria-label="Dismiss error"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Transaction history */}
      <section className="panel transactions-page-panel">

        <div className="transactions-panel-heading">

          <div>
            <h2>Transaction history</h2>

            <p>
              View, search and track your banking activity.
            </p>
          </div>

          <button
            type="button"
            className="outline-button transactions-refresh-button"
            onClick={() => void loadTransactions(page, true)}
            disabled={refreshing || loading}
          >
            <RefreshCw
              size={15}
              className={
                refreshing ? 'refresh-spinning' : ''
              }
            />

            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>

        </div>

        {/* Search and filters */}
        <div className="transactions-toolbar">

          <label className="transactions-search">
            <Search size={17} />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search reference, description or ID..."
              aria-label="Search transactions on this page"
            />

            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                aria-label="Clear search"
              >
                <X size={15} />
              </button>
            )}
          </label>

          <label className="transactions-select-wrap">
            <span>Type</span>

            <select
              value={filter}
              onChange={(event) =>
                setFilter(event.target.value as Filter)
              }
              aria-label="Filter by transaction type"
            >
              <option value="ALL">All types</option>
              <option value="DEPOSIT">Deposits</option>
              <option value="WITHDRAWAL">Withdrawals</option>
              <option value="TRANSFER">Transfers</option>
            </select>
          </label>

          <label className="transactions-select-wrap">
            <span>Status</span>

            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(
                  event.target.value as StatusFilter,
                )
              }
              aria-label="Filter by transaction status"
            >
              <option value="ALL">All statuses</option>
              <option value="POSTED">Completed</option>
              <option value="PENDING">Pending</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </label>

        </div>

        <div className="transactions-results-label">
          {loading
            ? 'Loading records...'
            : `Showing ${filteredItems.length} of ${history.items.length} records on this page`}
        </div>

        {/* Transaction table */}
        <div className="transactions-table-wrapper">

          {loading ? (

            <div className="transactions-empty">
              <RefreshCw
                className="refresh-spinning"
                size={24}
              />

              <h3>Loading transactions</h3>

              <p>
                Please wait while we retrieve your activity.
              </p>
            </div>

          ) : filteredItems.length === 0 ? (

            <div className="transactions-empty">

              <span className="transactions-empty-icon">
                <FileText size={27} />
              </span>

              <h3>
                {history.items.length === 0
                  ? 'No transactions yet'
                  : 'No matching transactions'}
              </h3>

              <p>
                {history.items.length === 0
                  ? 'Your deposits, withdrawals and transfers will appear here.'
                  : 'Try another search term or change your filters.'}
              </p>

              {(search ||
                filter !== 'ALL' ||
                statusFilter !== 'ALL') && (
                <button
                  type="button"
                  className="transactions-clear-filters"
                  onClick={() => {
                    setSearch('')
                    setFilter('ALL')
                    setStatusFilter('ALL')
                  }}
                >
                  Clear filters
                </button>
              )}

            </div>

          ) : (

            <table className="transactions-table">

              <thead>
                <tr>
                  <th>Transaction</th>
                  <th>Reference</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>

              <tbody>
                {filteredItems.map((item) => (

                  <tr key={item.id}>

                    <td>
                      <div className="transactions-type-cell">

                        <span
                          className={`transactions-type-icon ${item.transaction_type.toLowerCase()}`}
                        >
                          {iconForType(item.transaction_type)}
                        </span>

                        <span>
                          <strong>
                            {typeLabel(item.transaction_type)}
                          </strong>

                          <small>
                            {item.description || 'Banking transaction'}
                          </small>
                        </span>

                      </div>
                    </td>

                    <td>
                      <span className="transactions-reference">
                        {item.reference}
                      </span>
                    </td>

                    <td>
                      <strong className="transactions-amount">
                        {formatINR(item.amount_paise)}
                      </strong>
                    </td>

                    <td>
                      <span
                        className={`transactions-status status-${item.status.toLowerCase()}`}
                      >
                        {statusLabel(item.status)}
                      </span>
                    </td>

                    <td className="transactions-date">
                      {formatDate(item.created_at)}
                    </td>

                    <td>
                      <button
                        type="button"
                        className="transactions-view-button"
                        title="View transaction details"
                        aria-label={`View details for ${item.reference}`}
                        onClick={() => void openDetails(item)}
                      >
                        <Eye size={16} />
                      </button>
                    </td>

                  </tr>

                ))}
              </tbody>

            </table>

          )}

        </div>

        {/* Pagination */}
        <div className="transactions-pagination">

          <span>
            Page {page + 1} of {totalPages}
            <span className="transactions-pagination-dot">·</span>
            {history.total} total records
          </span>

          <div className="transactions-pagination-actions">

            <button
              type="button"
              className="outline-button"
              disabled={page === 0 || loading}
              onClick={() =>
                setPage((value) => Math.max(0, value - 1))
              }
            >
              <ChevronLeft size={16} />
              Previous
            </button>

            <button
              type="button"
              className="outline-button"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
              <ChevronRight size={16} />
            </button>

          </div>
        </div>

      </section>

      {/* Transaction detail modal */}
      {selected && (

        <div
          className="accounts-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDetails()
            }
          }}
        >

          <section
            className="accounts-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="transaction-detail-title"
          >

            <div className="accounts-modal-header">

              <div>
                <span className="date-label">
                  TRANSACTION DETAILS
                </span>

                <h2 id="transaction-detail-title">
                  Transaction information
                </h2>
              </div>

              <button
                type="button"
                className="accounts-icon-action"
                onClick={closeDetails}
                aria-label="Close details"
              >
                <X size={18} />
              </button>

            </div>

            {detailLoading ? (

              <div className="transactions-empty transactions-detail-loading">
                <RefreshCw
                  className="refresh-spinning"
                  size={22}
                />

                <p>Loading transaction details...</p>
              </div>

            ) : (

              <>

                <div className="transactions-detail-summary">

                  <span>
                    {typeLabel(selected.transaction_type)}
                  </span>

                  <strong>
                    {formatINR(selected.amount_paise)}
                  </strong>

                  <span
                    className={`transactions-status status-${selected.status.toLowerCase()}`}
                  >
                    {statusLabel(selected.status)}
                  </span>

                </div>

                <dl className="accounts-detail-list">

                  <div>
                    <dt>Reference</dt>
                    <dd>{selected.reference}</dd>
                  </div>

                  <div>
                    <dt>Transaction ID</dt>
                    <dd>{selected.id}</dd>
                  </div>

                  <div>
                    <dt>Type</dt>
                    <dd>{typeLabel(selected.transaction_type)}</dd>
                  </div>

                  <div>
                    <dt>Status</dt>
                    <dd>{statusLabel(selected.status)}</dd>
                  </div>

                  <div>
                    <dt>Source account</dt>
                    <dd>
                      {selected.source_account_id ?? 'Not applicable'}
                    </dd>
                  </div>

                  <div>
                    <dt>Destination account</dt>
                    <dd>
                      {selected.destination_account_id ?? 'Not applicable'}
                    </dd>
                  </div>

                  <div>
                    <dt>Description</dt>
                    <dd>
                      {selected.description || 'No description'}
                    </dd>
                  </div>

                  <div>
                    <dt>Initiated by</dt>
                    <dd>{selected.initiated_by}</dd>
                  </div>

                  <div>
                    <dt>Date</dt>
                    <dd>{formatDate(selected.created_at)}</dd>
                  </div>

                </dl>

              </>

            )}

          </section>

        </div>

      )}

    </div>
  )
}