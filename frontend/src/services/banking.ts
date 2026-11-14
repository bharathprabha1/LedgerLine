
import api from '../lib/api'

import type {
  Account,
  AccountStatement,
  TransactionHistory,
  DepositRequest,
  WithdrawalRequest,
  TransferRequest,
  TransactionActionResponse,
  RecipientLookup,
  RecipientSearchResult,
} from '../types/banking'

// ========================================
// ACCOUNTS
// ========================================

export async function getAccounts(): Promise<Account[]> {
  const response = await api.get<Account[]>('/accounts')
  return response.data
}

// ========================================
// RECIPIENT LOOKUP
// ========================================

// Find an eligible recipient using their exact account number.
export async function lookupRecipient(
  accountNumber: string,
): Promise<RecipientLookup> {
  const response = await api.get<RecipientLookup>(
    '/accounts/recipient-lookup',
    {
      params: {
        account_number: accountNumber.trim(),
      },
    },
  )

  return response.data
}

// Search eligible recipients by account-holder name.
export async function searchRecipients(
  query: string,
): Promise<RecipientSearchResult[]> {
  const response = await api.get<RecipientSearchResult[]>(
    '/accounts/recipient-search',
    {
      params: {
        q: query.trim(),
      },
    },
  )

  return response.data
}

// Verify a recipient selected from name-search results.
export async function lookupRecipientById(
  accountId: string,
): Promise<RecipientLookup> {
  const response = await api.get<RecipientLookup>(
    '/accounts/recipient-lookup-by-id',
    {
      params: {
        account_id: accountId,
      },
    },
  )

  return response.data
}

// ========================================
// TRANSACTION HISTORY
// ========================================

export async function getTransactions(
  limit = 20,
  offset = 0,
): Promise<TransactionHistory> {
  const response = await api.get<TransactionHistory>(
    '/transactions',
    {
      params: {
        limit,
        offset,
      },
    },
  )

  return response.data
}

// ========================================
// ACCOUNT STATEMENTS
// ========================================

export async function getAccountStatement(
  accountId: string,
): Promise<AccountStatement> {
  const response = await api.get<AccountStatement>(
    `/accounts/${encodeURIComponent(accountId)}/statement`,
  )

  return response.data
}

// ========================================
// DEPOSIT
// ========================================

export async function depositMoney(
  request: DepositRequest,
  idempotencyKey: string,
): Promise<TransactionActionResponse> {
  const response = await api.post<TransactionActionResponse>(
    '/transactions/deposit',
    request,
    {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    },
  )

  return response.data
}

// ========================================
// WITHDRAWAL
// ========================================

export async function withdrawMoney(
  request: WithdrawalRequest,
  idempotencyKey: string,
): Promise<TransactionActionResponse> {
  const response = await api.post<TransactionActionResponse>(
    '/transactions/withdrawal',
    request,
    {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    },
  )

  return response.data
}

// ========================================
// TRANSFER
// ========================================

export async function transferMoney(
  request: TransferRequest,
  idempotencyKey: string,
): Promise<TransactionActionResponse> {
  const response = await api.post<TransactionActionResponse>(
    '/transactions/transfer',
    request,
    {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    },
  )

  return response.data
}
