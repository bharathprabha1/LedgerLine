
import { useEffect, useState } from 'react'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Bell,
  CircleHelp,
  CreditCard,
  LayoutDashboard,
  LogOut,
  MoreHorizontal,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Wallet,
  ArrowUpDown,
  FileText,
  Menu,
  X,
  RefreshCw,
} from 'lucide-react'

import AuthScreen from './AuthScreen'
import AccountsPage from './AccountsPage'
import TransactionsPage from './TransactionsPage'
import DepositModal from './DepositModal'
import WithdrawalModal from './WithdrawalModal'
import TransferModal from './TransferModal'

import {
  getCurrentUser,
  getStoredToken,
  logoutUser,
} from './services/auth'

import {
  getAccounts,
  getTransactions,
} from './services/banking'

import type { User } from './types/auth'

import type {
  Account,
  Transaction as ApiTransaction,
  TransactionType,
  TransactionStatus,
} from './types/banking'

import './App.css'

type TransactionFilter = 'All' | 'Deposit' | 'Withdrawal' | 'Transfer'

type DashboardTransaction = {
  id: string
  name: string
  reference: string
  date: string
  amountPaise: number
  type: TransactionType
  status: TransactionStatus
}

const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Accounts', icon: Wallet },
  { label: 'Transactions', icon: ArrowLeftRight },
  { label: 'Statements', icon: FileText },
]

function getInitials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function formatCurrencyFromPaise(amountPaise: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amountPaise / 100)
}

function formatDate(dateValue: string) {
  const date = new Date(dateValue)

  if (Number.isNaN(date.getTime())) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function getApiErrorMessage(error: unknown): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error
  ) {
    const response = error.response

    if (
      typeof response === 'object' &&
      response !== null &&
      'data' in response
    ) {
      const data = response.data

      if (
        typeof data === 'object' &&
        data !== null &&
        'detail' in data &&
        typeof data.detail === 'string'
      ) {
        return data.detail
      }
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unable to load your banking information. Please try again.'
}

function mapTransaction(
  transaction: ApiTransaction,
  accounts: Account[],
): DashboardTransaction {
  const ownedAccountIds = new Set(accounts.map((account) => account.id))

  let name = ''
  let amountPaise = transaction.amount_paise

  switch (transaction.transaction_type) {
    case 'DEPOSIT':
      name = 'Money deposited'
      break

    case 'WITHDRAWAL':
      name = 'Money withdrawn'
      amountPaise = -transaction.amount_paise
      break

    case 'TRANSFER': {
      const sentFromMyAccount =
        transaction.source_account_id !== null &&
        ownedAccountIds.has(transaction.source_account_id)

      const receivedIntoMyAccount =
        transaction.destination_account_id !== null &&
        ownedAccountIds.has(transaction.destination_account_id)

      if (sentFromMyAccount) {
        name = 'Transfer sent'
        amountPaise = -transaction.amount_paise
      } else if (receivedIntoMyAccount) {
        name = 'Transfer received'
        amountPaise = transaction.amount_paise
      } else {
        name = 'Account transfer'
      }
      break
    }
  }

  return {
    id: transaction.id,
    name,
    reference: transaction.description || transaction.reference,
    date: formatDate(transaction.created_at),
    amountPaise,
    type: transaction.transaction_type,
    status: transaction.status,
  }
}

function getStatusLabel(status: TransactionStatus) {
  switch (status) {
    case 'POSTED':
      return 'Completed'
    case 'PENDING':
      return 'Pending'
    case 'REJECTED':
      return 'Rejected'
  }
}

function App() {
  // Authentication state
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [authChecked, setAuthChecked] = useState(false)

  // Dashboard navigation state
  const [activePage, setActivePage] = useState('Overview')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeFilter, setActiveFilter] =
    useState<TransactionFilter>('All')

  // Live backend data
  const [accounts, setAccounts] = useState<Account[]>([])
  const [apiTransactions, setApiTransactions] = useState<ApiTransaction[]>([])
  const [totalTransactions, setTotalTransactions] = useState(0)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardError, setDashboardError] = useState('')

  // Transaction modal states
  const [depositOpen, setDepositOpen] = useState(false)
  const [withdrawalOpen, setWithdrawalOpen] = useState(false)
  const [transferOpen, setTransferOpen] = useState(false)

  // Restore and validate an existing login session.
  useEffect(() => {
    let active = true

    async function restoreSession() {
      const token = getStoredToken()

      if (!token) {
        if (active) {
          setAuthChecked(true)
        }
        return
      }

      try {
        const user = await getCurrentUser()

        if (active) {
          setCurrentUser(user)
        }
      } catch {
        logoutUser()

        if (active) {
          setCurrentUser(null)
        }
      } finally {
        if (active) {
          setAuthChecked(true)
        }
      }
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [])

  // Fetch real accounts and transaction history for the logged-in user.
  const userId = currentUser?.id

  useEffect(() => {
    if (!userId) return

    let active = true

    async function loadDashboard() {
      setDashboardLoading(true)
      setDashboardError('')

      try {
        const [accountData, transactionData] = await Promise.all([
          getAccounts(),
          getTransactions(100, 0),
        ])

        if (!active) return

        setAccounts(accountData)
        setApiTransactions(transactionData.items)
        setTotalTransactions(transactionData.total)
      } catch (error) {
        if (!active) return

        setDashboardError(getApiErrorMessage(error))
      } finally {
        if (active) {
          setDashboardLoading(false)
        }
      }
    }

    void loadDashboard()

    return () => {
      active = false
    }
  }, [userId])

  // Handle successful login or registration.
  const handleAuthenticated = (user: User) => {
    setCurrentUser(user)
    setActivePage('Overview')
  }

  // Handle logout.
  const handleLogout = () => {
    logoutUser()
    setCurrentUser(null)
    setAccounts([])
    setApiTransactions([])
    setTotalTransactions(0)
    setDashboardError('')
    setDashboardLoading(false)
    setDepositOpen(false)
    setWithdrawalOpen(false)
    setTransferOpen(false)
    setActivePage('Overview')
    setMobileMenuOpen(false)
  }

  const closeMobileMenu = () => setMobileMenuOpen(false)

  // Refresh account and transaction data.
  const refreshDashboard = async () => {
    if (!currentUser) return

    setDashboardLoading(true)
    setDashboardError('')

    try {
      const [accountData, transactionData] = await Promise.all([
        getAccounts(),
        getTransactions(100, 0),
      ])

      setAccounts(accountData)
      setApiTransactions(transactionData.items)
      setTotalTransactions(transactionData.total)
    } catch (error) {
      setDashboardError(getApiErrorMessage(error))
    } finally {
      setDashboardLoading(false)
    }
  }

  // Calculate the balance from actual account records.
  const totalBalancePaise = accounts.reduce(
    (total, account) => total + account.balance_paise,
    0,
  )

  const activeAccounts = accounts.filter(
    (account) => account.status === 'ACTIVE',
  )

  // Only POSTED transactions are included in these calculations.
  // These figures cover the latest 100 fetched transactions.
  const postedTransactions = apiTransactions.filter(
    (transaction) => transaction.status === 'POSTED',
  )

  const totalDepositsPaise = postedTransactions
    .filter((transaction) => transaction.transaction_type === 'DEPOSIT')
    .reduce((total, transaction) => total + transaction.amount_paise, 0)

  const totalWithdrawalsPaise = postedTransactions
    .filter((transaction) => transaction.transaction_type === 'WITHDRAWAL')
    .reduce((total, transaction) => total + transaction.amount_paise, 0)

  const dashboardTransactions = apiTransactions.map((transaction) =>
    mapTransaction(transaction, accounts),
  )

  const filteredTransactions = dashboardTransactions.filter(
    (transaction) =>
      activeFilter === 'All' ||
      transaction.type === activeFilter.toUpperCase(),
  )

  const recentTransactions = filteredTransactions.slice(0, 5)

  const primaryAccount =
    activeAccounts[0] ?? accounts[0] ?? null

  const initials = currentUser
    ? getInitials(currentUser.full_name)
    : ''

  // Loading screen while validating the login session.
  if (!authChecked) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-mark">
          <Wallet size={25} />
        </div>
        <p>Checking your secure session...</p>
      </div>
    )
  }

  // Never show the dashboard without authentication.
  if (!currentUser) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />
  }

  return (
    <div className="app-shell">

      {mobileMenuOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={closeMobileMenu}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${mobileMenuOpen ? 'sidebar-open' : ''}`}>

        <div className="brand">
          <div className="brand-mark">
            <Wallet size={21} strokeWidth={2.3} />
          </div>

          <span>
            Ledger<span className="brand-light">Line</span>
          </span>

          <button
            className="mobile-close"
            onClick={closeMobileMenu}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="navigation">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${
                activePage === label ? 'nav-active' : ''
              }`}
              onClick={() => {
                setActivePage(label)
                closeMobileMenu()
              }}
            >
              <Icon size={19} />
              <span>{label}</span>

              {label === 'Transactions' && totalTransactions > 0 && (
                <span className="nav-count">
                  {totalTransactions > 99 ? '99+' : totalTransactions}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="workspace-label tools-label">
          PREFERENCES
        </div>

        <nav className="navigation">
          <button
            className={`nav-item ${
              activePage === 'Settings' ? 'nav-active' : ''
            }`}
            onClick={() => {
              setActivePage('Settings')
              closeMobileMenu()
            }}
          >
            <Settings size={19} />
            <span>Settings</span>
          </button>

          <button
            className={`nav-item ${
              activePage === 'Help & Support' ? 'nav-active' : ''
            }`}
            onClick={() => {
              setActivePage('Help & Support')
              closeMobileMenu()
            }}
          >
            <CircleHelp size={19} />
            <span>Help & Support</span>
          </button>
        </nav>

        {/* Sidebar bottom */}
        <div className="sidebar-bottom">

          <div className="security-card">
            <div className="security-icon">
              <ShieldCheck size={19} />
            </div>

            <strong>Your money, protected</strong>

            <p>
              Secure banking with transparent transaction records.
            </p>
          </div>

          <div className="profile-row">
            <div className="avatar">{initials}</div>

            <div className="profile-info">
              <strong>{currentUser.full_name}</strong>
              <span>{currentUser.role.replace(/_/g, ' ')}</span>
            </div>

            <MoreHorizontal size={19} />
          </div>

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            <LogOut size={17} />
            <span>Sign out</span>
          </button>

        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">

        {/* Top navigation */}
        <header className="topbar">

          <div className="topbar-left">
            <button
              className="mobile-menu-button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={22} />
            </button>

            <div className="breadcrumb">
              <span>Workspace</span>
              <span className="breadcrumb-separator">/</span>
              <strong>{activePage}</strong>
            </div>
          </div>

          <div className="topbar-actions">

            <button
              className="search-button"
              aria-label="Search"
              disabled
              title="Search is not available yet"
            >
              <Search size={18} />
              <span>Search anything...</span>
              <kbd>Ctrl K</kbd>
            </button>

            <button
              className="notification-button"
              aria-label="Notifications"
              title="Notifications are not available yet"
            >
              <Bell size={19} />
            </button>

            <div className="topbar-avatar">{initials}</div>

          </div>
        </header>

        <div className="dashboard-container">

          {activePage !== 'Accounts' && activePage !== 'Transactions' && (
            <section className="welcome-section">

              <div>
                <div className="date-label">
                  {new Intl.DateTimeFormat('en-IN', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                  }).format(new Date()).toUpperCase()}
                </div>

                <h1>
                  {activePage === 'Overview'
                    ? `Welcome, ${currentUser.full_name.split(' ')[0]}`
                    : activePage}
                </h1>

                <p>
                  {activePage === 'Overview'
                    ? "Here's what's happening with your finances today."
                    : `Manage and review your ${activePage.toLowerCase()} information.`}
                </p>
              </div>

              <button
                className="outline-button"
                onClick={() => void refreshDashboard()}
                disabled={dashboardLoading}
                title="Refresh account information"
              >
                <RefreshCw
                  size={16}
                  className={dashboardLoading ? 'refresh-spinning' : ''}
                />
                <span>Refresh data</span>
              </button>

            </section>
          )}

          {activePage === 'Accounts' ? (
            <AccountsPage currentUser={currentUser} />
          ) : activePage === 'Transactions' ? (
            <TransactionsPage />
          ) : activePage === 'Overview' ? (
            <>

              {/* Backend status and data information */}
              <div className="demo-data-notice">
                <ShieldCheck size={16} />
                <span>
                  Live account information from LedgerLine. Deposit and
                  withdrawal summaries use the latest 100 transactions.
                </span>
              </div>

              {dashboardError && (
                <div className="dashboard-error" role="alert">
                  <strong>Unable to load banking information.</strong>
                  <p>{dashboardError}</p>
                  <button
                    className="text-button"
                    onClick={() => void refreshDashboard()}
                  >
                    Try again
                  </button>
                </div>
              )}

              {/* Statistics */}
              <section className="stats-grid">

                <article className="stat-card balance-card">
                  <div className="stat-top">
                    <span>Total balance</span>
                    <div className="stat-icon balance-icon">
                      <Wallet size={19} />
                    </div>
                  </div>

                  <div className="balance-amount">
                    {dashboardLoading
                      ? 'Loading...'
                      : formatCurrencyFromPaise(totalBalancePaise)}
                  </div>

                  <div className="stat-foot">
                    <span>
                      {accounts.length} account
                      {accounts.length === 1 ? '' : 's'}
                    </span>
                    <span>Current account balances</span>
                  </div>

                  <div className="balance-decoration decoration-one" />
                  <div className="balance-decoration decoration-two" />
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Posted deposits</span>
                    <div className="stat-icon income-icon">
                      <ArrowDownLeft size={19} />
                    </div>
                  </div>

                  <div className="stat-amount">
                    {dashboardLoading
                      ? 'Loading...'
                      : formatCurrencyFromPaise(totalDepositsPaise)}
                  </div>

                  <div className="stat-foot">
                    <span className="trend-positive">
                      <ArrowDownLeft size={14} /> Deposits
                    </span>
                    <span>Latest 100 records</span>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Posted withdrawals</span>
                    <div className="stat-icon expense-icon">
                      <ArrowUpRight size={19} />
                    </div>
                  </div>

                  <div className="stat-amount">
                    {dashboardLoading
                      ? 'Loading...'
                      : formatCurrencyFromPaise(totalWithdrawalsPaise)}
                  </div>

                  <div className="stat-foot">
                    <span className="trend-negative">
                      <ArrowUpRight size={14} /> Withdrawals
                    </span>
                    <span>Latest 100 records</span>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-top">
                    <span>Active accounts</span>
                    <div className="stat-icon accounts-icon">
                      <CreditCard size={19} />
                    </div>
                  </div>

                  <div className="stat-amount">
                    {dashboardLoading ? '...' : activeAccounts.length}
                  </div>

                  <div className="stat-foot">
                    <span className="account-caption">
                      {accounts.length} total account
                      {accounts.length === 1 ? '' : 's'}
                    </span>
                  </div>
                </article>

              </section>

              {/* Quick actions */}
              <section className="quick-actions-section">

                <div className="section-heading">
                  <div>
                    <h2>Quick actions</h2>
                    <p>
                      {currentUser.role === 'ACCOUNT_HOLDER'
                        ? 'Manage your account transactions'
                        : 'Transaction actions are restricted for your role'}
                    </p>
                  </div>
                </div>

                <div className="quick-actions">

                  {/* Deposit */}
                  <button
                    className="quick-action"
                    type="button"
                    disabled={currentUser.role !== 'ACCOUNT_HOLDER'}
                    onClick={() => setDepositOpen(true)}
                    title={
                      currentUser.role === 'ACCOUNT_HOLDER'
                        ? 'Deposit funds into your account'
                        : 'Only account holders can deposit money'
                    }
                  >
                    <span className="quick-icon deposit-quick">
                      <Plus size={21} />
                    </span>

                    <span>
                      <strong>Add money</strong>
                      <small>Deposit funds</small>
                    </span>

                    <ArrowUpRight className="quick-arrow" size={17} />
                  </button>

                  {/* Transfer */}
                  <button
                    className="quick-action"
                    type="button"
                    disabled={currentUser.role !== 'ACCOUNT_HOLDER'}
                    onClick={() => setTransferOpen(true)}
                    title={
                      currentUser.role === 'ACCOUNT_HOLDER'
                        ? 'Transfer money to another eligible account'
                        : 'Only account holders can transfer money'
                    }
                  >
                    <span className="quick-icon transfer-quick">
                      <ArrowLeftRight size={21} />
                    </span>

                    <span>
                      <strong>Transfer</strong>
                      <small>Send money</small>
                    </span>

                    <ArrowUpRight className="quick-arrow" size={17} />
                  </button>

                  {/* Withdrawal */}
                  <button
                    className="quick-action"
                    type="button"
                    disabled={currentUser.role !== 'ACCOUNT_HOLDER'}
                    onClick={() => setWithdrawalOpen(true)}
                    title={
                      currentUser.role === 'ACCOUNT_HOLDER'
                        ? 'Withdraw funds from your account'
                        : 'Only account holders can withdraw money'
                    }
                  >
                    <span className="quick-icon withdraw-quick">
                      <ArrowUpRight size={21} />
                    </span>

                    <span>
                      <strong>Withdraw</strong>
                      <small>Take out money</small>
                    </span>

                    <ArrowUpRight className="quick-arrow" size={17} />
                  </button>

                </div>
              </section>

              {/* Transactions and accounts */}
              <section className="content-grid">

                <div className="panel transactions-panel">

                  <div className="panel-heading">
                    <div>
                      <h2>Recent transactions</h2>
                      <p>
                        {totalTransactions} transaction
                        {totalTransactions === 1 ? '' : 's'} recorded
                      </p>
                    </div>

                    <button
                      className="text-button"
                      onClick={() => setActivePage('Transactions')}
                    >
                      View all <ArrowUpRight size={15} />
                    </button>
                  </div>

                  <div className="transaction-filters">
                    {(
                      ['All', 'Deposit', 'Withdrawal', 'Transfer'] as
                        TransactionFilter[]
                    ).map((filter) => (
                      <button
                        key={filter}
                        className={`filter-button ${
                          activeFilter === filter ? 'filter-active' : ''
                        }`}
                        onClick={() => setActiveFilter(filter)}
                      >
                        {filter}
                      </button>
                    ))}
                  </div>

                  <div className="transaction-list">

                    {dashboardLoading && (
                      <div className="empty-state">
                        Loading transactions...
                      </div>
                    )}

                    {!dashboardLoading &&
                      !dashboardError &&
                      recentTransactions.map((transaction) => (
                        <div
                          className="transaction-row"
                          key={transaction.id}
                        >
                          <div
                            className={`transaction-icon ${
                              transaction.type.toLowerCase()
                            }`}
                          >
                            {transaction.type === 'DEPOSIT' && (
                              <ArrowDownLeft size={18} />
                            )}

                            {transaction.type === 'WITHDRAWAL' && (
                              <ArrowUpRight size={18} />
                            )}

                            {transaction.type === 'TRANSFER' && (
                              <ArrowLeftRight size={18} />
                            )}
                          </div>

                          <div className="transaction-details">
                            <strong>{transaction.name}</strong>

                            <span>
                              {transaction.reference} · {transaction.date}
                            </span>
                          </div>

                          <div className="transaction-values">
                            <strong
                              className={
                                transaction.amountPaise > 0
                                  ? 'amount-positive'
                                  : ''
                              }
                            >
                              {transaction.amountPaise > 0 ? '+' : ''}
                              {formatCurrencyFromPaise(
                                transaction.amountPaise,
                              )}
                            </strong>

                            <span
                              className={`status-${
                                transaction.status === 'POSTED'
                                  ? 'completed'
                                  : transaction.status === 'PENDING'
                                    ? 'pending'
                                    : 'failed'
                              } status`}
                            >
                              {getStatusLabel(transaction.status)}
                            </span>
                          </div>
                        </div>
                      ))}

                    {!dashboardLoading &&
                      !dashboardError &&
                      recentTransactions.length === 0 && (
                        <div className="empty-state">
                          {apiTransactions.length === 0
                            ? 'No transactions found. Your account activity will appear here.'
                            : 'No transactions in this category.'}
                        </div>
                      )}

                  </div>
                </div>

                {/* Account panel */}
                <div className="right-column">

                  <div className="panel account-panel">

                    <div className="panel-heading">
                      <div>
                        <h2>My accounts</h2>
                        <p>Your connected accounts</p>
                      </div>

                      <button
                        className="icon-button"
                        aria-label="Refresh accounts"
                        onClick={() => void refreshDashboard()}
                        disabled={dashboardLoading}
                      >
                        <RefreshCw size={17} />
                      </button>
                    </div>

                    {dashboardLoading ? (
                      <div className="empty-state">
                        Loading account information...
                      </div>
                    ) : primaryAccount ? (
                      <>
                        <div className="bank-card">

                          <div className="bank-card-top">
                            <div className="mini-brand">
                              <Wallet size={16} /> LedgerLine
                            </div>
                            <span>{primaryAccount.currency}</span>
                          </div>

                          <div className="bank-card-number">
                            •••• •••• ••••{' '}
                            {primaryAccount.account_number.slice(-4)}
                          </div>

                          <div className="bank-card-bottom">
                            <div>
                              <small>ACCOUNT HOLDER</small>
                              <strong>
                                {currentUser.full_name.toUpperCase()}
                              </strong>
                            </div>

                            <div className="card-chip">
                              <span />
                              <span />
                              <span />
                              <span />
                            </div>
                          </div>

                        </div>

                        <div className="account-balance-row">
                          <div>
                            <span>Account balance</span>
                            <strong>
                              {formatCurrencyFromPaise(
                                primaryAccount.balance_paise,
                              )}
                            </strong>
                          </div>

                          <span className="active-pill">
                            {primaryAccount.status}
                          </span>
                        </div>

                        <div className="account-number-caption">
                          Account ending in{' '}
                          {primaryAccount.account_number.slice(-4)}
                          {accounts.length > 1 &&
                            ` · ${accounts.length} accounts available`}
                        </div>
                      </>
                    ) : (
                      <div className="empty-state">
                        <CreditCard size={25} />
                        <p>
                          You do not have an account yet.
                        </p>
                        <p>
                          Contact an administrator to create an account.
                        </p>
                      </div>
                    )}

                  </div>

                  <div className="security-banner">
                    <div className="security-banner-icon">
                      <ShieldCheck size={20} />
                    </div>

                    <div>
                      <strong>Security matters</strong>
                      <p>
                        Your account activity is protected and recorded.
                      </p>
                    </div>
                  </div>

                </div>
              </section>

              {/* Footer */}
              <footer className="dashboard-footer">
                <span>© 2026 LedgerLine. All rights reserved.</span>

                <span>
                  <ShieldCheck size={14} />
                  Secure financial workspace
                </span>
              </footer>

            </>
          ) : (
            <section className="placeholder-panel">

              <div className="placeholder-icon">
                <ArrowUpDown size={27} />
              </div>

              <h2>{activePage}</h2>

              <p>
                This section's interface will be connected to the
                LedgerLine API in the next development steps.
              </p>

              <button
                className="primary-button"
                onClick={() => setActivePage('Overview')}
              >
                Back to overview
              </button>

            </section>
          )}

        </div>
      </main>

      {/* Deposit modal */}
      {depositOpen && currentUser.role === 'ACCOUNT_HOLDER' && (
        <DepositModal
          accounts={accounts}
          onClose={() => setDepositOpen(false)}
          onSuccess={async () => {
            await refreshDashboard()
          }}
        />
      )}

      {/* Withdrawal modal */}
      {withdrawalOpen &&
        currentUser.role === 'ACCOUNT_HOLDER' && (
          <WithdrawalModal
            accounts={accounts}
            onClose={() => setWithdrawalOpen(false)}
            onSuccess={async () => {
              await refreshDashboard()
            }}
          />
        )}

      {/* Transfer modal */}
      {transferOpen && currentUser.role === 'ACCOUNT_HOLDER' && (
        <TransferModal
          accounts={accounts}
          onClose={() => setTransferOpen(false)}
          onSuccess={async () => {
            await refreshDashboard()
          }}
        />
      )}

    </div>
  )
}

export default App
