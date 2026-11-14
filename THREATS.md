# LedgerLine — Threat Model

## 1. Purpose

This document identifies security threats relevant to LedgerLine, a FastAPI-based financial transaction and double-entry ledger application.

The purpose of this threat model is to identify important assets, understand possible attack scenarios, assess their potential impact, document implemented mitigations, and identify remaining risks and future security improvements.

LedgerLine is an educational hiring-challenge project. Its security design demonstrates application-level controls, but it is not a certified production banking platform.

---

## 2. Application Security Scope

LedgerLine includes:

- User authentication and JWT-based access.
- Role-based access control for `ADMIN`, `ACCOUNT_HOLDER`, and `AUDITOR`.
- Account and transaction ownership validation.
- Simulated deposits and withdrawals.
- Transfers between customer accounts.
- Double-entry ledger records.
- Idempotency protection.
- Concurrency protection for selected financial operations.
- Account statements and transaction history.
- Audit logging for relevant operations.
- Recipient account lookup with per-user rate limiting.

The security review focuses on authentication, authorization, financial integrity, data access, duplicate requests, concurrency, auditability, configuration exposure, and service availability.

---

## 3. Assets to Protect

| Asset                         | Security importance                                  |
| ----------------------------- | ---------------------------------------------------- |
| User credentials              | Prevent account compromise                           |
| JWT access tokens             | Prevent unauthorized API access                      |
| Customer account data         | Protect confidentiality and ownership                |
| Account balances              | Preserve financial integrity                         |
| Ledger entries                | Maintain accurate accounting records                 |
| Transaction records           | Prevent unauthorized changes                         |
| Audit logs                    | Support accountability and investigation             |
| Database credentials          | Prevent unauthorized database access                 |
| Application secrets           | Protect authentication and application configuration |
| Recipient account information | Reduce unauthorized account discovery                |

---

## 4. Threats and Mitigations

### T1 — Broken Authentication

**Threat**

An attacker may attempt to access another user's account using stolen credentials, weak passwords, or forged authentication tokens.

**Potential impact**

Unauthorized access to customer information and financial operations.

**Implemented mitigations**

- Passwords are hashed using Argon2.
- Protected endpoints require JWT authentication.
- JWT tokens include expiration timestamps.
- The application checks whether the authenticated user is active.
- Token-version-based session invalidation is included in the authentication design.

**Remaining risks**

Token theft, weak user-selected passwords, credential stuffing, and brute-force login attempts remain possible attack scenarios.

Application-wide login rate limiting, refresh-token rotation, multi-factor authentication, and additional session controls should be considered before production use.

---

### T2 — Broken Object-Level Authorization (BOLA / IDOR)

**Threat**

An authenticated user may change an account or transaction identifier in an API request to access another customer's resources.

**Potential impact**

Unauthorized disclosure of account information, statements, or transaction records.

**Implemented mitigations**

- Customer account queries are restricted by ownership.
- Transaction history and detail access apply ownership checks.
- Account statement access applies ownership checks.
- Administrative operations use role-based authorization.
- System settlement accounts are protected from ordinary customer access.
- Transfer operations validate ownership of the source account and eligibility of the destination account.
- Negative API tests verify that customers cannot access another customer's account, transaction, or statement in the tested scenarios.

**Remaining risks**

Every new endpoint that accepts a resource identifier must receive an authorization review and dedicated negative tests.

Authorization should be reviewed whenever new account, transaction, statement, recipient, or administrative functionality is introduced.

---

### T3 — Privilege Escalation

**Threat**

A customer may attempt to register as an administrator or invoke administrator-only operations.

**Potential impact**

Unauthorized account creation, account status changes, or access to other customers' data.

**Implemented mitigations**

- Public registration creates account-holder users only.
- Administrator-only endpoints use role checks.
- Customer attempts to perform restricted account-management operations are tested.
- Auditors have read-only access to accounts, statements, transaction history, and transaction details under the tested authorization rules.
- Auditors cannot create accounts, change account status, or initiate deposits, withdrawals, or transfers under the tested authorization rules.
- Automated API tests verify auditor read-only permissions and denied operations.

**Remaining risks**

Administrator account compromise and unsafe future role-management features require additional controls.

Administrator provisioning, role changes, and privileged account recovery should use a restricted and audited process.

---

### T4 — Double-Spending and Concurrent Transactions

**Threat**

Multiple simultaneous withdrawal or transfer requests may attempt to spend the same available balance.

**Potential impact**

Incorrect balances, duplicate debits, negative balances, or inconsistent financial records.

**Implemented mitigations**

- Financial operations use database transactions.
- Account balance changes and ledger records are handled together.
- Account rows are locked during financial operations.
- Account locks are acquired in a deterministic order for transfer operations.
- Database constraints help prevent invalid balances.
- A concurrency test verifies that simultaneous transfers with different idempotency keys cannot overdraw the source account.
- A separate concurrency test verifies that simultaneous requests using the same idempotency key process a transfer only once.
- A concurrent withdrawal test verifies that simultaneous withdrawals cannot overdraw the customer or settlement account in the tested scenario.
- The withdrawal test also checks that successful and rejected attempts are recorded correctly.

**Remaining risks**

The current tests cover specific concurrent transfer and withdrawal scenarios, not production-scale stress conditions.

Production workloads require additional concurrency testing, operational monitoring, and review of database locking behavior.

The test results do not establish production-scale or distributed multi-instance guarantees.

---

### T5 — Duplicate Transaction Requests

**Threat**

A client may retry a request because of a timeout or network failure, unintentionally submitting the same financial operation more than once.

An attacker may also attempt to reuse an idempotency key with a modified transaction payload.

**Potential impact**

Duplicate deposits, withdrawals, or transfers, or inconsistent transaction responses.

**Implemented mitigations**

- Idempotency keys are supported for financial transaction requests.
- Idempotency records are associated with the requesting user and endpoint.
- Request hashes help detect reuse of a key with a different payload.
- Repeated requests with the same key and payload return the existing transaction response in tested scenarios.
- Reusing a key with a different payload is rejected.
- Automated tests verify successful transfer replay.
- Automated tests verify rejected transfer replay.
- Deposit and withdrawal idempotency tests verify repeated requests.
- Concurrent duplicate-transfer testing verifies that two simultaneous requests with the same key create only one transaction, one pair of ledger entries, and one successful audit event.
- Transaction API tests validate missing, empty, and oversized idempotency keys.

**Remaining risks**

Idempotency retention, cleanup, and retry behavior need further operational testing.

Distributed deployments should verify idempotency behavior across application instances and define appropriate retention and cleanup policies.

---

### T6 — SQL Injection

**Threat**

An attacker may submit malicious input intended to manipulate database queries.

**Potential impact**

Unauthorized data access, modification, or deletion.

**Implemented mitigations**

- SQLAlchemy is used for database operations.
- Input validation is handled using Pydantic schemas.
- Database operations use structured queries rather than manually concatenated user input.

**Remaining risks**

Any future raw SQL must use parameterized queries and receive security review.

Database access should also follow the principle of least privilege.

---

### T7 — Audit Log Tampering or Insufficient Audit Coverage

**Threat**

An attacker or compromised application account may attempt to modify or delete audit records, or important operations may not generate audit events.

**Potential impact**

Reduced accountability and difficulty investigating suspicious transactions.

**Implemented mitigations**

- Relevant application operations create audit log records.
- Audit records include actor, action, resource, outcome, and timestamp information.
- Account status changes include successful and rejected operation audit events.
- Automated tests verify selected account status audit scenarios.
- Transfer tests verify successful and rejected transaction audit events.
- Concurrent duplicate-transfer testing verifies that only one successful transfer audit event is generated.

**Remaining risks**

The current application database is not an independently protected audit store.

Production deployment should use restricted write permissions, centralized logging, retention policies, and tamper detection.

Audit coverage should be expanded and verified for all relevant sensitive operations.

---

### T8 — Sensitive Configuration Exposure

**Threat**

Database credentials, JWT signing secrets, API keys, or other sensitive configuration may be exposed through source control, application logs, or deployment configuration.

**Potential impact**

Database compromise, token forgery, or unauthorized access.

**Implemented mitigations**

- Environment variables are used for application configuration.
- `.env` files are excluded through `.gitignore`.
- `.env.example` contains configuration placeholders.
- Production environment variables are configured through hosting-provider settings rather than committed source files.

**Remaining risks**

Production secrets should be stored in a dedicated secret manager and rotated when exposure is suspected.

Secret scanning, dependency scanning, and periodic repository reviews should be considered.

---

### T9 — Account Status Bypass

**Threat**

A user may attempt to operate on a frozen or closed account.

**Potential impact**

Unauthorized financial activity involving restricted accounts.

**Implemented mitigations**

- Account status is represented explicitly.
- Administrative status changes are protected.
- Financial operations validate account eligibility.
- Automated tests verify that frozen accounts are rejected in tested financial operations.
- System settlement accounts are protected from ordinary status changes.

**Remaining risks**

All financial endpoints and account lifecycle transitions must consistently enforce account status rules.

Additional tests should cover closed accounts across applicable financial operations.

---

### T10 — Denial of Service

**Threat**

An attacker may send excessive requests or expensive queries to exhaust application or database resources.

**Potential impact**

API downtime, degraded service, and increased infrastructure costs.

**Implemented mitigations**

- Transaction history endpoints support pagination.
- Database connection pooling is configured.
- Recipient account lookup has a database-backed per-user rate limit, documented under T11.

**Remaining risks**

Production deployment should add application-wide rate limiting, request-size limits, timeouts, monitoring, and infrastructure-level protections.

Authentication endpoints and other resource-intensive operations should receive particular attention.

---

### T11 — Recipient Account Enumeration and Excessive Lookup Attempts

**Threat**

An authenticated account holder may repeatedly submit account numbers to discover whether other customers have accounts on LedgerLine.

This could expose recipient information or enable account enumeration.

**Potential impact**

Unauthorized discovery of customer account information, privacy violations, and excessive database requests.

**Implemented mitigations**

- Recipient lookup is restricted to authenticated account holders.
- Only active, non-system customer accounts with eligible account holders can be returned.
- Unknown, inactive, and ineligible recipients are not returned as valid transfer recipients.
- Customers cannot use recipient lookup to select their own account.
- A database-backed rate limiter allows a maximum of 10 lookup attempts per user within a 60-second window.
- The rate limiter uses an atomic PostgreSQL upsert to enforce the limit safely during concurrent database updates.
- Excessive attempts receive HTTP 429 Too Many Requests with a `Retry-After` response header.
- Automated service and API tests verify the lookup limit, rejected attempts, and independent limits for different users.

**Remaining risks**

Concurrent recipient lookup requests have not yet received a dedicated concurrency test.

The current implementation has not been validated under production-scale or distributed deployment conditions.

Account enumeration resistance should be reviewed alongside other privacy controls before production use.

---

## 5. Security Testing Plan

The following checks are covered by the current automated test suite, as recorded in the supplied development documentation.

### Verified test scenarios

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
- [x] Concurrent transfers cannot produce an invalid negative source balance in the tested scenario.
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

### Tests to implement or expand

- [x] Frozen and closed account restrictions are tested across all applicable financial operations.
- [x] Concurrent duplicate deposits and withdrawals receive dedicated tests.
- [ ] Audit events are verified for all relevant sensitive operations.
- [ ] Additional tests verify account lifecycle and role-management security.
- [x] Concurrent recipient lookup requests are tested against rate-limit bypass.
- [ ] Production-scale concurrency and multi-instance idempotency behavior are tested.

Unchecked items are future testing work and must not be interpreted as completed controls.

---

## 6. Future Security Improvements

Before any real production financial use, consider the following improvements:

1. Expand rate limiting and brute-force protection to authentication and other sensitive endpoints.
2. Implement refresh-token rotation and token revocation.
3. Add multi-factor authentication for privileged users.
4. Use independent and tamper-resistant audit-log storage.
5. Add automated dependency and vulnerability scanning.
6. Expand security-focused API integration tests.
7. Implement centralized monitoring and alerting.
8. Perform database backup and recovery testing.
9. Arrange external penetration testing.
10. Integrate a payment provider with verified settlement callbacks, if real payments are ever required.
11. Define idempotency-record retention and cleanup policies.
12. Perform production-scale concurrency and multi-instance testing.
13. Add dedicated concurrent recipient lookup testing and rate-limit validation.
14. Review database permissions and apply least-privilege access.
15. Define incident-response and credential-rotation procedures.

---

## 7. Test Results and Evidence Limitations

The supplied project documentation records the following historical development results:

| Metric                                     | Recorded result  |
| ------------------------------------------ | ---------------- |
| Later automated backend test run           | 93 passing tests |
| Failures in that recorded run              | 0                |
| Date recorded in the original threat model | November 9, 2026 |
| Earlier reported overall code coverage     | 92%              |

The 93-test result is the later recorded test result and supersedes the earlier 76-test development result documented in `PROMPTS.md`.

The 92% coverage figure was previously reported. Coverage has not yet been remeasured after adding the later concurrency and recipient lookup security tests.

One Starlette deprecation warning was reported by the test environment during the recorded full test run.

The concurrent transfer, duplicate-transfer, and withdrawal tests verify simultaneous requests against the PostgreSQL test database. They do not establish production-scale concurrency or distributed multi-instance guarantees.

Recipient lookup rate-limit tests verify the configured per-user limit and API rejection behavior. Concurrent recipient lookup requests have not yet received a dedicated concurrency test.

These are historical test records from the supplied project documentation. They are not a claim that a fresh test run or independent security audit was performed while preparing this document.

---

## 8. Scope and Limitations

LedgerLine is an educational development project built to demonstrate secure application design, authentication, role-based authorization, financial transaction processing, and double-entry accounting concepts.

Deposits and withdrawals are simulated. The application is not connected to real banking infrastructure or payment networks.

The mitigations described in this document represent the current design and the tested scenarios where implemented.

Items identified as remaining risks, incomplete tests, or future improvements must not be treated as completed security controls.

A real banking or financial platform would require independent security assessments, regulatory and compliance reviews, operational controls, infrastructure hardening, monitoring, disaster recovery planning, and payment-provider integration.

**Security principle:** A security control is only as reliable as its implementation, verification, and ongoing operational monitoring.
