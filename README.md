# CharkhoneApplication-Django

Charkhone Online Shop — A Django e-commerce project with Docker

## Table of Contents

* [About](#about)
* [Database Schema](#database-schema)
* [Services](#services)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Project Structure](#project-structure)
* [Password Reset](#password-reset)
* [Environment Variables](#environment-variables)
* [Features](#features)
* [Useful Commands](#useful-commands)
* [Development](#development)
* [Testing](#testing)
* [Architecture](#architecture)
* [Troubleshooting](#troubleshooting)
* [Production Hardening](#production-hardening)

---

## Database Schema

The current database schema is documented in:

```text
docs/db-diagram.png
```

![Database Schema](./docs/db-diagram.png)

The schema represents the currently implemented application domain. Future domains such as Orders, Inventory, and Payments will be added when those features are implemented.

---

## About

CharkhoneApplication is a Django-based e-commerce application.

The project uses Docker Compose to provide a reproducible development environment with PostgreSQL, Django, and smtp4dev.

The application currently focuses on:

* Custom email-based authentication
* Email verification
* Password reset
* Product catalog
* Product publishing
* Shopping cart
* AJAX cart quantity updates
* Newsletter subscription and verification
* REST API support
* Database integrity
* Concurrency-safe operations
* Automated testing

The project is being developed incrementally toward a complete e-commerce workflow:

```text
Registration
      ↓
Email Verification
      ↓
Login
      ↓
Product Catalog
      ↓
Shopping Cart
      ↓
Checkout
      ↓
Order
      ↓
Payment
      ↓
Order Management
```

The Checkout, Order, Inventory, and Payment stages are part of the ongoing development roadmap.

---

## Services

| Service        | Version   | Ports     | Description              |
| -------------- | --------- | --------- | ------------------------ |
| **PostgreSQL** | 15-alpine | 5432      | Primary database         |
| **Django**     | 5.2.16    | 8000      | Web application          |
| **smtp4dev**   | v3        | 25 / 5000 | Development email server |

---

## Prerequisites

* [Docker](https://docs.docker.com/get-docker/) 20.10+
* [Docker Compose](https://docs.docker.com/compose/install/) 2.0+
* Git

The recommended development workflow uses Docker Compose so that the required services can be started together.

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd CharkhoneApplication-django
```

### 2. Create the environment file

```bash
cp envs/dev/django/.env.sample envs/dev/django/.env
```

Edit the environment file according to your local configuration.

Example:

```env
DJANGO_SECRET_KEY="your-secret-key"
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]

POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

TIME_ZONE=UTC
```

> **Warning:** Never use development credentials or a development secret key in production.

### 3. Build and start the project

```bash
docker compose up --build -d
```

### 4. Apply migrations

```bash
docker exec -it charkhoneh-backend python manage.py migrate
```

### 5. Create an admin user

```bash
docker exec -it charkhoneh-backend python manage.py createsuperuser
```

### 6. Check the Django configuration

```bash
docker exec -it charkhoneh-backend python manage.py check
```

### 7. Access the services

| Service      | URL                          |
| ------------ | ---------------------------- |
| Django       | http://localhost:8000        |
| Django Admin | http://localhost:8000/admin/ |
| smtp4dev     | http://localhost:5000        |

---

## Project Structure

```text
CharkhoneApplication-django/
│
├── core/
│   ├── core/                    # Django project configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── accounts/                # Authentication and user management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── management/
│   │   │   └── commands/
│   │   └── tests/
│   │
│   ├── shop/                    # Product catalog
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── cart/                    # Shopping cart
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── website/                 # Public website
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── models.py
│   │   └── admin.py
│   │
│   ├── templates/               # Django templates
│   ├── static/                  # Static source files
│   ├── staticfiles/             # Collected static files
│   └── manage.py
│
├── dockerfiles/
│   └── dev/
│       └── django/
│
├── envs/
│   └── dev/
│       └── django/
│
├── docs/                        # Project documentation and diagrams
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

### Application Responsibilities

| Application | Responsibility                                      |
| ----------- | --------------------------------------------------- |
| `accounts`  | Users, authentication, verification, password reset |
| `shop`      | Products, categories, images and product visibility |
| `cart`      | Shopping cart and cart operations                   |
| `website`   | Public website and presentation layer               |
| `core`      | Django project configuration                        |

---

## Password Reset

Charkhoneh uses a custom password-reset flow based on Django's signing and hashing mechanisms.

**It does not rely on JWT tokens for password reset.**

The flow is designed around:

* Expiring reset tokens
* Single-use tokens
* Hashed token storage
* Atomic token consumption
* Concurrency protection
* Rate limiting
* Password validation
* Email-enumeration protection

### How it works

```text
User
 │
 │ Request password reset
 ▼
Django
 │
 ├── Validate request
 │
 ├── Create secure token
 │
 ├── Store token hash
 │
 └── Send reset email
          │
          ▼
       smtp4dev
```

When the user submits the reset token:

```text
Reset Request
      │
      ▼
Validate Token
      │
      ├── Invalid / Expired → Reject
      │
      ▼
Atomically Claim Token
      │
      ├── Already Used → Reject
      │
      ▼
Validate New Password
      │
      ▼
Update Password
      │
      ▼
Invalidate Token
```

### Security Properties

* **Expiration:** Reset tokens have a limited lifetime.
* **Single-use:** A successfully consumed token cannot be reused.
* **Hashing:** Stored token values are protected rather than keeping the raw token.
* **Concurrency protection:** Token consumption is protected against concurrent requests.
* **Rate limiting:** Password reset requests are rate-limited.
* **Password validation:** New passwords are checked against Django password validators.
* **Email enumeration protection:** Reset requests use a non-revealing response.
* **Atomic operations:** Token state changes are handled transactionally.

### Password Reset API

| Endpoint                    | Method | Description                        |
| --------------------------- | ------ | ---------------------------------- |
| `/accounts/request-reset/`  | POST   | Request a password reset           |
| `/accounts/reset-password/` | POST   | Reset password using a valid token |

Example request:

```bash
curl -X POST http://localhost:8000/accounts/request-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

Example response:

```json
{
  "message": "در صورت وجود ایمیل، لینک بازیابی ارسال شد."
}
```

### Cleanup Command

Expired password-reset tokens can be cleaned up using:

```bash
docker exec -it charkhoneh-backend \
python manage.py cleanup_expired_tokens
```

---

## Environment Variables

### Django

| Variable               | Description                   |
| ---------------------- | ----------------------------- |
| `DJANGO_SECRET_KEY`    | Django secret key             |
| `DJANGO_DEBUG`         | Enables Django debug mode     |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |

### PostgreSQL

| Variable            | Description               |
| ------------------- | ------------------------- |
| `POSTGRES_DB`       | Database name             |
| `POSTGRES_USER`     | Database user             |
| `POSTGRES_PASSWORD` | Database password         |
| `POSTGRES_HOST`     | PostgreSQL Docker service |
| `POSTGRES_PORT`     | PostgreSQL port           |

### Other

| Variable    | Description          |
| ----------- | -------------------- |
| `TIME_ZONE` | Application timezone |

Environment configuration should be kept outside the source code.

---

## Features

### Authentication

* Custom email-based user authentication
* User registration
* Email verification
* Login/logout
* Password validation
* Password reset
* Expiring reset tokens
* Single-use reset tokens
* Password reset rate limiting
* Email enumeration protection

### Product Catalog

* Product listing
* Product detail pages
* Categories
* Product images
* Product pricing
* Published/unpublished products
* Protection against exposing unpublished products

### Shopping Cart

* Session-based shopping cart
* Add products
* Remove products
* Update quantities
* AJAX quantity updates
* Cart validation
* Cart-related regression tests

### Newsletter

* Newsletter subscription
* Email verification
* Verification token handling
* Delivery status tracking
* Partial delivery handling
* HTML sanitization

### API

* Django REST Framework
* API serializers
* API validation
* Authentication and permission handling

### Database and Reliability

* PostgreSQL
* Database constraints
* Transactions
* Row-level locking where required
* Concurrency-safe operations
* Regression tests for previously fixed bugs

### Development Tools

* Docker Compose
* smtp4dev
* Django Debug Toolbar
* pytest
* pytest-django

---

## Django Debug Toolbar

Django Debug Toolbar is available during development.

When:

```env
DJANGO_DEBUG=True
```

the toolbar can be used to inspect:

* SQL queries
* Query execution time
* Requests and responses
* Templates
* Static files
* Cache usage
* Django settings
* Logging

> **Warning:** Debug mode and Django Debug Toolbar must not be enabled in a production environment.

---

## Useful Commands

### Docker

```bash
# Start services
docker compose up

# Start in background
docker compose up -d

# Rebuild and start
docker compose up --build -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# View backend logs
docker compose logs -f backend

# Check running services
docker compose ps
```

### Django Management

```bash
# Run Django management command
docker exec -it charkhoneh-backend python manage.py <command>

# Create superuser
docker exec -it charkhoneh-backend python manage.py createsuperuser

# Apply migrations
docker exec -it charkhoneh-backend python manage.py migrate

# Create migrations
docker exec -it charkhoneh-backend python manage.py makemigrations

# Collect static files
docker exec -it charkhoneh-backend python manage.py collectstatic

# Django system checks
docker exec -it charkhoneh-backend python manage.py check

# Django shell
docker exec -it charkhoneh-backend python manage.py shell

# Cleanup expired password reset tokens
docker exec -it charkhoneh-backend python manage.py cleanup_expired_tokens
```

### Testing

```bash
# Run the complete pytest suite
docker exec -it charkhoneh-backend pytest

# Run with verbose output
docker exec -it charkhoneh-backend pytest -v

# Run a specific test
docker exec -it charkhoneh-backend pytest path/to/test_file.py
```

### Database

```bash
docker exec -it charkhoneh-db psql -U postgres
```

---

## Development

### Static Path Converter

The `convert_static.py` utility converts hardcoded static paths in templates into Django static template tags.

Example:

```bash
python convert_static.py --dir core/templates
```

Preview changes without modifying files:

```bash
python convert_static.py --dir core/templates --dry-run
```

Create backups before modifying files:

```bash
python convert_static.py --dir core/templates --backup
```

### smtp4dev

smtp4dev captures outgoing emails during development.

* Web interface: `http://localhost:5000`
* SMTP server: `localhost:25`

Django can use smtp4dev with:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp4dev"
EMAIL_PORT = 25
EMAIL_USE_TLS = False
```

### Persian Fonts

The project includes Persian font resources for the website interface.

---

## Testing

The project uses `pytest` and `pytest-django`.

Run the full test suite:

```bash
docker exec -it charkhoneh-backend pytest
```

The test suite is intended to cover both normal application behavior and failure-sensitive cases.

Important test areas include:

* Authentication
* Registration
* Email verification
* Password reset
* Password validation
* Token expiration
* Token single-use behavior
* Password reset concurrency
* Product visibility
* Product catalog behavior
* Shopping cart operations
* AJAX cart operations
* Newsletter verification
* Email delivery failures
* Database integrity
* Regression scenarios

### Why concurrency tests matter

Some operations cannot be validated correctly using only sequential tests.

For example, password-reset token consumption must remain correct when two requests attempt to consume the same token concurrently.

The expected behavior is:

```text
Request A ──► Token ──► SUCCESS
Request B ──► Same Token ──► REJECTED
```

rather than allowing both requests to successfully consume the same token.

---

## Architecture

Charkhoneh currently follows a **modular monolith** architecture.

The application remains a single Django deployment while separating responsibilities into Django applications.

```text
                         Client
                           │
                           ▼
                     Django Application
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
      accounts           shop             cart
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                       PostgreSQL
                           │
                           ▼
                        smtp4dev
```

### Why Modular Monolith?

At the current project scale, a modular monolith provides:

* Clear application boundaries
* Simpler deployment
* Lower operational complexity
* Easier local development
* Straightforward database transactions
* Room for future architectural evolution

Microservices are intentionally not introduced at this stage.

---

## Data Integrity and Concurrency

The project treats application-level validation and database-level integrity as separate responsibilities.

Where appropriate, critical operations use:

* `transaction.atomic()`
* `select_for_update()`
* Database constraints
* Unique constraints
* Explicit state transitions

This is particularly important for operations such as:

* Password reset token consumption
* Email verification token handling
* Cart data integrity
* Unique product slugs
* Concurrent requests affecting the same database records

---

## Entity Relationship Diagram

The current ERD represents implemented models only.

```text
User
 │
 ├──────────────► Email Verification
 │
 ├──────────────► Password Reset Token
 │
 └──────────────► Cart
                       │
                       └──────────────► Product
                                            │
                                            └──────────────► Category
```

The complete visual diagram is available at:

```text
docs/db-diagram.png
```

Future Order, Inventory, and Payment relationships should only be added to the ERD after their corresponding models are implemented.

---

## Troubleshooting

### Database Connection Error

Check the running services:

```bash
docker compose ps
```

Check PostgreSQL logs:

```bash
docker compose logs db
```

### Backend Logs

```bash
docker compose logs -f backend
```

### Port Already in Use

If port `8000` is already occupied, change the host-side port mapping in `docker-compose.yml`.

For example:

```yaml
ports:
  - "8001:8000"
```

The application will then be available at:

```text
http://localhost:8001
```

### Reset the Development Database

> **Warning:** This removes the development database data.

```bash
docker compose down -v
rm -rf postgres/data/*
docker compose up --build -d
```

After resetting the database:

```bash
docker exec -it charkhoneh-backend python manage.py migrate
```

---

# Production Hardening

The project has undergone a series of security, integrity, concurrency, and testing improvements.

## Completed Engineering Improvements

### Security

* Protected production configuration from missing `SECRET_KEY`.
* Added email enumeration protection.
* Improved token invalidation.
* Added token expiration handling.
* Added password validation.
* Added password reset rate limiting.
* Reduced unsafe exception handling.
* Protected sensitive token operations.

### Authentication and Verification

* Custom email-based user authentication.
* Email verification workflow.
* Expiring verification tokens.
* Single-use token behavior.
* Password reset with secure token handling.
* Concurrency protection for password-reset token consumption.

### Database Integrity

* Unique constraints for important identifiers.
* Transactional token operations.
* Row-level locking for concurrency-sensitive operations.
* Product publication filtering.
* Protection against invalid application states.

### Cart

* Session-based cart implementation.
* Cart quantity management.
* AJAX quantity updates.
* Validation of cart product state.
* Regression coverage for cart-related bugs.

### Newsletter

* Email verification.
* Delivery state tracking.
* Partial delivery handling.
* HTML sanitization.
* Failure-aware email processing.

### Testing

The project now uses pytest/pytest-django for automated testing.

Testing has been expanded beyond simple happy-path tests to include:

* Regression tests
* Security-sensitive cases
* Failure scenarios
* Database integrity
* Concurrency behavior

---

## Current Development Roadmap

The project is being developed incrementally.

### Implemented

* Authentication
* Registration
* Email verification
* Password reset
* Product catalog
* Product visibility
* Shopping cart
* AJAX cart updates
* Newsletter
* REST API foundation
* Automated tests
* Docker development environment
* PostgreSQL
* Concurrency and integrity improvements

### In Progress / Planned

* Checkout
* Order creation
* Inventory management
* Payment integration
* Payment state management
* Order management
* Complete end-to-end purchase flow

The README intentionally distinguishes implemented functionality from future functionality so that the documentation reflects the actual state of the application.
