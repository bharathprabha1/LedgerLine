# LedgerLine

**A secure, API-first digital banking and double-entry ledger system.**

LedgerLine is a banking backend application built with **FastAPI and PostgreSQL**. It provides user authentication, account management, simulated cash transactions, account transfers, transaction history, account statements, idempotency, and audit logging.

> **Project status:** Backend implementation and automated testing are completed for the current development scope. Frontend development and production payment integration are not included in the current implementation.

## Features

### 1. Authentication and authorization

- User registration and login.
- Password hashing using Argon2.
- JWT-based authentication.
- Role-based access control for administrators, account holders, and auditors.
- Active-user validation for protected requests.
- Restricted administrator operations.

### 2. Account management

- Administrator-controlled customer account creation.
- Account information retrieval.
- Customer account ownership restrictions.
- Account status management.
- Protected system settlement account.
- Account status validation during financial operations.

### 3. Transactions and double-entry ledger

- Simulated deposits and withdrawals.
- Transfers between customer accounts.
- Double-entry ledger records.
- Unique transaction references.
- Transaction status tracking.
- Idempotency support for transaction requests.
- Transaction history with pagination.
- Transaction detail retrieval.
- Account statements with debit and credit entries.
- Amounts represented in integer paise.

### 4. Audit and security

- Audit logging for relevant sensitive operations.
- Database constraints for important financial data.
- Database transactions for financial operations.
- Account balance validation.
- Role-based and object-level authorization.
- Protection against duplicate transaction requests.
- Automated authentication, authorization, transaction, and concurrency tests.

## Technology stack

| Component | Technology |
|---|---|
| Backend framework | FastAPI |
| Programming language | Python 3.13 |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database migrations | Alembic |
| Data validation | Pydantic |
| Authentication | JWT |
| Password hashing | Argon2 |
| Database driver | Psycopg 3 |
| Testing | Pytest |
| Coverage | Pytest-Cov |
| API documentation | Swagger UI |

## Project structure

```text
LedgerLine/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── accounts.py
│   │   │       └── transactions.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   │
│   │   ├── models/
│   │   │   ├── account.py
│   │   │   ├── audit_log.py
│   │   │   ├── enums.py
│   │   │   ├── idempotency.py
│   │   │   ├── ledger_entry.py
│   │   │   ├── transaction.py
│   │   │   └── user.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── account.py
│   │   │   ├── auth.py
│   │   │   ├── statement.py
│   │   │   └── transaction.py
│   │   │
│   │   ├── services/
│   │   │   ├── account_service.py
│   │   │   ├── statement_service.py
│   │   │   └── transaction_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── migrations/
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api_security.py
│   │   ├── test_cash_transactions.py
│   │   ├── test_concurrency.py
│   │   ├── test_statements.py
│   │   ├── test_transactions.py
│   │   └── test_transaction_api.py
│   │
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── bootstrap_admin.py
│   └── initialize_system_accounts.py
│
├── .gitignore
├── README.md
├── PROMPTS.md
└── THREATS.md
```

## Prerequisites

Install the following software:

- Python 3.13
- PostgreSQL
- Git
- PowerShell (Windows)

## Local installation and setup

### 1. Clone the repository

```powershell
git clone YOUR_REPOSITORY_URL
cd LedgerLine
```

Replace `YOUR_REPOSITORY_URL` with your actual repository URL.

### 2. Create a Python virtual environment

```powershell
cd backend

py -3.13 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install all pinned backend dependencies using the requirements file:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Configure the required database connection string and a strong, randomly generated application secret.

Use your own PostgreSQL credentials and database details.

**Important:** Never commit `.env` or share real database credentials and JWT signing secrets.

### 5. Run database migrations

Ensure PostgreSQL is running and the configured database has been created.

Run:

```powershell
alembic upgrade head
```

This applies the database migrations.

### 6. Initialize the system settlement account

Run:

```powershell
python initialize_system_accounts.py
```

This initializes the system settlement account required by the transaction services.

### 7. Create the initial administrator

Run:

```powershell
python bootstrap_admin.py
```

Follow the interactive prompts to configure the initial administrator account.

The bootstrap script is intended for initial administrator setup.

### 8. Start the FastAPI application

Run:

```powershell
python -m uvicorn app.main:app --reload
```

The backend API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative API documentation:

```text
http://127.0.0.1:8000/redoc
```

## API endpoints

All endpoints use the `/api/v1` prefix.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register an account holder |
| POST | `/api/v1/auth/login` | Authenticate a user |
| GET | `/api/v1/auth/me` | Retrieve the current user |

### Account management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/accounts` | Create a customer account |
| GET | `/api/v1/accounts` | List accessible accounts |
| GET | `/api/v1/accounts/{account_id}` | Retrieve account details |
| PATCH | `/api/v1/accounts/{account_id}/status` | Update account status |
| GET | `/api/v1/accounts/{account_id}/statement` | Retrieve an account statement |

### Financial transactions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/transactions/deposit` | Simulate a deposit |
| POST | `/api/v1/transactions/withdrawal` | Withdraw funds |
| POST | `/api/v1/transactions/transfer` | Transfer funds between accounts |
| GET | `/api/v1/transactions` | Retrieve transaction history |
| GET | `/api/v1/transactions/{transaction_id}` | Retrieve transaction details |

### Idempotency

Transaction creation endpoints require an `Idempotency-Key` HTTP header.

The key helps prevent duplicate processing when a client retries a request.

Reusing the same key with a different request payload is rejected.

Example:

```http
Idempotency-Key: unique-operation-123
```

Use Swagger UI at `/docs` to inspect request schemas, authentication requirements, and available API operations.

## Running automated tests

From the `backend` directory, activate the virtual environment and execute:

### Run the complete test suite

```powershell
python -m pytest -v --tb=short
```

### Run tests with code coverage

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

### Latest verified test results

| Metric | Result |
|---|---:|
| Total tests | 76 |
| Passed | 76 |
| Failed | 0 |
| Overall code coverage | 92% |

These results reflect the verified development test run on November 7, 2026.

## Double-entry accounting approach

LedgerLine follows a double-entry accounting approach.

Each posted financial transaction creates corresponding debit and credit ledger entries.

### Deposit

- Debit the system settlement account.
- Credit the customer account.

### Withdrawal

- Debit the customer account.
- Credit the system settlement account.

### Transfer

- Debit the source account.
- Credit the destination account.

### Monetary precision

All transaction amounts are represented in integer paise rather than floating-point values.

This avoids floating-point rounding errors in financial calculations.

**Important:** Deposits and withdrawals are simulated for this project. They are not connected to a real bank, payment gateway, or live payment network.

## Security considerations

LedgerLine incorporates several security controls:

- Argon2 password hashing.
- JWT-based authentication.
- Role-based authorization.
- Account ownership validation.
- Active-user verification.
- Database constraints for financial data integrity.
- Transactional financial operations.
- Idempotency protection.
- Audit logging for relevant operations.
- Automated security and authorization tests.

The threat model and remaining security risks are documented in `THREATS.md`.

This is an educational development project, not a certified production banking platform. Production deployment would require additional security reviews, operational controls, payment-provider integration, monitoring, and regulatory assessment.

## Project documentation

| Document | Purpose |
|---|---|
| `README.md` | Project overview, installation, configuration, and usage |
| `PROMPTS.md` | AI prompts, suggestions, issues, developer corrections, and commit references |
| `THREATS.md` | Security threats, potential impacts, mitigations, and future improvements |

## Disclaimer

LedgerLine is an educational software engineering project. It does not provide real banking services, hold customer funds, or process actual payments.