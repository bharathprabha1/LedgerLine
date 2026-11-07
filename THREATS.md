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



**Remaining risk:** Every new endpoint that accepts a resource identifier must receive an authorization review and dedicated negative tests.



### T3 - Privilege Escalation



**Threat:** A customer may attempt to register as an administrator or invoke administrator-only operations.



**Potential impact:** Unauthorized account creation, account status changes, or access to other customers' data.



**Mitigations:**

- Public registration creates account-holder users only.

- Administrator-only endpoints use role checks.

- Initial administrator creation uses a separate bootstrap script.



**Remaining risk:** Administrator account compromise and unsafe future role-management features require additional controls.



### T4 - Double-Spending and Concurrent Transactions



**Threat:** Multiple simultaneous withdrawal or transfer requests may attempt to spend the same available balance.



**Potential impact:** Incorrect balances, duplicate debits, or financial inconsistencies.



**Mitigations:**

- Financial operations use database transactions.

- Account balance changes and ledger records are handled together.

- Database constraints help prevent invalid balances.

- Concurrency scenarios are included in the test suite.



**Remaining risk:** Production workloads require additional concurrency testing, operational monitoring, and review of database locking behavior.



### T5 - Duplicate Transaction Requests



**Threat:** A client may retry a request because of a timeout or network failure, unintentionally submitting the same financial operation more than once.



**Potential impact:** Duplicate deposits, withdrawals, or transfers.



**Mitigations:**

- Idempotency keys are supported for transaction requests.

- Idempotency records are associated with the requesting user and endpoint.

- Request hashes help detect reuse of a key with a different payload.



**Remaining risk:** Idempotency retention, cleanup, and retry behavior need further operational testing.



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



**Remaining risk:** All future financial endpoints must consistently enforce account status rules.



### T10 - Denial of Service



**Threat:** An attacker may send excessive requests or expensive queries to exhaust application or database resources.



**Potential impact:** API downtime and degraded service.



**Mitigations:**

- Transaction history endpoints support pagination.

- Database connection pooling is configured.



**Remaining risk:** Production deployment should add rate limiting, request-size limits, timeouts, monitoring, and infrastructure-level protections.



## 4. Security Testing Plan



The following checks should be maintained as the project evolves:



- \[ ] Unauthenticated users cannot access protected endpoints.

- \[ ] Account holders cannot access another customer's account.

- \[ ] Account holders cannot access another customer's transactions.

- \[ ] Customers cannot perform administrator-only operations.

- \[ ] Inactive users cannot use protected endpoints.

- \[ ] Frozen or closed accounts cannot perform prohibited transactions.

- \[ ] Repeated idempotency keys do not create duplicate transactions.

- \[ ] Reusing an idempotency key with a different payload is rejected.

- \[ ] Concurrent withdrawals cannot produce an invalid negative balance.

- \[ ] Failed transactions do not leave partial ledger entries.

- \[ ] Audit events are recorded for relevant sensitive operations.



## 5. Future Security Improvements



Before production use, consider:



1\. Rate limiting and brute-force protection.

2\. Refresh-token rotation and token revocation.

3\. Multi-factor authentication for privileged users.

4\. Independent and tamper-resistant audit-log storage.

5\. Automated dependency and vulnerability scanning.

6\. Security-focused API integration tests.

7\. Centralized monitoring and alerting.

8\. Database backup and recovery testing.

9\. External penetration testing.

10\. Payment-provider integration with verified settlement callbacks.



## 6. Scope and Limitations



LedgerLine is an educational development project. Deposits are simulated, and the application is not connected to real banking infrastructure or payment networks.



The mitigations listed above describe the current design where implemented. Items identified as remaining risks or future improvements must not be treated as completed security controls.



A production banking platform would require independent security, compliance, infrastructure, and operational reviews.


