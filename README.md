# 🏭 FactoryIQ — Multi-Tenant Manufacturing ERP

> A production-grade, multi-tenant ERP system for garment and discrete manufacturing. Built with **FastAPI**, **PostgreSQL**, **Next.js 14**, and an integrated **AI conversational assistant**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Multi-Tenancy Model](#multi-tenancy-model)
- [Running Tests](#running-tests)
- [Roadmap](#roadmap)

---

## Overview

FactoryIQ is a full-stack manufacturing ERP designed to manage the complete production lifecycle — from raw material procurement and inventory tracking, through production scheduling and shop floor execution, to sales order fulfilment and AI-assisted decision making.

It supports multiple tenants on a single deployment, with two isolation strategies:
- **Standard RLS** — shared tables with PostgreSQL Row-Level Security
- **Premium Schema** — fully private PostgreSQL schema per enterprise tenant

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        Browser / Client                     │
│                   Next.js 14 (App Router)                   │
└─────────────────────────────┬──────────────────────────────┘
                              │  HTTP/REST
┌─────────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend  (Port 8000)               │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Auth   │  │Inventory │  │Production│  │   Sales  │  │
│  │  + RLS   │  │+ Transfers│  │+ Gantt   │  │+ Feasib. │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐ │
│  │Purchasing│  │   BOM    │  │  AI Assistant (Gemini)   │ │
│  │  + POs   │  │ + MRP    │  │  Conversational Actions   │ │
│  └──────────┘  └──────────┘  └──────────────────────────┘ │
└─────────────────────────────┬──────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────┐
│                PostgreSQL 15  (Port 5432)                   │
│                                                             │
│  public schema (global tenants directory)                   │
│  tenant_<subdomain> schema (premium isolated tenants)       │
└────────────────────────────────────────────────────────────┘
```

---

## Features

### ✅ Multi-Tenancy
- **RLS-based isolation** — PostgreSQL Row-Level Security enforced at DB policy level for standard tenants
- **Schema-based isolation** — Dynamic private schema provisioning (`tenant_<subdomain>`) for enterprise tenants with full table namespace separation
- **Automatic schema migration** — Tables created inside tenant schema on sign-up with topological DDL ordering

### ✅ Inventory Management
- Multi-warehouse component stock tracking (`on_hand`, `reserved`, `allocated`, `wip`, `damaged`, `in_transit`)
- Stock adjustments with ledger-backed audit trail (`stock_movements`)
- **Multi-warehouse stock transfers** — Pessimistic row locking + double-entry `transfer_out` / `transfer_in` movements
- Soft reservations per sales order / production order

### ✅ Bill of Materials (BOM)
- Versioned, multi-level BOM headers and line items
- Scrap percentage per component line
- BOM explosion during production scheduling

### ✅ Sales Orders & Feasibility
- Sales order lines with ordered/produced quantity tracking
- **Real-time feasibility check** — BOM explosion against available warehouse stock with bottleneck identification
- Production readiness percentage per order

### ✅ Production Scheduling
- Production order creation with automatic BOM-driven material reservation
- Work order stages: `cutting → stitching → finishing → packing`
- **Advanced scheduling** — Lead-time chaining (8h, 16h, 8h, 4h per stage)
- `actual_start` / `actual_end` stamped on stage transitions for schedule adherence tracking
- **Gantt API** — `GET /production/schedule` returns flat work order list for Gantt chart rendering

### ✅ Purchasing
- Supplier management
- Purchase order creation with line items and expected delivery dates
- PO receive flow — triggers GRN stock movements into selected warehouse

### ✅ AI Conversational Assistant
- Natural language queries answered against live ERP data
- **Conversational actions** — AI can create purchase orders (`create_po`) and transition work order stages (`transition_work_order`) from chat commands
- JWT identity-aware — AI actions respect RLS tenant boundaries

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), asyncpg |
| **Database** | PostgreSQL 15 with Row-Level Security |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **AI** | Google Gemini (via `google-generativeai`) |
| **Auth** | JWT (python-jose), bcrypt password hashing |
| **Testing** | pytest, pytest-asyncio, aiosqlite (in-memory) |
| **Infra** | Docker Compose (DB + Redis) |

---

## Project Structure

```
FactoryIQ/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings
│   │   │   └── tenancy.py            # DB session + search_path switcher
│   │   ├── db/
│   │   │   ├── session.py            # Async engine + session factory
│   │   │   └── init_db.py            # Table creation + RLS policies + seed roles
│   │   ├── modules/
│   │   │   ├── auth/                 # Tenant registration, login, JWT, RLS
│   │   │   ├── bom/                  # Products, components, BOM headers/lines
│   │   │   ├── inventory/            # Stock balances, adjustments, transfers, reservations
│   │   │   ├── sales/                # Sales orders, lines, feasibility engine
│   │   │   ├── production/           # Production orders, work orders, Gantt scheduling
│   │   │   ├── purchasing/           # Suppliers, purchase orders, GRN receive
│   │   │   └── ai_assistant/         # Gemini-powered ERP chat with action intents
│   │   └── main.py
│   └── web/                          # Next.js 14 frontend
│       └── app/
│           └── page.tsx              # Main ERP dashboard
├── tests/
│   ├── unit/                         # Pure logic unit tests (no DB)
│   │   ├── test_feasibility.py
│   │   ├── test_production_scheduling.py
│   │   └── test_ai_actions.py
│   └── integration/                  # Live PostgreSQL integration tests
│       ├── test_schema_isolation.py
│       └── test_inventory_transfers.py
└── infra/
    └── docker-compose.yml
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 15
- (Optional) Docker

### 1. Clone & Backend Setup

```bash
git clone https://github.com/annjan777/airflow-taxi-etl.git FactoryIQ
cd FactoryIQ

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r apps/api/requirements.txt

# Set up PostgreSQL database
createdb factoryiq

# Initialize tables, RLS policies, and seed roles
PYTHONPATH=apps/api python apps/api/db/init_db.py
```

### 2. Start the API Server

```bash
PYTHONPATH=apps/api uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start the Frontend

```bash
cd apps/web
npm install
npm run dev
```

Frontend available at: [http://localhost:3000](http://localhost:3000)

### 4. Environment Variables

Create `apps/api/.env` (or rely on defaults in `config.py`):

```env
DATABASE_URL=postgresql+asyncpg://factoryiq_user:factoryiq_pass@localhost:5432/factoryiq
SYNC_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/factoryiq
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register-tenant` | Register a new tenant + admin user |
| `POST` | `/api/v1/auth/login` | Login and get JWT token |
| `GET` | `/api/v1/inventory/balances` | List all inventory balances |
| `POST` | `/api/v1/inventory/adjustments` | Stock adjustment (GRN/issue/scrap) |
| `POST` | `/api/v1/inventory/transfers` | Transfer stock between warehouses |
| `GET` | `/api/v1/sales-orders/{id}/feasibility` | Check production feasibility |
| `POST` | `/api/v1/production/runs` | Schedule a production run |
| `GET` | `/api/v1/production/schedule` | Gantt schedule (all work orders) |
| `POST` | `/api/v1/production/work-orders/{id}/transition` | Advance work order stage |
| `POST` | `/api/v1/purchasing/pos` | Create a purchase order |
| `POST` | `/api/v1/purchasing/pos/{id}/receive` | Receive PO into warehouse |
| `POST` | `/api/v1/ai/query` | AI conversational ERP query |

Full interactive docs: `http://localhost:8000/docs`

---

## Multi-Tenancy Model

FactoryIQ supports two isolation modes selectable at tenant registration:

| Mode | `isolation_mode` | Data Separation | Use Case |
|---|---|---|---|
| **Standard** | `rls` | PostgreSQL Row-Level Security on `tenant_id` | SME / startup tenants |
| **Premium** | `schema` | Private PostgreSQL schema per tenant | Enterprise / compliance tenants |

### How Schema Isolation Works

1. On registration, a `CREATE SCHEMA "tenant_<subdomain>"` is executed
2. All application tables are provisioned inside the private schema
3. At runtime, the DB session connection sets `SET search_path TO "tenant_<subdomain>", public`
4. Queries automatically resolve to the tenant's private tables

---

## Running Tests

```bash
# Unit tests (no DB required)
./venv/bin/pytest tests/unit/ -v

# Integration tests (requires live PostgreSQL)
PYTHONPATH=apps/api ./venv/bin/pytest tests/integration/ -v -s
```

### Test Coverage

| Test File | What it covers |
|---|---|
| `test_feasibility.py` | BOM explosion, bottleneck detection, readiness % |
| `test_production_scheduling.py` | Lead-time chaining, actual timestamps, Gantt structure |
| `test_ai_actions.py` | `create_po` and `transition_work_order` AI intents |
| `test_schema_isolation.py` | Dynamic schema provisioning, table creation, RLS |
| `test_inventory_transfers.py` | Multi-warehouse transfers, ledger audit, over-transfer validation |

---

## Roadmap

- [x] Multi-tenant RLS isolation
- [x] Premium schema-based tenant isolation
- [x] Multi-warehouse stock transfers
- [x] Advanced production scheduling (Gantt + lead times)
- [ ] MRP (Material Requirements Planning) engine
- [ ] Admin portal (tenant management dashboard)
- [ ] Email / webhook notifications
- [ ] Real-time websocket updates (production floor live view)
- [ ] Barcode / QR scanning support

---

## License

MIT © FactoryIQ Contributors
