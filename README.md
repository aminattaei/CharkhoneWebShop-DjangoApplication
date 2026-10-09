# CharkhonehApplication-Django

**Charkhone Online Shop — Django E-Commerce Application**

A production-oriented Django e-commerce application built with a **modular monolith architecture**, PostgreSQL, Docker, Django REST Framework, and automated testing.

The project is being developed as both a functional online shop and a software-engineering portfolio project, with particular focus on authentication, data integrity, security, concurrency, testing, and maintainable architecture.

---

## Table of Contents

- [CharkhonehApplication-Django](#charkhonehapplication-django)
  - [Table of Contents](#table-of-contents)
- [Overview](#overview)
  - [What is Charkhoneh?](#what-is-charkhoneh)
  - [Database Schema](#database-schema)
  - [Target Users](#target-users)
  - [Project Goal](#project-goal)
- [Product Snapshot](#product-snapshot)
    - [Current Product State](#current-product-state)
- [Product Flow](#product-flow)
    - [Current implementation status](#current-implementation-status)
- [Features](#features)
  - [Authentication \& Account Management](#authentication--account-management)
  - [Product Catalog](#product-catalog)
  - [Shopping Cart](#shopping-cart)
  - [Newsletter](#newsletter)
  - [API](#api)
  - [Testing](#testing)
- [Demo](#demo)
  - [Video Example](#video-example)
  - [Image Example](#image-example)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Installation](#installation)
  - [1. Clone the repository](#1-clone-the-repository)
  - [2. Configure environment variables](#2-configure-environment-variables)
  - [3. Build and start the development environment](#3-build-and-start-the-development-environment)
  - [4. Check running containers](#4-check-running-containers)
  - [5. Apply migrations](#5-apply-migrations)
  - [6. Create a superuser](#6-create-a-superuser)
- [Usage](#usage)
  - [Application](#application)
  - [Django Management Commands](#django-management-commands)
  - [Lint and Reformat + Pre-commit (Optional)](#lint-and-reformat--pre-commit-optional)
  - [Documentation](#documentation)
  - [Testing](#testing-1)
    - [Testing Philosophy](#testing-philosophy)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
  - [Architectural Approach](#architectural-approach)
    - [Why a Modular Monolith?](#why-a-modular-monolith)
- [Engineering Highlights](#engineering-highlights)
  - [Database Integrity](#database-integrity)
  - [Concurrency Safety](#concurrency-safety)
  - [Security](#security)
  - [Regression Testing](#regression-testing)
- [ERD / Database Schema](#erd--database-schema)
- [Deployment](#deployment)
    - [Production Deployment](#production-deployment)
- [Known Issues](#known-issues)
- [References and Definitions (Optional)](#references-and-definitions-optional)
  - [Modular Monolith](#modular-monolith)
  - [Data Integrity](#data-integrity)
  - [Concurrency](#concurrency)
  - [Regression Test](#regression-test)
  - [Session-Based Cart](#session-based-cart)
- [License](#license)
- [Support / Contact](#support--contact)
* [Database Schema](#database-schema)

- [Deployment](#deployment)
    - [Production Deployment](#production-deployment)
- [Known Issues](#known-issues)
- [References and Definitions (Optional)](#references-and-definitions-optional)
  - [Modular Monolith](#modular-monolith)
  - [Data Integrity](#data-integrity)
  - [Concurrency](#concurrency)
  - [Regression Test](#regression-test)
  - [Session-Based Cart](#session-based-cart)
- [License](#license)
- [Support / Contact](#support--contact)

---

# Overview

## What is Charkhoneh?

Charkhoneh is a Django-based **online shop** designed around a complete e-commerce workflow.

The application provides the foundation for customers to:

1. Register an account
2. Verify their email address
3. Log in
4. Browse published products
5. Add products to a session-based cart
6. Modify cart quantities
7. Proceed toward checkout
8. Create an order
9. Complete payment
10. Receive order confirmation
11. Manage their orders

The project is currently focused on building and hardening the core platform before completing the remaining order, inventory, and payment components.

---

## Database Schema

The current database schema is documented in:

```text
docs/db-diagram.png
```

![Database Schema](./docs/db-diagram.png)

The schema represents the currently implemented application domain. Future domains such as Orders, Inventory, and Payments will be added when those features are implemented.

---


## Target Users

The primary user is an online-shop customer who needs to:

* Create and manage an account
* Browse available products
* Maintain a shopping cart
* Complete the purchasing process
* Manage their orders

The application also provides administrative foundations for managing products and related shop data.

## Project Goal

The goal is not only to build a functional e-commerce website, but to demonstrate practical software-engineering capabilities through:

* Maintainable Django architecture
* Database integrity
* Secure authentication
* Concurrency-safe operations
* Automated testing
* Containerized development
* Clear separation of application responsibilities
* Incremental implementation of a realistic product

---

# Product Snapshot

| Item                     | Current State                                |
| ------------------------ | -------------------------------------------- |
| Product Type             | E-commerce / Online Shop                     |
| Architecture             | Modular Monolith                             |
| Backend                  | Django 5.2.16                                |
| Database                 | PostgreSQL 15                                |
| API                      | Django REST Framework                        |
| Environment              | Docker / Docker Compose                      |
| Email Development        | smtp4dev                                     |
| Testing                  | pytest / pytest-django                       |
| Authentication           | Custom email-based user model                |
| Cart                     | Session-based                                |
| Current Phase            | Core platform + security/integrity hardening |
| Release Candidate Target | Friday, 13 November 2026                     |

### Current Product State

**Implemented**

* Custom email-based authentication
* User registration
* Email verification
* Login
* Password reset
* Password reset token expiration and single-use behavior
* Password reset token hashing
* Password reset rate limiting
* Product catalog
* Published/unpublished product handling
* Product categories
* Product images
* Product pricing
* Session-based shopping cart
* Add/remove/update cart items
* AJAX cart quantity updates
* Newsletter subscription
* Newsletter email verification
* Newsletter delivery status tracking
* Partial newsletter delivery handling
* HTML sanitization
* REST API foundation
* Automated tests
* Docker development environment
* PostgreSQL integration
* smtp4dev integration
* Django Debug Toolbar
* Regression tests for resolved bugs
* Database integrity and concurrency hardening

**In Progress / Planned**

* Checkout workflow
* Order creation
* Inventory management
* Payment integration
* Order confirmation
* Order management
* Completion of the end-to-end purchasing flow

---

# Product Flow

The intended end-to-end customer journey is:

```text
Register
   ↓
Verify Email
   ↓
Login
   ↓
Browse Products
   ↓
Add to Cart
   ↓
Update Cart
   ↓
Checkout
   ↓
Create Order
   ↓
Payment
   ↓
Confirmation
   ↓
Order Management
```

### Current implementation status

```text
Register              ✅
Verify Email          ✅
Login                 ✅
Browse Products       ✅
Add to Cart           ✅
Update Cart           ✅
Checkout              🚧
Create Order          🚧
Payment               🚧
Confirmation          🚧
Order Management      🚧
```

The remaining purchasing stages are intentionally separated from the currently implemented catalog and cart functionality so that order, inventory, and payment logic can be introduced with appropriate transaction and integrity guarantees.

---

# Features

## Authentication & Account Management

* Custom email-based user authentication
* Registration
* Login
* Email verification
* Password reset
* Expiring password reset tokens
* Single-use password reset tokens
* Password reset token hashing
* Password validation
* Password reset rate limiting
* Secure authentication-related flows

## Product Catalog

* Product management
* Product categories
* Product images
* Product pricing
* Published/unpublished products
* Prevention of unpublished products appearing in customer-facing queries

## Shopping Cart

* Session-based cart
* Add products to cart
* Remove products from cart
* Update product quantities
* AJAX quantity updates
* Cart validation
* Database-aware product handling

## Newsletter

* Newsletter subscription
* Email verification
* Delivery status tracking
* Successful / failed / partially successful delivery states
* HTML sanitization

## API

The project includes Django REST Framework as the foundation for exposing application functionality through APIs.

The API layer is being developed alongside the web application rather than as a completely separate backend.

## Testing

The project uses automated testing to verify:

* Authentication behavior
* Password reset behavior
* Cart behavior
* Product visibility
* Newsletter behavior
* Security-related behavior
* Concurrency-sensitive behavior
* Regression cases

---

# Demo

## Video Example

> Add project demonstration video here.

```text
Coming soon
```

## Image Example

> Add application screenshots here.

```text
Coming soon
```

---

# Requirements

The project currently uses:

* Python 3.12+
* Django 5.2.16
* PostgreSQL 15
* Docker
* Docker Compose
* Django REST Framework
* pytest
* pytest-django
* smtp4dev

For the recommended development workflow, Docker should be available on the host machine.

---

# Configuration

Development configuration is stored separately from application source code.

Example environment file:

```text
envs/dev/django/.env.sample
```

Create the development environment file from the sample:

```bash
cp envs/dev/django/.env.sample envs/dev/django/.env
```

Then configure the required environment variables.

Typical configuration includes:

* Django secret key
* Debug configuration
* Allowed hosts
* Database connection
* Email configuration
* Application-specific settings

Sensitive credentials should never be committed to the repository.

---

# Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd CharkhoneWebShop-DjangoApplication
```

## 2. Configure environment variables

```bash
cp envs/dev/django/.env.sample envs/dev/django/.env
```

Edit the `.env` file according to your local environment.

## 3. Build and start the development environment

```bash
docker compose up --build -d
```

## 4. Check running containers

```bash
docker compose ps
```

## 5. Apply migrations

```bash
docker compose exec django python manage.py migrate
```

## 6. Create a superuser

```bash
docker compose exec django python manage.py createsuperuser
```

The application can now be accessed through the configured development server.

---

# Usage

## Application

Start the development environment:

```bash
docker compose up -d
```

Stop it:

```bash
docker compose down
```

Rebuild after dependency or Docker configuration changes:

```bash
docker compose up --build -d
```

## Django Management Commands

Run Django commands inside the application container:

```bash
docker compose exec django python manage.py <command>
```

For example:

```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
```

---

## Lint and Reformat + Pre-commit (Optional)

Formatting, linting, and pre-commit tooling can be added to the development workflow as the project evolves.

The current priority is application correctness, automated testing, database integrity, and maintainable implementation.

---

## Documentation

Project documentation is maintained alongside the source code.

The `docs/` directory is intended for documentation that is too detailed for the main README, including technical decisions, implementation notes, and engineering documentation.

The README intentionally focuses on the product, architecture, current state, setup, and development workflow.

---

## Testing

The project uses:

* `pytest`
* `pytest-django`

Run the complete test suite with:

```bash
docker compose exec django pytest
```

For a specific test:

```bash
docker compose exec django pytest path/to/test_file.py
```

For verbose output:

```bash
docker compose exec django pytest -v
```

### Testing Philosophy

Tests are treated as part of the implementation rather than as an afterthought.

When a bug is fixed, the corresponding regression behavior should be covered by an automated test whenever practical.

Particular attention is given to security-sensitive and concurrency-sensitive operations.

---

# Project Structure

The project follows a Django modular-monolith structure:

```text
CharkhoneApplication-django/
│
├── accounts/
│   ├── migrations/
│   ├── templates/
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── ...
│
├── cart/
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── ...
│
├── shop/
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── ...
│
├── website/
│   ├── templates/
│   ├── static/
│   └── ...
│
├── core/
│   ├── settings/
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── dockerfiles/
│   └── dev/
│       └── django/
│
├── envs/
│   └── dev/
│       └── django/
│
├── postgres/
│
├── docs/
│
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
├── README.md
└── ...
```

The exact structure may evolve as additional domain functionality such as orders, inventory, and payments is implemented.

---

# Architecture

## Architectural Approach

Charkhoneh currently follows a **Modular Monolith** architecture.

The application is deployed as a single Django application while domain responsibilities are separated into Django apps.

```text
                    ┌─────────────────────┐
                    │      Client         │
                    │  Browser / API      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Django        │
                    │   Application       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │ Accounts │     │   Shop   │     │   Cart   │
        └──────────┘     └──────────┘     └──────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PostgreSQL       │
                    └─────────────────────┘
```

### Why a Modular Monolith?

The project does not currently require the operational and architectural complexity of microservices.

A modular monolith provides:

* Clear domain boundaries
* Simpler deployment
* Easier local development
* Straightforward transactions
* Lower infrastructure complexity
* A foundation that can evolve as product requirements grow

The architecture can be decomposed further if future requirements justify it.

---

# Engineering Highlights

The project emphasizes engineering correctness in addition to feature development.

## Database Integrity

Database-level constraints and application-level validation are used together where appropriate.

The goal is to prevent invalid states rather than relying exclusively on application code.

## Concurrency Safety

Concurrency-sensitive operations are designed to avoid race conditions.

For example, password reset token consumption is protected so that the same single-use token cannot be successfully consumed by multiple concurrent requests.

## Security

Security-related work includes:

* Password validation
* Secure password reset flow
* Token expiration
* Single-use tokens
* Token hashing
* Rate limiting
* HTML sanitization
* Protection against exposing unpublished products

## Regression Testing

Important bugs are converted into regression tests so that previously resolved problems are less likely to return.

---

# ERD / Database Schema

The following schema represents the **currently implemented domain**, not the final planned e-commerce model.

Order, inventory, and payment entities are intentionally excluded because they have not yet been implemented.

```text
┌──────────────────────┐
│        User          │
├──────────────────────┤
│ id                   │
│ email                │
│ password             │
│ is_active            │
│ ...                  │
└──────────┬───────────┘
           │
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
┌──────────────────────┐   ┌──────────────────────┐
│ Email Verification   │   │ Password Reset       │
│ / Verification Data  │   │ Token Data           │
└──────────────────────┘   └──────────────────────┘


┌──────────────────────┐
│       Category       │
├──────────────────────┤
│ id                   │
│ name                 │
│ ...                  │
└──────────┬───────────┘
           │
           │ 1:N
           ▼
┌──────────────────────┐
│       Product        │
├──────────────────────┤
│ id                   │
│ category             │
│ name                 │
│ price                │
│ published            │
│ ...                  │
└──────────┬───────────┘
           │
           │
           ▼
┌──────────────────────┐
│    Product Image     │
├──────────────────────┤
│ id                   │
│ product              │
│ image                │
│ ...                  │
└──────────────────────┘


┌──────────────────────┐
│   Session Cart       │
│   / Cart Data        │
├──────────────────────┤
│ product reference    │
│ quantity             │
└──────────────────────┘


┌──────────────────────┐
│ Newsletter Subscriber│
├──────────────────────┤
│ id                   │
│ email                │
│ verification state   │
│ delivery status      │
│ ...                  │
└──────────────────────┘
```

The ERD will be expanded when the Order, Inventory, and Payment domains are implemented.

---

# Deployment

The project currently provides a Docker-based development environment.

Development services include:

```text
Django
   │
   ├── PostgreSQL 15
   │
   └── smtp4dev
```

### Production Deployment

Production deployment is not yet considered the final stage of the project.

Before production deployment, the application should be hardened around areas such as:

* Production settings
* Secret management
* HTTPS
* Secure cookies
* Database backups
* Static/media file serving
* Logging
* Monitoring
* Error reporting
* Email provider configuration
* Database connection management
* Container and infrastructure configuration

The current Docker configuration is primarily intended for development and local engineering workflows.

---

# Known Issues

The following major product areas are not yet complete:

* Checkout
* Order creation
* Inventory management
* Payment integration
* Order confirmation
* Order management

These are part of the remaining product roadmap and should not be considered implemented functionality.

Minor bugs and regressions are tracked and resolved through the project's engineering workflow.

---

# References and Definitions (Optional)

## Modular Monolith

A single deployable application divided internally into clearly defined modules or domains.

## Data Integrity

The use of constraints, validation, transactions, and correct application behavior to prevent invalid database states.

## Concurrency

The behavior of the application when multiple requests attempt to modify or consume the same resource at approximately the same time.

## Regression Test

An automated test that verifies a previously fixed bug does not return.

## Session-Based Cart

A shopping cart whose current state is associated with the user's session rather than requiring a persistent order record.

---

# License

This project is intended as a software-engineering portfolio project.

Add the repository's applicable license here when the project's licensing decision is finalized.

---

# Support / Contact

For questions, feedback, or collaboration related to the project, use the repository's issue tracker or contact the project owner through the associated repository profile.
