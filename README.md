# LedgerLine

### Secure money movement with a ledger you can prove.

LedgerLine is a full-stack financial transaction management application built to demonstrate secure money movement, reliable transaction processing, and verifiable double-entry accounting.

The application combines a React and TypeScript frontend with a Python FastAPI backend and PostgreSQL database. It demonstrates authentication, role-based authorization, account management, simulated deposits and withdrawals, account-to-account transfers, transaction history, double-entry ledger entries, idempotency, concurrency protection, account statements, and audit logging.

**Project status:** Deployed and available for evaluation.

> **Important:** LedgerLine is an educational hiring-challenge project. Deposits and withdrawals are simulated. It is not connected to a real bank, payment gateway, or live payment network and must not be used as a production banking service.

---

## Live Application

| Component | URL |
|---|---|
| **Live Frontend** | https://ledgerline-ten-orpin.vercel.app |
| **Backend API** | https://ledgerline-n9fl.onrender.com |
| **Swagger API Documentation** | https://ledgerline-n9fl.onrender.com/docs |
| **OpenAPI Schema** | https://ledgerline-n9fl.onrender.com/openapi.json |
| **GitHub Repository** | https://github.com/bharathprabha1/LedgerLine |

The frontend is deployed on Vercel, the backend on Render, and the application database uses Neon PostgreSQL.

---

## Key Features

### 1. Authentication and Authorization

- User registration and login.
- Secure password hashing using Argon2.
- JWT-based authentication.
- Role-based access control.
- Support for `ADMIN`, `ACCOUNT_HOLDER`, and `AUDITOR` roles.
- Active-user validation for protected requests.
- Protected administrative operations.
- Account ownership validation.
- Token-version-based session invalidation.

### 2. Account Management

- Administrator-controlled customer account creation.
- Account information retrieval.
- Account listing based on user permissions.
- Customer account ownership restrictions.
- Account status management.
- Protected system settlement account.
- Account status validation before financial operations.

### 3. Financial Transactions

- Simulated deposits.
- Withdrawals.
- Transfers between customer accounts.
- Unique transaction references.
- Transaction status tracking.
- Transaction history with pagination.
- Transaction detail retrieval.
- Account statements with debit and credit entries.
- Monetary amounts represented in integer paise.

### 4. Double-Entry Ledger

- Corresponding debit and credit ledger entries.
- Balanced financial transaction records.
- Ledger-based account activity.
- Transactional database operations.
- Verifiable accounting records.

### 5. Financial Integrity and Security

- Idempotency protection against duplicate requests.
- Concurrency protection for simultaneous financial operations.
- Database constraints for financial data integrity.
- Balance validation and overdraft prevention.
- Role-based and object-level authorization.
- Audit logging for relevant sensitive operations.
- Automated authentication, authorization, transaction, and concurrency tests.

---

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend Framework | FastAPI |
| Programming Language | Python 3.13 |
| Database | PostgreSQL |
| Database Hosting | Neon PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Data Validation | Pydantic |
| Authentication | JWT |
| Password Hashing | Argon2 |
| Database Driver | Psycopg 3 |
| Backend Testing | Pytest, Pytest-Cov |
| API Documentation | Swagger UI / OpenAPI |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Version Control | Git and GitHub |

---

## Demo Accounts and Evaluator Access

LedgerLine supports three application roles.

The following account information identifies the configured accounts. **Passwords are intentionally excluded from this public README.**

| Account | Display Name | Registered Email | Role |
|---|---|---|---|
| Administrator | ADMINISTRATOR | `admin@gmail.com` | `ADMIN` |
| Auditor | AUDITOR* | `auditor@gmail.com` | `AUDITOR` |
| Account Holder | Kranthi Kumar Naik | `kranthikumarnaik@gmail.com` | `ACCOUNT_HOLDER` |

\*The auditor account's original display name was entered as `ADUITOR`. The assigned role is `AUDITOR`; the display name and authorization role are separate.

### Evaluator access

For evaluation, use the dedicated **AUDITOR** account where possible. Its permissions are intended for reviewing permitted financial information without granting administrative or transaction-creation privileges.

Demo passwords are shared separately through a private channel with authorized evaluators. They are not stored in this public repository.

**Security recommendations:**
- Never publish passwords, JWT tokens, database URLs, API keys, `.env` files, or application secrets.
- Do not share the administrator password with evaluators.
- Use temporary evaluation credentials and rotate or disable them after evaluation.
- Use a dedicated test account for any transaction demonstrations.

### Role Overview

| Role | Permissions |
|---|---|
| `ADMIN` | Administrative operations, including customer account creation and permitted account management. |
| `ACCOUNT_HOLDER` | Access to owned accounts and permitted financial operations. |
| `AUDITOR` | Read and review access to financial information permitted by backend authorization rules. |

### Auditor Authorization — Production Checks

The following checks were performed against the deployed API while authenticated as the auditor role:

| Request | Observed HTTP Status | Result |
|---|---:|---|
| `GET /api/v1/accounts` | 200 | Verified |
| `GET /api/v1/transactions` | 200 | Verified |
| `POST /api/v1/transactions/deposit` | 403 | Correctly blocked |
| `POST /api/v1/transactions/transfer` | 403 | Correctly blocked |

The API returned `403 Forbidden` for deposit and transfer attempts made with the auditor role.

Account creation and withdrawal restrictions require separate verification and are not claimed as verified here.

---

## Application Architecture

```text
                  ┌─────────────────────────┐
                  │       User / Browser    │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │   React + TypeScript    │
                  │      Vite Frontend      │
                  │       (Vercel)          │
                  └────────────┬────────────┘
                               │
                         REST API / HTTPS
                               │
                               ▼
                  ┌─────────────────────────┐
                  │       FastAPI           │
                  │    Backend (Render)     │
                  ├─────────────────────────┤
                  │ Authentication / JWT    │
                  │ Role-Based Authorization│
                  │ Account Management      │
                  │ Transaction Processing  │
                  │ Ledger and Audit Logic  │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │      PostgreSQL         │
                  │    Database (Neon)      │
                  ├─────────────────────────┤
                  │ Users                   │
                  │ Accounts                │
                  │ Transactions            │
                  │ Ledger Entries          │
                  │ Audit Records           │
                  └─────────────────────────┘
```

The backend handles authentication, authorization, validation, transaction processing, and database operations. The frontend communicates with the backend through REST API endpoints.

---

## Project Structure

```text
LedgerLine/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── accounts.py
│   │   │       └── transactions.py
│   │   │
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── bootstrap_admin.py
│   └── initialize_system_accounts.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── .gitignore
├── README.md
├── PROMPTS.md
└── THREATS.md
```

---

## Prerequisites

Install the following software before running the project locally:

- Python 3.13
- Node.js and npm
- PostgreSQL or a PostgreSQL connection string
- Git
- PowerShell on Windows, or an equivalent terminal

---

## Local Installation and Setup

### 1. Clone the repository

```powershell
git clone https://github.com/bharathprabha1/LedgerLine.git
cd LedgerLine
```

### 2. Configure the backend

```powershell
cd backend

py -3.13 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Copy-Item .env.example .env

notepad .env
```

Configure the `.env` file with:

- Your PostgreSQL database connection string.
- A strong, randomly generated application secret.
- The required backend configuration values defined in `.env.example`.

Do not use production credentials in your local development environment.

Ensure PostgreSQL is running and the configured database exists.

### 3. Apply database migrations

From the `backend` directory:

```powershell
$env:PYTHONPATH = (Get-Location).Path

alembic upgrade head

python initialize_system_accounts.py
```

For a fresh local database, create the initial administrator interactively:

```powershell
python bootstrap_admin.py
```

### 4. Start the backend

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 5. Configure the frontend

Open a second terminal from the repository root:

```powershell
cd frontend

npm install
```

Configure the frontend API base URL:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

If required, create a `frontend/.env` file and add the configuration above.

### 6. Start the frontend

```powershell
npm run dev
```

Open the local URL printed by Vite in your terminal.

### 7. Production Environment Configuration

The deployed frontend and backend use separate hosting services.

For a new deployment:

- Configure the frontend API base URL to point to the backend API.
- Configure the backend CORS allowlist to include the frontend origin.
- Set database credentials and application secrets through the hosting provider's environment-variable settings.
- Never commit production environment variables or secrets to GitHub.

---

## API Documentation

All API endpoints use the `/api/v1` prefix.

The complete interactive API documentation is available at:

**https://ledgerline-n9fl.onrender.com/docs**

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register an account holder |
| POST | `/api/v1/auth/login` | Authenticate a user |
| GET | `/api/v1/auth/me` | Retrieve the current user |

### Account Management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/accounts` | Create a customer account (administrator permission required) |
| GET | `/api/v1/accounts` | List accessible accounts |
| GET | `/api/v1/accounts/{account_id}` | Retrieve account details |
| PATCH | `/api/v1/accounts/{account_id}/status` | Update account status |
| GET | `/api/v1/accounts/{account_id}/statement` | Retrieve an account statement |

### Financial Transactions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/transactions/deposit` | Simulate a deposit |
| POST | `/api/v1/transactions/withdrawal` | Withdraw funds |
| POST | `/api/v1/transactions/transfer` | Transfer funds between accounts |
| GET | `/api/v1/transactions` | Retrieve transaction history |
| GET | `/api/v1/transactions/{transaction_id}` | Retrieve transaction details |

Use Swagger UI to inspect the current request schemas, authentication requirements, and available operations.

---

## Idempotency and Duplicate Transaction Protection

Transaction creation endpoints require an `Idempotency-Key` HTTP header.

This key helps prevent duplicate processing when a client retries a request because of a timeout, network interruption, or uncertain response.

Reusing the same key with a different request payload is rejected.

Example:

```http
Idempotency-Key: unique-operation-123
```

This helps ensure that retrying the same operation does not accidentally create duplicate financial transactions.

---

## Double-Entry Accounting Approach

LedgerLine uses a double-entry accounting approach. Each posted financial transaction creates corresponding debit and credit ledger entries.

### Deposit

- Debit the system settlement account.
- Credit the customer account.

### Withdrawal

- Debit the customer account.
- Credit the system settlement account.

### Transfer

- Debit the source account.
- Credit the destination account.

### Monetary Precision

Transaction amounts are represented in integer paise instead of floating-point values. This avoids floating-point rounding errors in financial calculations.

**Important:** Deposits and withdrawals are simulated for demonstration purposes. They do not move real money.

---

## Running Automated Tests

From the `backend` directory, activate the virtual environment and run:

```powershell
python -m pytest -v --tb=short
```

For test coverage:

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

The development test suite was previously reported as **93 passing tests and 0 failures**. This is a previously recorded result, not a claim that the current repository has been freshly tested. Run the commands above to reproduce the result against the current code.

### Build the frontend

From the repository root:

```powershell
cd frontend

npm install

npm run build
```

---

## Production Deployment and Observed Application Behaviour

The application is deployed using:

| Service | Hosting Platform |
|---|---|
| Frontend | Vercel |
| Backend | Render |
| PostgreSQL Database | Neon |

The following production application flows were manually exercised:

- User login.
- Dashboard loading.
- Account listing.
- Transaction history.
- Statements.
- Settings.
- Help and support pages.
- A test deposit and transfer.
- Transaction persistence after refreshing the application.
- Account balance and statement reconciliation for the exercised transactions.

The observed test transactions included a ₹480 simulated deposit and a ₹1 transfer. The resulting account balance and transaction records were consistent with the exercised operations.

These observations describe the tested application flows; they are not a certification of every endpoint or production security control.

**Deployment note:** Render free-tier services may spin down after inactivity, so the first request after a period of inactivity can take longer to respond.

---

## Security Considerations

LedgerLine incorporates the following security and integrity mechanisms:

- Argon2 password hashing.
- JWT-based authentication.
- Role-based authorization.
- Account ownership validation.
- Active-user verification.
- Token-version-based session invalidation.
- Database constraints for financial data integrity.
- Transactional financial operations.
- Idempotency protection.
- Concurrency protection.
- Audit logging for relevant operations.
- Automated security and authorization tests.

The threat model and remaining security risks are documented in [`THREATS.md`](THREATS.md).

AI-development notes, implementation decisions, prompts, and developer corrections are documented in [`PROMPTS.md`](PROMPTS.md).

This is an educational development project, not a certified production banking platform. A real financial deployment would require additional security reviews, operational controls, payment-provider integration, monitoring, database privilege hardening, compliance checks, and regulatory assessment.

---

## Project Documentation

| Document | Purpose |
|---|---|
| `README.md` | Project overview, installation, configuration, and usage |
| `PROMPTS.md` | AI prompts, suggestions, issues, developer corrections, and commit references |
| `THREATS.md` | Security threats, potential impacts, mitigations, and future improvements |

---

## Developer

**Bharath Babu Medikonda**

- GitHub: https://github.com/bharathprabha1
- Project Repository: https://github.com/bharathprabha1/LedgerLine

This project was developed as part of the Snovasys Fresher Hiring Challenge 2026.

---

## Disclaimer

LedgerLine is an educational software engineering project developed to demonstrate secure application design, backend development, database integrity, authentication, authorization, and financial transaction concepts.

It does not provide real banking services, hold customer funds, or process actual payments.

**Built with a focus on security, consistency, transparency, and verifiable transactions.**