# LedgerLine



**A secure, API-first digital banking and double-entry ledger system.**



LedgerLine is a banking backend project built with FastAPI and PostgreSQL. It provides user authentication, account management, simulated cash transactions, account transfers, transaction history, account statements, and audit logging.



> **Project status:** Backend development is in progress. This repository currently contains the backend API; a completed frontend and production payment integration are not claimed.



## Features



### Authentication and authorization

- User registration and login.

- Password hashing using Argon2.

- JWT-based authentication.

- Role-based access control for administrators, account holders, and auditors.

- Active-user validation for protected requests.



### Account management

- Create customer accounts (administrator access).

- View account information.

- Account ownership restrictions.

- Account status management.

- Protected system settlement account.



### Transactions and ledger

- Simulated deposits and withdrawals.

- Transfers between accounts.

- Double-entry ledger records.

- Transaction references and status tracking.

- Idempotency support for transaction requests.

- Transaction history and transaction details.

- Account statements with debit and credit entries.



### Audit and security

- Audit log records for relevant operations.

- Database constraints for important financial data.

- Database transactions for financial operations.

- Account balance validation.

- Role and ownership checks.



## Technology stack



| Component | Technology |

|---|---|

| Backend framework | FastAPI |

| Language | Python |

| Database | PostgreSQL |

| ORM | SQLAlchemy |

| Database migrations | Alembic |

| Data validation | Pydantic |

| Authentication | JWT |

| Password hashing | Argon2 |

| Testing | Pytest |

| API documentation | Swagger UI |



## Project structure



```text
LedgerLine/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- deps.py
|   |   |   `-- v1/
|   |   |       |-- auth.py
|   |   |       |-- accounts.py
|   |   |       `-- transactions.py
|   |   |-- core/
|   |   |-- db/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- main.py
|   |-- migrations/
|   |-- tests/
|   |-- .env.example
|   |-- alembic.ini
|   `-- requirements.txt
|-- .gitignore
|-- README.md
|-- PROMPTS.md
`-- THREATS.md



## Prerequisites



Install the following before running the project:



- Python 3.13

- PostgreSQL

- Git

- PowerShell (Windows)



## Local setup



### 1. Clone the repository



```powershell

git clone YOUR_REPOSITORY_URL

cd LedgerLine

```



Replace `YOUR_REPOSITORY_URL` with the actual repository URL.



### 2. Create and activate a virtual environment



```powershell

cd backend

py -3.13 -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



### 3. Install dependencies



```powershell

python -m pip install -r requirements.txt

```



### 4. Configure environment variables



Create your local environment file:



```powershell

Copy-Item .env.example .env

notepad .env

```



Configure the PostgreSQL connection string and a strong, randomly generated application secret in `.env`.



**Never commit `.env` or share real credentials.**



### 5. Run database migrations



Make sure PostgreSQL is running and the configured database exists.



```powershell

alembic upgrade head

```



### 6. Initialize the system settlement account



```powershell

python initialize_system_accounts.py

```



### 7. Create the initial administrator



```powershell

python bootstrap_admin.py

```



Follow the interactive prompts. The script is intended for initial administrator setup.



### 8. Start the API server



```powershell

python -m uvicorn app.main:app --reload

```



The API will be available at:



```text

http://127.0.0.1:8000

```



Interactive API documentation:



```text

http://127.0.0.1:8000/docs

```



## API endpoints



The API uses the `/api/v1` prefix.



| Method | Endpoint | Purpose |

|---|---|---|

| POST | `/auth/register` | Register an account holder |

| POST | `/auth/login` | Authenticate a user |

| GET | `/auth/me` | Get the current user |

| POST | `/accounts` | Create a customer account |

| GET | `/accounts` | List accessible accounts |

| GET | `/accounts/{account_id}` | Get account details |

| PATCH | `/accounts/{account_id}/status` | Update account status |

| GET | `/accounts/{account_id}/statement` | Get an account statement |

| POST | `/transactions/deposit` | Simulate a deposit |

| POST | `/transactions/withdrawal` | Withdraw funds |

| POST | `/transactions/transfer` | Transfer funds |

| GET | `/transactions` | List transaction history |

| GET | `/transactions/{transaction_id}` | Get transaction details |



Use Swagger UI at `/docs` to inspect request schemas and try the endpoints with an authorized bearer token.



## Running tests



From the `backend` directory, activate the virtual environment and run:



```powershell

python -m pytest -v

```



The existing service-level test suite includes cash transaction, transfer, and concurrency scenarios. Check the latest test output before reporting the current test count or coverage.



## Accounting approach



LedgerLine uses a double-entry accounting approach.



- A deposit records a debit to the system settlement account and a credit to the customer account.

- A withdrawal records a debit to the customer account and a credit to the settlement account.

- A transfer records a debit to the source account and a credit to the destination account.



Amounts are represented in integer paise to avoid floating-point rounding errors in financial calculations.



**Important:** Deposits are simulated for this project. They are not connected to a real bank, payment gateway, or live payment network.



## Security considerations



- Passwords are hashed rather than stored in plaintext.

- Protected API endpoints require JWT authentication.

- Authorization checks restrict operations by role and account ownership.

- Database constraints help protect financial data integrity.

- Transaction operations use database transactions.

- Idempotency records help prevent duplicate processing of repeated requests.

- Audit logs record relevant system activities.



This is a development project, not a certified production banking platform. A production deployment would require additional security review, operational controls, payment-provider integration, monitoring, and regulatory assessment.



## Project documentation



- `PROMPTS.md` â€” AI prompts, generated suggestions, corrections, and related commit references.

- `THREATS.md` â€” Security threats, impact analysis, and mitigations.



## Disclaimer



LedgerLine is an educational software engineering project. It does not provide real banking services, hold customer funds, or process actual payments.


