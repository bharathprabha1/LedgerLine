# LedgerLine - Threat Model

## 1. Purpose

This document identifies security threats relevant to LedgerLine, a FastAPI-based banking and double-entry ledger application.

The goal is to identify possible attacks, understand their impact, and document the controls implemented or planned to reduce risk.

## 2. Assets to Protect

| Asset | Security importance |
|---|---|
| User credentials | Prevent account compromise |
| JWT access tokens | Prevent unauthorized API access |
| Customer account data | Protect confidentiality and ownership |
| Account balances | Preserve financial integrity |
| Ledger entries | Maintain accurate accounting records |
| Transaction records | Prevent unauthorized changes |
| Audit logs | Support accountability and investigation |
| Database credentials | Prevent unauthorized database access |

## 3. Threats and Mitigations

### T1 - Broken Authentication

**Threat:** An attacker may attempt to access another user's account using stolen credentials or forged authentication tokens.

**Potential impact:** Unauthorized access to customer information and financial operations.

**Mitigations:**

- Passwords are hashed using Argon2.
- Protected endpoints require JWT authentication.
- JWT tokens include expiration timestamps.
- The application checks whether the authenticated user is active.

**Remaining risk:** Token theft and weak user-selected passwords remain possible. Rate limiting, token revocation, and stronger session controls should be considered before production use.

### T2 - Broken Object-Level Authorization (BOLA / IDOR)

**Threat:** An authenticated user may change an account or transaction ID in an API request to access another customer's resources.

**Potential impact:** Unauthorized disclosure of account information or transaction records.

**Mitigations:**

- Customer account queries are restricted by ownership.
- Transaction history and detail access apply ownership checks.
- Administrative operations use role-based authorization.
- System settlement accounts are protected from ordinary customer access.
- Negative API tests verify that customers cannot access another customer's account, transaction, or statement.
- Transfer operations validate ownership of the source account and eligibility of the destination account.

**Remaining risk:** Every new endpoint that accepts a resource identifier must receive an authorization review and dedicated negative tests.

### T3 - Privilege Escalation

**Threat:** A customer may attempt to register as an administrator or invoke administrator-only operations.

**Potential impact:** Unauthorized account creation, account status changes, or access to other customers' data.

**Mitigations:**

- Public registration creates account-holder users only.
- Administrator-only endpoints use role checks.
- Customer attempts to perform restricted account-management operations are tested.
- Auditors have read-only access to accounts, statements, transaction history, and transaction details.
- Auditors cannot create accounts, change account status, or initiate deposits, withdrawals, or transfers.
- Automated API tests verify the auditor's read-only permissions and denied operations.

**Remaining risk:** Administrator account compromise and unsafe future role-management features require additional controls. Administrator provisioning and role changes should use a restricted, audited process.

### T4 - Double-Spending and Concurrent Transactions

**Threat:** Multiple simultaneous withdrawal or transfer requests may attempt to spend the same available balance.

**Potential impact:** Incorrect balances, duplicate debits, or financial inconsistencies.

**Mitigations:**

- Financial operations use database transactions.
- Account balance changes and ledger records are handled together.
- Account rows are locked during financial operations.
- Account locks are acquired in a deterministic order for transfer operations.
- Database constraints help prevent invalid balances.
- A concurrency test verifies that simultaneous transfers with different idempotency keys cannot overdraw the source account.
- A separate concurrency test verifies that simultaneous requests using the same idempotency key process a transfer only once.
- A concurrent withdrawal test verifies that simultaneous withdrawals cannot overdraw the customer or settlement account, and that the successful and rejected attempts are recorded correctly.

**Remaining risk:** The current tests cover specific concurrent transfer and withdrawal scenarios, not production-scale stress conditions. Production workloads require additional concurrency testing, operational monitoring, and review of database locking behavior.

### T5 - Duplicate Transaction Requests

**Threat:** A client may retry a request because of a timeout or network failure, unintentionally submitting the same financial operation more than once.

An attacker may also attempt to reuse an idempotency key with a modified transaction payload.

**Potential impact:** Duplicate deposits, withdrawals, or transfers, or inconsistent transaction responses.

**Mitigations:**

- Idempotency keys are supported for financial transaction requests.
- Idempotency records are associated with the requesting user and endpoint.
- Request hashes help detect reuse of a key with a different payload.
- Repeated requests with the same key and payload return the existing transaction response.
- Reusing a key with a different payload is rejected.
- Automated tests verify successful transfer replay.
- Automated tests verify rejected transfer replay.
- Deposit and withdrawal idempotency tests verify repeated requests.
- Concurrent duplicate-transfer testing verifies that two simultaneous requests with the same key create only one transaction, one pair of ledger entries, and one successful audit event.
- Transaction API tests validate missing, empty, and oversized idempotency keys.

**Remaining risk:** Idempotency retention, cleanup, and retry behavior need further operational testing. Distributed deployments should also verify idempotency behavior across application instances.

### T6 - SQL Injection

**Threat:** An attacker may submit malicious input intended to manipulate database queries.

**Potential impact:** Unauthorized data access, modification, or deletion.

**Mitigations:**

- SQLAlchemy is used for database operations.
- Input validation is handled using Pydantic schemas.
- Database operations use structured queries rather than manually concatenated user input.

**Remaining risk:** Any future raw SQL must use parameterized queries and receive security review.

### T7 - Audit Log Tampering or Insufficient Audit Coverage

**Threat:** An attacker or compromised application account may attempt to modify or delete audit records, or important operations may not generate audit events.

**Potential impact:** Reduced accountability and difficulty investigating suspicious transactions.

**Mitigations:**

- Relevant application operations create audit log records.
- Audit records include actor, action, resource, outcome, and timestamp information.
- Account status changes include successful and rejected operation audit events.
- Automated tests verify selected account status audit scenarios.
- Transfer tests verify successful and rejected transaction audit events.
- Concurrent duplicate-transfer testing verifies that only one successful transfer audit event is generated.

**Remaining risk:** The current application database is not an independently protected audit store. Production deployment should use restricted write permissions, centralized logging, retention policies, and tamper detection.

### T8 - Sensitive Configuration Exposure

**Threat:** Database credentials, JWT signing secrets, or other sensitive configuration may be exposed through source control or logs.

**Potential impact:** Database compromise, token forgery, or unauthorized access.

**Mitigations:**

- Environment variables are used for application configuration.
- `.env` files are excluded through `.gitignore`.
- `.env.example` contains configuration placeholders.

**Remaining risk:** Production secrets should be stored in a dedicated secret manager and rotated when exposure is suspected.

### T9 - Account Status Bypass

**Threat:** A user may attempt to operate on a frozen or closed account.

**Potential impact:** Unauthorized financial activity involving restricted accounts.

**Mitigations:**

- Account status is represented explicitly.
- Administrative status changes are protected.
- Financial operations validate account eligibility.
- Automated tests verify that frozen accounts are rejected in tested financial operations.
- System settlement accounts are protected from ordinary status changes.

**Remaining risk:** All financial endpoints and account lifecycle transitions must consistently enforce account status rules. Additional tests should cover closed accounts across applicable financial operations.

### T10 - Denial of Service

**Threat:** An attacker may send excessive requests or expensive queries to exhaust application or database resources.

**Potential impact:** API downtime and degraded service.

**Mitigations:**

- Transaction history endpoints support pagination.
- Database connection pooling is configured.
- Recipient account lookup has a database-backed per-user rate limit, documented separately under T11.

**Remaining risk:** Production deployment should add application-wide rate limiting, request-size limits, timeouts, monitoring, and infrastructure-level protections.

### T11 - Recipient Account Enumeration and Excessive Lookup Attempts

**Threat:** An authenticated account holder may repeatedly submit account numbers to discover whether other customers have accounts on LedgerLine. This could expose recipient information or enable account enumeration.

**Potential impact:** Unauthorized discovery of customer account information, privacy violations, and excessive database requests.

**Mitigations:**

- Recipient lookup is restricted to authenticated account holders.
- Only active, non-system customer accounts with eligible account holders can be returned.
- Unknown, inactive, and ineligible recipients are not returned as valid transfer recipients.
- Customers cannot use recipient lookup to select their own account.
- A database-backed rate limiter allows a maximum of 10 lookup attempts per user within a 60-second window.
- The rate limiter uses an atomic PostgreSQL upsert to enforce the limit safely during concurrent database updates.
- Excessive attempts receive HTTP 429 Too Many Requests with a Retry-After response header.
- Automated service and API tests verify the lookup limit, rejected attempts, and independent limits for different users.

**Remaining risk:** Concurrent recipient lookup requests have not yet received a dedicated concurrency test. The current implementation has not been validated under production-scale or distributed deployment conditions. Account enumeration resistance should be reviewed alongside other privacy controls before production use.

## 4. Security Testing Plan

The following checks are covered by the current automated test suite:

- [x] Unauthenticated users cannot access protected endpoints.
- [x] Account holders cannot access another customer's account.
- [x] Account holders cannot access another customer's transactions.
- [x] Customers cannot perform administrator-only operations.
- [x] Auditors can view accounts, transaction history, transaction details, and customer account statements.
- [x] Auditors cannot create accounts or change account status.
- [x] Auditors cannot initiate deposits, withdrawals, or transfers.
- [x] Inactive users cannot use protected endpoints.
- [x] Repeated idempotency keys do not create duplicate transactions.
- [x] Reusing an idempotency key with a different payload is rejected.
- [x] Rejected transaction requests are replayed consistently in tested scenarios.
- [x] Concurrent transfers cannot produce an invalid negative source balance.
- [x] Concurrent duplicate transfer requests create only one financial transaction.
- [x] Concurrent duplicate transfer requests create only one pair of ledger entries.
- [x] Concurrent duplicate transfer requests create only one successful audit event.
- [x] Selected account status changes generate the expected audit events.
- [x] Failed transfer requests are verified to leave no partial ledger entries in the tested scenario.
- [x] Concurrent withdrawals cannot overdraw the customer or settlement account in the tested scenario.
- [x] Recipient lookup returns eligible recipients in the tested scenario.
- [x] Recipient lookup rejects unknown and invalid account-number attempts in the tested scenarios.
- [x] Recipient lookup rate limiting rejects excessive attempts with HTTP 429.
- [x] Recipient lookup limits are independent for different users.
- [x] Recipient lookup rate-limit service tests verify the 10-attempt, 60-second limit.

Additional checks to implement or expand:

- [ ] Frozen and closed account restrictions are tested across all applicable financial operations.
- [ ] Concurrent duplicate deposits and withdrawals receive dedicated tests.
- [ ] Audit events are verified for all relevant sensitive operations.
- [ ] Additional tests verify account lifecycle and role-management security.
- [ ] Concurrent recipient lookup requests are tested against rate-limit bypass.
- [ ] Production-scale concurrency and multi-instance idempotency behavior are tested.

## 5. Future Security Improvements

Before production use, consider:

1. Expand rate limiting and brute-force protection to authentication and other sensitive endpoints.
2. Refresh-token rotation and token revocation.
3. Multi-factor authentication for privileged users.
4. Independent and tamper-resistant audit-log storage.
5. Automated dependency and vulnerability scanning.
6. Expanded security-focused API integration tests.
7. Centralized monitoring and alerting.
8. Database backup and recovery testing.
9. External penetration testing.
10. Payment-provider integration with verified settlement callbacks.
11. Idempotency-record retention and cleanup policies.
12. Production-scale concurrency and multi-instance testing.
13. Dedicated concurrent recipient lookup testing and rate-limit validation.

## 6. Scope and Limitations

LedgerLine is an educational development project. Deposits are simulated, and the application is not connected to real banking infrastructure or payment networks.

The mitigations listed above describe the current design where implemented. Items identified as remaining risks or future improvements must not be treated as completed security controls.

The current automated backend test suite contains 93 passing tests as of November 9, 2026. The latest full test run completed with no failures. One Starlette deprecation warning was reported by the test environment.

Overall code coverage was previously reported as 92%. Coverage has not yet been remeasured after adding the latest concurrency and recipient lookup security tests.

The concurrent transfer, duplicate-transfer, and withdrawal tests verify simultaneous requests against the PostgreSQL test database. They do not establish production-scale concurrency or distributed multi-instance guarantees.

Recipient lookup rate-limit tests verify the configured per-user limit and API rejection behavior. Concurrent recipient lookup requests have not yet received a dedicated concurrency test.

A production banking platform would require independent security, compliance, infrastructure, and operational reviews.
