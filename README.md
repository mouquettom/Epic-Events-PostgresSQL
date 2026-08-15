# Epic Events CRM

Command-line CRM application developed in Python to manage employees, clients, contracts, and events for the fictional company **Epic Events**.

The project uses a layered architecture to clearly separate the user interface, business rules, and data access.

---

## Features

### Authentication

- Login with email and password
- Password hashing with bcrypt
- JWT token generation
- User session management
- Access token expiration
- Secure logout

### Employee Management

Features restricted to the management department:

- List employees
- View an employee
- Create an employee
- Update an employee
- Delete an employee
- Prevent users from deleting their own account
- Assign `GESTION`, `COMMERCIAL`, and `SUPPORT` roles

### Client Management

- Client creation by a sales employee
- Viewing and updating clients according to permissions
- Duplicate email detection
- Automatic assignment of the client to the logged-in sales employee
- Client deletion according to business rules

### Contract Management

- Create a contract for a client
- Manage total and remaining amounts
- Sign a contract
- View contracts
- List unsigned contracts
- List contracts with outstanding balances
- Update contracts according to role and ownership
- Contract deletion restricted to the management department

### Event Management

- Create an event from a signed contract
- Manage dates, location, number of attendees, and notes
- View events according to role
- Assign a support employee
- Remove a support employee
- List events without assigned support
- Update events by the management department or assigned support employee
- Event deletion restricted to the management department

### Monitoring

- Technical error reporting with Sentry
- Distinction between business errors and unexpected errors
- Configurable Sentry environment
- No personal data sent by default

---

## Roles and Permissions

### GESTION

The management department can, among other things:

- manage employees;
- view all clients;
- view and update contracts;
- view unsigned contracts and contracts with outstanding balances;
- view and update all events;
- assign or remove a support employee;
- delete contracts and events.

### COMMERCIAL

A sales employee can, among other things:

- create and manage their clients;
- create contracts for their own clients;
- view and update their own contracts;
- view their contracts with outstanding balances;
- create an event for one of their signed contracts;
- view events associated with their contracts.

### SUPPORT

A support employee can, among other things:

- view clients;
- view contracts;
- view events assigned to them;
- update events assigned to them.

Permissions are enforced in the `services` layer, independently of the menus displayed in the interface.

---

## Architecture

```
OC_P12_EpicEvents/
│
├── app/
│   ├── controllers/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── session/
│   └── utils/
│
├── migrations/
├── tests/
│   ├── functional/
│   ├── integration/
│   ├── unit/
│   ├── conftest.py
│   ├── factories.py
│   └── README.md
│
├── .env.example
├── .flake8
├── .gitignore
├── alembic.ini
├── main.py
├── pytest.ini
├── requirements.txt
└── README.md

```

### Layer Organization

```
CLI Interface
    ↓
Controllers
    ↓
Services
    ↓
Repositories
    ↓
SQLAlchemy
    ↓
PostgreSQL

```

- **Controllers** handle console input and output.
- **Services** enforce business rules and permissions.
- **Repositories** perform SQLAlchemy queries.
- **Models** define database tables and their relationships.
- `CurrentSession` stores the employee and token for the active session.
- Utilities handle exceptions, passwords, JWTs, and Sentry.

---

## Technologies Used

- Python 3
- PostgreSQL
- SQLAlchemy 2
- Alembic
- psycopg
- PyJWT
- bcrypt
- python-dotenv
- Sentry SDK
- pytest
- pytest-cov
- Flake8
- Black

---

## Prerequisites

- Python 3.11 or later
- PostgreSQL
- Git
- A Python virtual environment
- An optional Sentry project for error monitoring

---

## Installation

### 1. Clone the Repository

```
git clone https://github.com/mouquettom/Epic-Events-PostgresSQL.git
cd Epic-Events-PostgresSQL
```

### 2. Create a Virtual Environment

On macOS or Linux:

```
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

---

## Environment Configuration

Copy the example file:

```
cp .env.example .env
```

Then set the variables in `.env`:

```
DB_USER=epic_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=epic_events

JWT_SECRET_KEY=replace_with_a_long_random_secret

SENTRY_DSN=
SENTRY_ENVIRONMENT=development
```

The `.env` file contains sensitive information and must never be committed to version control.

### Generate a JWT Secret Key

```
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Configure Sentry

After creating a Python project in Sentry, retrieve the DSN from:

```
Settings → Projects → Client Keys (DSN)

```

Then add it to `.env`:

```
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=development
```

The application also works without Sentry if `SENTRY_DSN` is left empty.

---

## PostgreSQL Configuration

PostgreSQL must be installed and the server must be running before proceeding.

### Connect to PostgreSQL

From a terminal, connect using a PostgreSQL user with sufficient privileges to create a database and a user.

For example:

```
psql -d postgres
```

Depending on your local configuration, you may need to specify the user:

```
psql -U postgres -d postgres
```

### Create the Database and User

From the PostgreSQL prompt:

```
CREATE DATABASE epic_events;

CREATE USER epic_user
WITH PASSWORD 'your_database_password';

GRANT ALL PRIVILEGES
ON DATABASE epic_events
TO epic_user;
```

The password must match the `DB_PASSWORD` value defined in the `.env` file.

### Grant Schema Permissions

Connect to the newly created database:

```
\c epic_events
```

Then allow `epic_user` to use and create objects in the `public` schema:

```
GRANT USAGE, CREATE
ON SCHEMA public
TO epic_user;
```

Exit PostgreSQL:

```
\q

```

The database is now ready for Alembic migrations.

---

## Alembic Migrations

Alembic is the recommended method for creating and updating the database schema.

Apply all migrations:

```
alembic upgrade head
```

Display the current migration:

```
alembic current
```

Display the migration history:

```
alembic history
```

Create a new migration after modifying the models:

```
alembic revision --autogenerate -m "Migration description"
```

Then apply it:

```
alembic upgrade head
```

The `app/database/init_db.py` script may be used in some development contexts, but Alembic should remain the source of truth for the project schema.

---

## Creating the First Management Account

Once the database and tables are ready:

```
python -m app.database.create_admin
```

The created account is automatically assigned the `GESTION` role.

---

## Running the Application

```
python main.py
```

After login, the displayed menu depends on the employee's role.

---

## Security

### Passwords

Passwords are hashed with bcrypt and are never stored in plain text.

The current password policy requires at least eight characters.

### JWT

JWT tokens:

- are signed using `HS256`;
- contain the employee ID;
- expire after sixty minutes;
- use a secret key loaded from the `.env` file.

### Sensitive Variables

The following items must never be committed to the Git repository:

- `.env`
- PostgreSQL passwords
- JWT secret key
- JWT tokens
- integration secrets
- real personal information

---

## Sentry

Sentry is initialized at application startup when `SENTRY_DSN` is defined.

Business exceptions such as:

- `ValidationError`
- `AuthorizationError`
- `DuplicateError`
- `NotFoundError`

are displayed to the user without being treated as technical errors.

Unexpected exceptions are sent to Sentry from `main.py`.

The configuration disables the automatic transmission of personal data:

```
send_default_pii=False
```

---

## Tests

Tests are divided into three categories.

### Unit Tests

```
pytest tests/unit -v
```

### Integration Tests

```
pytest tests/integration -v
```

### Functional Tests

```
pytest tests/functional -v
```

### Run the Full Test Suite

```
pytest
```

At the time of the project's latest validation:

```
481 tests passed
95% overall coverage

```

These values may change as the codebase evolves.

### Coverage

```
pytest --cov=app --cov-report=term-missing
```

Generate an HTML report:

```
pytest --cov=app --cov-report=html
```

The report is then available at:

```
htmlcov/index.html

```

---

## Code Quality

### Black

Check formatting:

```
black --check app tests main.py
```

Apply formatting:

```
black app tests main.py
```

### Flake8

```
flake8 app tests main.py
```

---

## Main Business Rules

- Only a management employee can manage employees.
- An employee cannot delete their own account.
- Only a sales employee can create a client.
- A sales employee can only update their own clients.
- Only a sales employee can create a contract.
- A contract can only be created for a client assigned to that sales employee.
- The remaining amount cannot be negative or exceed the total amount.
- An event can only be created for a signed contract.
- Only the management department can assign a support employee.
- A support employee can only update events assigned to them.
- Unexpected technical errors are reported to Sentry.

---

## Possible Improvements

- Dynamically adapt submenus to each role's permissions
- Explicitly prevent deletion of a client who has contracts
- Filter a sales employee's client list by ownership
- Complete field validation when updating an employee
- Add a password reset command
- Centralize environment variable configuration
- Add a web interface or REST API
- Automate checks with continuous integration

---

## Author

Project developed as part of the OpenClassrooms Python Developer learning path.

---
