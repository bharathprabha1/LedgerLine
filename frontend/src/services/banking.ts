
import api from '../lib/api'

import type {
  Account,
  AccountStatement,
  TransactionHistory,
} from '../types/banking'

// Fetch accounts belonging to the authenticated user.
export async function getAccounts(): Promise<Account[]> {
  const response = await api.get<Account[]>('/accounts')
  return response.data
}

// Fetch paginated transaction history.
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

// Fetch a specific account statement.
export async function getAccountStatement(
  accountId: string,
): Promise<AccountStatement> {
  const response = await api.get<AccountStatement>(
    `/accounts/${encodeURIComponent(accountId)}/statement`,
  )

  return response.data
}
