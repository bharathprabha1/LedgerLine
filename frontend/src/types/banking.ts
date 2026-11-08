
export type AccountStatus = 'ACTIVE' | 'FROZEN' | 'CLOSED'

export type TransactionType =
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'TRANSFER'

export type TransactionStatus =
  | 'PENDING'
  | 'POSTED'
  | 'REJECTED'

// Account information.
export interface Account {
  id: string
  account_number: string
  owner_id: string
  balance_paise: number
  currency: string
  status: AccountStatus
  is_system: boolean
  created_at: string
}

// Verified recipient information returned by the backend.
export interface RecipientLookup {
  id: string
  account_number: string
  holder_name: string
  currency: string
}

// Transaction information.
export interface Transaction {
  id: string
  reference: string
  transaction_type: TransactionType
  status: TransactionStatus
  amount_paise: number
  source_account_id: string | null
  destination_account_id: string | null
  initiated_by: string
  description: string | null
  created_at: string
}

// Paginated transaction history.
export interface TransactionHistory {
  items: Transaction[]
  total: number
  limit: number
  offset: number
}

// Individual statement transaction.
export interface StatementItem {
  transaction_id: string
  reference: string
  transaction_type: TransactionType
  status: TransactionStatus
  description: string | null
  created_at: string
  debit_paise: number
  credit_paise: number
  attempted_debit_paise: number
  attempted_credit_paise: number
  running_balance_paise: number
}

// Account statement.
export interface AccountStatement {
  account_id: string
  account_number: string
  currency: string
  opening_balance_paise: number
  closing_balance_paise: number
  items: StatementItem[]
}

// Deposit request.
export interface DepositRequest {
  account_id: string
  amount_paise: number
  description: string
}

// Withdrawal request.
export interface WithdrawalRequest {
  account_id: string
  amount_paise: number
  description: string
}

// Transfer request.
export interface TransferRequest {
  source_account_id: string
  destination_account_id: string
  amount_paise: number
  description: string
}

// Response returned by transaction operations.
export interface TransactionActionResponse {
  id: string
  reference: string
  transaction_type: TransactionType
  status: TransactionStatus
  amount_paise: number
  initiated_by: string
  description: string | null
  created_at: string
}
