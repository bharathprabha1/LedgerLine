# LedgerLine — AI Development Prompt Log

## 1. Purpose

This document records how AI assistance was used during the development of LedgerLine.

It documents the development tasks discussed with the AI assistant, the suggestions received, issues encountered, developer decisions, verification activities, and related Git commits.

AI assistance was used as a development support tool. The developer remained responsible for reviewing suggestions, integrating changes, investigating errors, testing application behavior, and deciding which changes to retain.

**AI assistant used:** ChatGPT

**Project:** LedgerLine — Secure Money Movement with a Verifiable Ledger

**Repository:** https://github.com/bharathprabha1/LedgerLine

---

## 2. Development Log

### Entry 1 — Transaction History and Detail APIs

**Date:** November 7, 2026

**Prompt / Task**

Help implement transaction history and transaction detail API endpoints while preserving the existing deposit, withdrawal, and transfer functionality.

**AI assistance**

Suggested API routes, database queries, account ownership checks, pagination, and response schemas for retrieving transaction records.

**Issue identified**

An initial transaction-detail request returned an error because the supplied identifier was not a transaction ID. An expired or missing JWT also caused authentication failures during testing.

**Developer verification and correction**

- Checked that the correct transaction identifier was supplied.
- Authenticated again when the JWT was expired or missing.
- Distinguished authentication failures from missing transaction records.
- Reviewed the API responses and transaction retrieval behavior.

**Related commits**

- [Initial implementation](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c)
- [Comprehensive API and statement tests](https://github.com/bharathprabha1/LedgerLine/commit/1e58310)

---

### Entry 2 — Account Statements and Ledger Access Control

**Date:** November 7, 2026

**Prompt / Task**

Implement an account statement endpoint that displays debit and credit entries while restricting customer access to their own accounts.

**AI assistance**

Suggested a statement service, response schema, ledger-entry retrieval, and account ownership filtering.

**Issue identified**

The implementation needed to distinguish customer access from administrator and auditor access. Opening-balance assumptions also needed to be documented.

**Developer verification and correction**

- Reviewed account ownership rules.
- Examined the relationship between ledger entries and account balances.
- Checked that statement entries correspond to the account's recorded ledger activity.
- Documented the statement calculation assumption.

The current statement calculation assumes accounts begin with a zero balance and all subsequent balance changes are represented in the ledger.

**Related commits**

- [Initial implementation](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c)
- [Comprehensive API and statement tests](https://github.com/bharathprabha1/LedgerLine/commit/1e58310)

---

### Entry 3 — Role-Based Authorization for Financial Operations

**Date:** November 7, 2026

**Prompt / Task**

Investigate why an administrator received a forbidden response when attempting to initiate a customer deposit.

**AI assistance**

Explained the account-holder-only restriction and the need to use an authorized account-holder identity for the operation.

**Issue identified**

The administrator role was not permitted to initiate that customer financial operation. Testing with the wrong role produced HTTP 403.

**Developer verification and correction**

- Identified the role associated with the authenticated request.
- Used the intended account-holder test identity for the operation.
- Retained the authorization restriction instead of weakening the role checks.
- Reviewed related API security tests.

**Security area:** Role-Based Access Control (RBAC).

**Related commits**

- [Initial implementation](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c)
- [API security tests](https://github.com/bharathprabha1/LedgerLine/commit/b4e2d64)
- [Auditor and account status security tests](https://github.com/bharathprabha1/LedgerLine/commit/ec8b38d)

---

### Entry 4 — Account Ownership and Object-Level Authorization

**Date:** November 7, 2026

**Prompt / Task**

Review how account and transaction identifiers should be checked to prevent customers from accessing another customer's resources.

**AI assistance**

Explained object-level authorization and recommended checking account ownership before returning account or transaction information.

**Issue identified**

A valid resource identifier alone must not be treated as proof of permission to access that resource.

**Developer verification and correction**

- Reviewed ownership checks for account and transaction retrieval.
- Used negative API tests to verify unauthorized access behavior.
- Verified that customers cannot access another customer's account, transaction, or statement in the tested scenarios.
- Reviewed administrator and auditor access paths separately.

**Security area:** Broken Object-Level Authorization (BOLA) / Insecure Direct Object Reference (IDOR).

**Related commits**

- [Initial implementation](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c)
- [API security tests](https://github.com/bharathprabha1/LedgerLine/commit/b4e2d64)
- [Auditor and account status security tests](https://github.com/bharathprabha1/LedgerLine/commit/ec8b38d)
- [Comprehensive API and statement tests](https://github.com/bharathprabha1/LedgerLine/commit/1e58310)

---

### Entry 5 — Idempotency and Duplicate Transaction Requests

**Date:** November 7, 2026

**Prompt / Task**

Investigate an idempotency-key conflict that occurred when a transaction request was retried with a different payload.

**AI assistance**

Explained that an idempotency key should identify a particular operation and that a request hash can detect reuse with different request data.

**Issue identified**

Reusing the same key with a different payload caused a conflict rather than creating a new transaction.

**Developer verification and correction**

- Used a fresh idempotency key for a new transaction request.
- Retained the conflict behavior for mismatched payloads.
- Reviewed replay behavior for repeated requests.
- Checked API validation for missing, empty, and oversized idempotency keys.
- Reviewed tests for duplicate transfers, deposits, and withdrawals.

**Security and integrity area:** Idempotency and duplicate transaction prevention.

**Related commits**

- [Initial implementation](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c)
- [Comprehensive API and statement tests](https://github.com/bharathprabha1/LedgerLine/commit/1e58310)

---

## 3. Developer Reflection

AI assistance was useful throughout LedgerLine development for:

- Understanding unfamiliar implementation details.
- Generating possible API and service-layer approaches.
- Explaining authentication and authorization errors.
- Identifying financial integrity and security considerations.
- Suggesting test scenarios and edge cases.
- Reviewing implementation decisions and debugging problems.

However, generated code and explanations were not accepted blindly.

The developer reviewed implementation suggestions, investigated errors, checked API responses, examined database records, and used automated tests and manual application checks to validate behavior.

When an issue resulted from an incorrect identifier, expired authentication token, or unsuitable user role, the developer investigated the cause rather than weakening the application's security rules.

The developer also maintained the project documentation, reviewed Git changes, and committed implementation and test updates to the repository.

---

## 4. Testing and Verification Record

The development test results were recorded at different stages of the project.

| Development record | Reported result |
|---|---|
| Earlier test run recorded in this development log | 76 passing tests |
| Later test run recorded in the threat model on November 9, 2026 | 93 passing tests, 0 failures |
| Earlier reported overall code coverage | 92% |

The 76-test result is a historical development result. The later 93-test result supersedes it as the latest result recorded in the supplied project documentation.

The 92% coverage figure was previously reported. It was not remeasured after the later concurrency and recipient lookup tests were added.

These figures are historical records, not a claim that a fresh test run was executed while preparing this document.

---

## 5. Commit Traceability

The following commit references were recorded during development:

| Commit | Development purpose |
|---|---|
| [fe2e87c](https://github.com/bharathprabha1/LedgerLine/commit/fe2e87c) | Initial implementation |
| [b4e2d64](https://github.com/bharathprabha1/LedgerLine/commit/b4e2d64) | API security tests |
| [ec8b38d](https://github.com/bharathprabha1/LedgerLine/commit/ec8b38d) | Auditor and account status security tests |
| [1e58310](https://github.com/bharathprabha1/LedgerLine/commit/1e58310) | Comprehensive API and statement tests |

These references identify the commits associated with the development work described in the entries above.

---

## 6. AI Assistance Declaration

AI was used as a supporting development tool for problem analysis, implementation suggestions, debugging explanations, and test planning.

The project was not treated as automatically generated or independently verified AI output. The developer was responsible for reviewing the code, making implementation decisions, testing behavior, correcting issues, and maintaining the repository.

**Development principle:** Use AI to accelerate problem-solving, but rely on code review, testing, and verification to determine whether an implementation is correct.