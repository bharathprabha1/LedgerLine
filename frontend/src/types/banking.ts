
export type AccountStatus = 'ACTIVE' | 'FROZEN' | 'CLOSED'

export type TransactionType =
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'TRANSFER'

export type TransactionStatus =
  | 'PENDING'
  | 'POSTED'
  | 'REJECTED'

export interface Account {
  id: string
  account_number: string
  owner_id: string
  balance_paise: number
  currency: string
  status: AccountStatus
  created_at: string
}

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

export interface TransactionHistory {
  items: Transaction[]
  total: number
  limit: number
  offset: number
}

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

export interface AccountStatement {
  account_id: string
  account_number: string
  currency: string
  opening_balance_paise: number
  closing_balance_paise: number
  items: StatementItem[]
}
