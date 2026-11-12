# LedgerLine



**Secure money movement with a ledger you can prove.**



LedgerLine is a full-stack financial transaction demonstration application. It combines a React frontend with a FastAPI backend and PostgreSQL database to demonstrate authentication, role-based access, account management, simulated deposits and withdrawals, account-to-account transfers, double-entry ledger records, idempotency, concurrency protection, transaction history, statements, and audit logging.



> **Project status:** LedgerLine is deployed for evaluation. Deposits and withdrawals are simulated; the application is not connected to a real bank or payment network. It is an educational hiring-challenge project, not a production banking service.



## Live application and API



- **Live application:** https://ledgerline-ten-orpin.vercel.app

- **Backend API:** https://ledgerline-n9fl.onrender.com

- **Swagger documentation:** https://ledgerline-n9fl.onrender.com/docs

- **OpenAPI schema:** https://ledgerline-n9fl.onrender.com/openapi.json



## Features



### Authentication and authorization

- User registration and login.

- Password hashing using Argon2.

- JWT-based authentication.

- Role-based access control for `ADMIN`, `ACCOUNT_HOLDER`, and `AUDITOR`.

- Active-user validation for protected requests.

- Restricted administrator operations and account ownership checks.



### Account management

- Administrator-controlled customer account creation.

- Account information retrieval and account listing.

- Customer account ownership restrictions.

- Account status management.

- Protected system settlement account.

- Account status validation during financial operations.



### Transactions and double-entry ledger

- Simulated deposits and withdrawals.

- Transfers between customer accounts.

- Double-entry ledger records.

- Unique transaction references and transaction status tracking.

- Idempotency support for transaction requests.

- Transaction history with pagination and transaction detail retrieval.

- Account statements with debit and credit entries.

- Monetary amounts represented in integer paise.



### Audit and financial integrity

- Audit logging for relevant sensitive operations.

- Database constraints for important financial data.

- Database transactions for financial operations.

- Account balance validation and overdraft prevention.

- Role-based and object-level authorization.

- Protection against duplicate transaction requests.

- Concurrency protection for simultaneous financial operations.

- Automated authentication, authorization, transaction, and concurrency tests.



## Technology stack



| Component | Technology |

|---|---|

| Frontend | React, TypeScript, Vite |

| Backend framework | FastAPI |

| Programming language | Python 3.13 |

| Database | PostgreSQL |

| ORM | SQLAlchemy |

| Database migrations | Alembic |

| Data validation | Pydantic |

| Authentication | JWT |

| Password hashing | Argon2 |

| Database driver | Psycopg 3 |

| Testing | Pytest, Pytest-Cov |

| API documentation | Swagger UI |

| Frontend hosting | Vercel |

| Backend hosting | Render |

| Database hosting | Neon PostgreSQL |



## Demo access for evaluators

LedgerLine supports three roles:

| Role | Demo login |
|---|---|
| Administrator | Create/use a dedicated evaluation account |
| Account holder | Create/use a dedicated evaluation account |
| Auditor | `auditor@gmail.com` |

**Password policy:** Demo passwords are intentionally not published in this repository. Share temporary passwords with evaluators through a private channel only. Do not publish personal passwords, production administrator credentials, JWT tokens, database URLs, API keys, `.env` files, or application secrets. Disable or rotate evaluation credentials after the evaluation period.

### Role overview

- **ADMIN:** Administrative operations, including customer account creation and permitted account management.
- **ACCOUNT_HOLDER:** Access to owned accounts and permitted financial operations.
- **AUDITOR:** Read/review access to financial information permitted by the backend authorization rules.

### Auditor permissions — production checks

The following checks were performed against the deployed API while authenticated as the AUDITOR role:

| Request | Observed result | Status |
|---|---:|---|
| `GET /api/v1/accounts` | HTTP 200 | Verified |
| `GET /api/v1/transactions` | HTTP 200 | Verified |
| `POST /api/v1/transactions/deposit` | HTTP 403 | Verified blocked |
| `POST /api/v1/transactions/transfer` | HTTP 403 | Verified blocked |

The API returned `403 Forbidden` for deposit and transfer requests with role-specific authorization messages. Account creation and withdrawal restrictions still require separate verification; do not assume they are verified until tested.

## Project structure



```text

LedgerLine/

├── backend/

│   ├── app/

│   │   ├── api/

│   │   │   ├── deps.py

│   │   │   └── v1/

│   │   │       ├── auth.py

│   │   │       ├── accounts.py

│   │   │       └── transactions.py

│   │   ├── core/

│   │   ├── db/

│   │   ├── models/

│   │   ├── schemas/

│   │   ├── services/

│   │   └── main.py

│   ├── migrations/

│   ├── tests/

│   ├── .env.example

│   ├── alembic.ini

│   ├── requirements.txt

│   ├── bootstrap_admin.py

│   └── initialize_system_accounts.py

├── frontend/

│   ├── src/

│   ├── public/

│   └── package.json

├── .gitignore

├── README.md

├── PROMPTS.md

└── THREATS.md

```



## Prerequisites



Install:

- Python 3.13

- Node.js and npm

- PostgreSQL (or a PostgreSQL connection string)

- Git

- PowerShell on Windows (or an equivalent terminal)



## Local installation and setup



### 1. Clone the repository



```powershell

git clone https://github.com/bharathprabha1/LedgerLine.git

cd LedgerLine

```



### 2. Configure and start the backend



```powershell

cd backend

py -3.13 -m venv .venv

.\\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Copy-Item .env.example .env

notepad .env

```



Edit `.env` with your own PostgreSQL connection string and a strong, randomly generated application secret. Do not use production credentials from the deployed environment.



Ensure PostgreSQL is running and the configured database exists. Then run:



```powershell

$env:PYTHONPATH = (Get-Location).Path

alembic upgrade head

python initialize_system_accounts.py

```



For a fresh local database, create the initial administrator interactively:



```powershell

python bootstrap_admin.py

```



Start the backend:



```powershell

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

```



Backend:

- API: http://127.0.0.1:8000

- Swagger UI: http://127.0.0.1:8000/docs

- ReDoc: http://127.0.0.1:8000/redoc



### 3. Configure and start the frontend



Open a second terminal from the repository root:



```powershell

cd frontend

npm install

```



Configure the frontend environment variable `VITE_API_BASE_URL` to:



```text

http://127.0.0.1:8000/api/v1

```



If your frontend setup uses a local `.env` file, create `frontend/.env` and add:



```env

VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

```



Start the frontend:



```powershell

npm run dev

```



Open the local URL printed by Vite in the terminal.



### 4. Production environment configuration



The deployed frontend and backend use separate hosting services. For a new deployment, configure the frontend API base URL to point to the backend API, and configure the backend CORS allowlist to include the frontend origin. Set database credentials and application secrets through the hosting provider's environment-variable settings, not in source code.



## API endpoints



All API endpoints use the `/api/v1` prefix.



### Authentication



| Method | Endpoint | Description |

|---|---|---|

| POST | `/api/v1/auth/register` | Register an account holder |

| POST | `/api/v1/auth/login` | Authenticate a user |

| GET | `/api/v1/auth/me` | Retrieve the current user |



### Account management



| Method | Endpoint | Description |

|---|---|---|

| POST | `/api/v1/accounts` | Create a customer account (administrator permission required) |

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



Use Swagger UI at `/docs` to inspect the current request schemas, authentication requirements, and available operations.



### Idempotency



Transaction creation endpoints require an `Idempotency-Key` HTTP header. The key helps prevent duplicate processing when a client retries a request. Reusing the same key with a different request payload is rejected.



Example:



```http

Idempotency-Key: unique-operation-123

```



## Running automated tests



From the `backend` directory, activate the virtual environment and run:



```powershell

python -m pytest -v --tb=short

```



For coverage:



```powershell

python -m pytest --cov=app --cov-report=term-missing

```



The development test suite was previously verified with **93 passing tests and 0 failures**. Test results can change as the code evolves; run the commands above to reproduce the result on your machine.



Build the frontend:



```powershell

cd ..\frontend

npm install

npm run build

```



## Double-entry accounting approach



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



Transaction amounts are represented in integer paise rather than floating-point values to avoid floating-point rounding errors in financial calculations.



**Important:** Deposits and withdrawals are simulated for this project. They are not connected to a real bank, payment gateway, or live payment network.



## Current role and account verification

The deployed database currently contains:

| Role | Registered users |
|---|---:|
| ADMIN | 1 |
| ACCOUNT_HOLDER | 2 |
| AUDITOR | 1 |

These counts were checked directly against the PostgreSQL `users` table. The auditor account is active and successful login to the deployed frontend was observed. Its display name was initially entered as `ADUITOR`; this is a display-name typo and does not change the assigned `AUDITOR` role.

## Security considerations



LedgerLine incorporates:

- Argon2 password hashing.

- JWT-based authentication.

- Role-based authorization.

- Account ownership validation.

- Active-user verification.

- Database constraints for financial data integrity.

- Transactional financial operations.

- Idempotency protection.

- Concurrency protection.

- Audit logging for relevant operations.

- Automated security and authorization tests.



The threat model and remaining security risks are documented in [`THREATS.md`](THREATS.md). AI-development notes and implementation decisions are documented in [`PROMPTS.md`](PROMPTS.md).



This is an educational development project, not a certified production banking platform. Production deployment would require additional security reviews, operational controls, payment-provider integration, monitoring, database privilege hardening, and regulatory assessment.



## Project documentation



| Document | Purpose |

|---|---|

| `README.md` | Project overview, installation, configuration, and usage |

| `PROMPTS.md` | AI prompts, suggestions, issues, developer corrections, and commit references |

| `THREATS.md` | Security threats, potential impacts, mitigations, and future improvements |



## Disclaimer



LedgerLine is an educational software engineering project. It does not provide real banking services, hold customer funds, or process actual payments.
