# Claude Context: Salehi Dialer Admin Panel

This document provides comprehensive context about the Salehi Dialer Admin Panel for AI assistants working on this codebase.

---

## Project Overview

**Salehi Dialer Admin Panel** is a production-grade call center management system for outbound dialing campaigns in Persian/Iranian call centers. It manages phone number queues, call scheduling, user/agent management, and provides APIs for external dialer system integration.

**Current Status:** Multi-company architecture fully implemented and deployed on `salehi` branch (local). Companies: salehi (company_id=1), saeid (company_id=2), agrad (company_id=3).

**Total Codebase:** ~4,100 lines of application code (excluding tests, configs, dependencies)

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12)
- **ORM:** SQLAlchemy 2.0 with declarative models
- **Database:** PostgreSQL with custom enum types
- **Authentication:** JWT tokens (1-day expiry) with bcrypt password hashing
- **Validation:** Pydantic v2 for request/response schemas
- **Server:** Uvicorn/Gunicorn ASGI servers
- **Migrations:** Alembic for database schema versioning
- **Testing:** Pytest
- **Lines of Code:** ~2,237 lines

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS (RTL layout for Persian)
- **Routing:** React Router v6
- **HTTP Client:** Axios with JWT interceptor
- **Charts:** Chart.js with react-chartjs-2
- **Date Handling:** Day.js with jalaliday plugin (Jalali/Persian calendar)
- **State Management:** React Context API for authentication
- **Lines of Code:** ~1,868 lines

### Deployment
- **Automation:** Ansible playbooks with roles
- **Web Server:** Nginx reverse proxy
- **Process Manager:** systemd
- **SSL/TLS:** Arvan CDN integration
- **Timezone:** All operations use Asia/Tehran

---

## Architecture

### Project Structure

```
salehi-panel/
├── backend/
│   ├── alembic/                    # Database migrations
│   │   ├── versions/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_roles_agents_and_statuses.py
│   │   │   └── 0003_superuser_first_admin.py
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── app/
│   │   ├── api/                    # FastAPI routers (343 lines)
│   │   │   ├── auth.py            # Login, /me, profile
│   │   │   ├── admins.py          # User CRUD (admin only)
│   │   │   ├── schedule.py        # Schedule config & windows
│   │   │   ├── numbers.py         # Phone number management
│   │   │   ├── dialer.py          # Dialer-facing APIs
│   │   │   ├── stats.py           # Dashboard statistics
│   │   │   └── deps.py            # Auth guards (DI)
│   │   ├── core/                   # Config, DB, security (270 lines)
│   │   │   ├── config.py          # Settings from .env
│   │   │   ├── database.py        # SQLAlchemy setup
│   │   │   └── security.py        # JWT, bcrypt
│   │   ├── models/                 # SQLAlchemy ORM
│   │   │   ├── user.py            # AdminUser (with company_id, is_superuser)
│   │   │   ├── phone_number.py    # PhoneNumber (numbers table), CallStatus, GlobalStatus
│   │   │   ├── call_result.py     # CallResult (call_results table, per-company)
│   │   │   ├── company.py         # Company
│   │   │   ├── scenario.py        # Scenario (per-company)
│   │   │   ├── outbound_line.py   # OutboundLine (per-company)
│   │   │   ├── schedule_config.py # ScheduleConfig (per-company singleton)
│   │   │   ├── schedule_window.py # ScheduleWindow
│   │   │   └── dialer_batch.py
│   │   ├── schemas/                # Pydantic models
│   │   │   ├── auth.py
│   │   │   ├── admin.py
│   │   │   ├── phone_number.py    # PhoneNumberOut has virtual fields populated from call_results
│   │   │   ├── schedule.py
│   │   │   ├── dialer.py
│   │   │   └── stats.py
│   │   ├── services/               # Business logic (1,168 lines)
│   │   │   ├── auth_service.py    # Auth, user mgmt
│   │   │   ├── phone_service.py   # Validation, bulk ops
│   │   │   ├── schedule_service.py # Time window eval
│   │   │   ├── dialer_service.py  # Batch dispatch, results
│   │   │   └── stats_service.py   # Aggregations
│   │   ├── utils/
│   │   │   └── create_admin.py    # CLI tool
│   │   └── main.py                 # FastAPI app init
│   ├── tests/                      # pytest
│   │   ├── conftest.py
│   │   ├── test_permissions.py
│   │   └── test_phone_validation.py
│   └── requirements.txt            # 14 packages
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts           # Axios + JWT
│   │   ├── components/
│   │   │   ├── Layout.tsx          # Main layout (RTL)
│   │   │   └── ProtectedRoute.tsx  # Role guards
│   │   ├── hooks/
│   │   │   └── useAuth.tsx         # Auth context
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Charts & stats
│   │   │   ├── Numbers.tsx         # Number mgmt
│   │   │   ├── Schedule.tsx        # Time windows
│   │   │   ├── AdminUsers.tsx      # User CRUD
│   │   │   ├── Profile.tsx         # Self-service
│   │   │   └── Login.tsx           # Auth
│   │   ├── styles/
│   │   ├── App.tsx                 # Router
│   │   └── main.tsx                # Entry
│   ├── dist/                       # Build output
│   ├── package.json                # 12 deps, 6 devDeps
│   ├── vite.config.ts
│   └── tailwind.config.js
├── deploy/
│   └── ansible/
│       ├── group_vars/
│       │   ├── prod.yml            # Agrad config (ignored)
│       │   ├── prod_salehi.yml     # Salehi config (ignored)
│       │   └── prod.sample.yml     # Template
│       ├── roles/
│       │   ├── backend/            # Gunicorn systemd
│       │   ├── frontend/           # npm build
│       │   ├── nginx/              # Reverse proxy
│       │   ├── postgres/           # DB setup
│       │   ├── common/             # System packages
│       │   └── ssl_arvan/          # SSL certs
│       ├── inventory.ini
│       └── playbook.yml
├── docs/
│   └── callcenter_agent.md         # Dialer integration
├── README.md                        # Main docs
└── claude.md                        # This file
```

---

## Database Schema

### Entity Relationship Diagram

```
AdminUser (1) ----< (M) PhoneNumber.assigned_agent_id
AdminUser (1) ----< (M) CallAttempt.agent_id

PhoneNumber (1) ----< (M) CallAttempt.phone_number_id

ScheduleConfig (singleton, id=1)
ScheduleWindow (multiple per weekday)

DialerBatch (audit log, no FK relations)
```

### Tables

#### 1. admin_users
User and agent management table.

**Fields:**
- `id` (Integer, PK, auto-increment)
- `username` (String, unique, not null)
- `password_hash` (String, not null) - bcrypt hash
- `is_superuser` (Boolean, default False) - bypass all restrictions
- `role` (Enum: ADMIN/AGENT, default ADMIN)
- `is_active` (Boolean, default True) - soft delete
- `first_name` (String, nullable)
- `last_name` (String, nullable)
- `phone_number` (String, unique, nullable) - for agent call routing
- `created_at` (DateTime, timezone-aware)
- `updated_at` (DateTime, timezone-aware)

**Constraints:**
- Username unique
- Phone number unique (if provided)
- First created admin becomes superuser automatically

**Relationships:**
- One-to-many with PhoneNumber (assigned_agent_id)
- One-to-many with CallAttempt (agent_id)

#### 2. numbers (formerly phone_numbers) — SHARED across all companies

**Fields:**
- `id` (Integer, PK, auto-increment)
- `phone_number` (String, unique, not null) - Iranian format 09xxxxxxxxx
- `global_status` (Enum: GlobalStatus, default ACTIVE) - affects ALL companies
- `last_called_at` (DateTime, nullable) - global cooldown timestamp
- `last_called_company_id` (Integer, FK to companies, nullable)
- `assigned_at` (DateTime, nullable) - when sent to dialer batch
- `assigned_batch_id` (String, nullable) - UUID for audit

**No per-company fields** — status, attempts, agent are in `call_results`.

**GlobalStatus Enum:**
- `ACTIVE` - callable by any company (subject to per-company dedup)
- `POWER_OFF` - globally blocked (phone off)
- `COMPLAINED` - globally blocked (complaint registered)

**CallStatus Enum** (stored in call_results, not numbers):
- `IN_QUEUE` - no call_result exists for this company (virtual default)
- `MISSED`, `CONNECTED`, `FAILED`, `NOT_INTERESTED`, `HANGUP`
- `DISCONNECTED`, `BUSY`, `POWER_OFF`, `BANNED`, `UNKNOWN`
- `INBOUND_CALL`, `COMPLAINED`

**Status Mutability Rules (applied to call_results status):**
- **Mutable**: IN_QUEUE, MISSED, BUSY, POWER_OFF, BANNED
- **Immutable**: CONNECTED, FAILED, NOT_INTERESTED, HANGUP, DISCONNECTED, UNKNOWN
- Superusers bypass these restrictions

#### 3. call_results (formerly call_attempts) — per-company call history

**Fields:**
- `id` (Integer, PK, auto-increment) — **use max(id) to find latest row, NOT max(attempted_at)**
- `phone_number_id` (Integer, FK to numbers, not null)
- `company_id` (Integer, FK to companies, not null)
- `scenario_id` (Integer, FK to scenarios, nullable)
- `outbound_line_id` (Integer, FK to outbound_lines, nullable)
- `status` (String: CallStatus, not null)
- `reason` (String, nullable)
- `user_message` (String, nullable) - customer feedback
- `agent_id` (Integer, FK to admin_users, nullable)
- `attempted_at` (DateTime, not null, timezone-aware)

**Indexes:**
- `(company_id, attempted_at)`
- `(phone_number_id, company_id)`
- `agent_id`

**IMPORTANT:** Multiple rows can share the same `attempted_at` timestamp (migration artifact).
Always use `max(id)` — NOT `max(attempted_at)` — to identify the latest call result.

#### 4. schedule_configs
Global scheduling settings (singleton pattern).

**Fields:**
- `id` (Integer, PK, always 1)
- `skip_holidays` (Boolean, default from .env)
- `enabled` (Boolean, default True) - master on/off switch
- `disabled_by_dialer` (Boolean, default False) - tracks auto-shutdown
- `version` (Integer, default 1) - increments on config changes
- `updated_at` (DateTime, timezone-aware)

**Purpose:** Single-row configuration table controlling dialer behavior.

#### 5. schedule_windows
Time windows when calling is allowed.

**Fields:**
- `id` (Integer, PK, auto-increment)
- `day_of_week` (Integer, 0-6) - 0=Saturday, 6=Friday (Persian week)
- `start_time` (Time, not null) - HH:MM:SS
- `end_time` (Time, not null) - HH:MM:SS

**Indexes:**
- day_of_week

**Constraints:**
- start_time < end_time
- Multiple windows per day allowed

#### 6. dialer_batches
Batch dispatch audit log.

**Fields:**
- `id` (String, PK) - UUID hex string
- `requested_size` (Integer, not null)
- `returned_size` (Integer, not null)
- `created_at` (DateTime, timezone-aware)

**Purpose:** Tracks every batch dispatch for audit/debugging.

---

## API Endpoints

### Authentication

#### POST /api/auth/login
Login and get JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### GET /api/auth/me
Get current user profile (requires JWT).

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "role": "ADMIN",
  "is_superuser": true,
  "is_active": true,
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "phone_number": "09123456789",
  "created_at": "2024-01-01T10:00:00+03:30",
  "updated_at": "2024-01-01T10:00:00+03:30"
}
```

#### PUT /api/auth/me
Update own profile (requires JWT).

**Request:**
```json
{
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "current_password": "old",
  "new_password": "new" // optional
}
```

### Admin User Management (ADMIN only)

#### GET /api/admins
List all users (pagination supported).

**Query params:** `skip`, `limit`

#### POST /api/admins
Create new user/agent.

**Request:**
```json
{
  "username": "agent1",
  "password": "pass123",
  "role": "AGENT",
  "first_name": "Hassan",
  "last_name": "Hosseini",
  "phone_number": "09121111111"
}
```

#### PUT /api/admins/{id}
Update user.

#### DELETE /api/admins/{id}
Delete user (cannot delete superuser).

### Phone Number Management

#### GET /api/numbers
List numbers with filtering and pagination.

**Query params:**
- `company` - company name (slug) for superusers to view another company's data
- `status` - filter by CallStatus (applied per-company via call_results)
- `search` - search phone number
- `start_date` - filter last_called_at >= (ISO8601)
- `end_date` - filter last_called_at <= (ISO8601)
- `sort_by` - created_at | last_attempt_at | status (last two use call_results subquery)
- `sort_order` - asc | desc
- `skip` - pagination offset
- `limit` - page size (default 50)

**Company resolution:** If `company` param is given and user is superuser, data is shown for that company. Otherwise uses `current_user.company_id`.

#### GET /api/numbers/stats
Count total numbers for current filter.

**Response:**
```json
{
  "total": 1523
}
```

#### POST /api/numbers
Add numbers manually (comma/newline separated).

**Request:**
```json
{
  "numbers": "09123456789,09121111111\n09122222222"
}
```

**Response:**
```json
{
  "added": 3,
  "duplicates": 0,
  "invalid": 0
}
```

#### POST /api/numbers/upload
Upload CSV/XLSX file (first column only).

**Form data:** `file` (multipart/form-data)

**Response:** Same as POST /api/numbers

#### PUT /api/numbers/{id}/status
Update single number status.

**Request:**
```json
{
  "status": "CONNECTED"
}
```

**Restrictions:**
- Agents: only assigned numbers, mutable statuses only
- Admins: all numbers, mutable statuses only
- Superusers: all numbers, all statuses

#### GET /api/numbers/stats
Count numbers matching filters. Accepts same `company` + `status` params as list endpoint.

#### POST /api/numbers/{id}/reset
Reset number for this company: **deletes all call_results for this company** so dialer can re-call it. Also clears `assigned_at`/`assigned_batch_id`.

#### DELETE /api/numbers/{id}
Delete number (mutable statuses only, unless superuser).

#### POST /api/numbers/bulk
Bulk operations on numbers.

**Request (with specific IDs):**
```json
{
  "action": "update_status",
  "status": "CONNECTED",
  "ids": [1, 2, 3]
}
```

**Request (select all filtered):**
```json
{
  "action": "delete",
  "select_all": true,
  "status": "IN_QUEUE",
  "search": "0912",
  "excluded_ids": [5, 10]
}
```

**Actions:** `update_status`, `reset`, `delete`

**Response:**
```json
{
  "affected": 25
}
```

#### POST /api/numbers/export
Export numbers to Excel (XLSX).

**Request:** Same as bulk (ids OR select_all with filters)

**Response:** Streaming XLSX file

**Columns:** ID, Phone, Status, Attempts, Last Attempt, Last Status Change, Agent Name, Agent Phone, User Message

### Schedule Management (ADMIN only)

#### GET /api/schedule
Get schedule config and windows.

**Response:**
```json
{
  "config": {
    "id": 1,
    "skip_holidays": true,
    "enabled": true,
    "disabled_by_dialer": false,
    "version": 3,
    "updated_at": "..."
  },
  "windows": [
    {
      "id": 1,
      "day_of_week": 0,
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

#### PUT /api/schedule
Update schedule (increments version).

**Request:**
```json
{
  "skip_holidays": true,
  "enabled": true,
  "windows": [
    {
      "day_of_week": 0,
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

### Dashboard Statistics (ADMIN only)

#### GET /api/stats/numbers-summary
Number distribution by status.

**Query params:** `timeframe` (all | today | 1h | 3h | 7d | 30d)

**Response:**
```json
{
  "total": 1000,
  "by_status": [
    {
      "status": "IN_QUEUE",
      "count": 500,
      "percentage": 50.0
    }
  ]
}
```

#### GET /api/stats/attempts-summary
Call attempts summary.

**Query params:** `timeframe` (same as above)

**Response:**
```json
{
  "total": 2500,
  "by_status": [
    {
      "status": "CONNECTED",
      "count": 1200,
      "percentage": 48.0
    }
  ]
}
```

#### GET /api/stats/attempt-trend
Time-series data for charts.

**Query params:**
- `span` - 6h | 24h | 7d | 30d
- `granularity` - hourly | daily

**Response:**
```json
{
  "buckets": [
    {
      "timestamp": "2024-01-01T09:00:00+03:30",
      "total": 100,
      "by_status": [
        {
          "status": "CONNECTED",
          "count": 50,
          "percentage": 50.0
        }
      ]
    }
  ]
}
```

### Dialer API (Bearer DIALER_TOKEN)

#### GET /api/dialer/next-batch?size=100
Fetch next batch of numbers to call.

**Headers:** `Authorization: Bearer <DIALER_TOKEN>`

**Response (allowed):**
```json
{
  "call_allowed": true,
  "timezone": "Asia/Tehran",
  "server_time": "2024-01-01T10:00:00+03:30",
  "schedule_version": 3,
  "active_agents": [
    {
      "id": 5,
      "full_name": "Ali Ahmadi",
      "phone_number": "09123456789"
    }
  ],
  "batch": {
    "batch_id": "abc123...",
    "size_requested": 100,
    "size_returned": 73,
    "numbers": [
      {
        "id": 1,
        "phone_number": "09123456789"
      }
    ]
  }
}
```

**Response (blocked):**
```json
{
  "call_allowed": false,
  "timezone": "Asia/Tehran",
  "server_time": "2024-01-01T23:00:00+03:30",
  "schedule_version": 3,
  "reason": "outside_allowed_time_window",
  "retry_after_seconds": 900
}
```

**Reasons:** `insufficient_funds`, `disabled`, `holiday`, `no_window`, `outside_allowed_time_window`

**Retry hints:**
- `short_retry_seconds`: 300s (`insufficient_funds`, `disabled`)
- `long_retry_seconds`: 900s (`holiday`, `no_window`, `outside_allowed_time_window`)

**Batch assignment logic:**
1. Check schedule (enabled, holidays, time windows)
2. Unlock stale assignments (>60min timeout)
3. Filter: `global_status=ACTIVE`, `assigned_at IS NULL`, `NOT EXISTS(call_results for this company)`, cooldown OK
4. SELECT FOR UPDATE SKIP LOCKED (concurrent-safe) — uses NOT EXISTS (not LEFT JOIN) for PG compatibility
5. Assign batch_id and timestamp
6. Create DialerBatch audit record
7. Return active agents roster

#### POST /api/dialer/report-result
Report call outcome.

**Headers:** `Authorization: Bearer <DIALER_TOKEN>`

**Request:**
```json
{
  "number_id": 1,
  "phone_number": "09123456789",
  "status": "CONNECTED",
  "reason": "answered after 3 rings",
  "attempted_at": "2024-01-01T10:05:00+03:30",
  "call_allowed": false,
  "agent_id": 5,
  "agent_phone": "09121111111",
  "user_message": "Customer interested in product X"
}
```

**Fields:**
- `number_id` - optional if phone provided
- `phone_number` - required
- `status` - CallStatus enum
- `reason` - optional description
- `attempted_at` - ISO8601 timestamp with timezone
- `call_allowed` - optional, toggles global enable flag
- `agent_id` - optional, assigns to agent
- `agent_phone` - fallback if id missing
- `user_message` - customer feedback/notes

**Processing:**
1. Find/create PhoneNumber record
2. Resolve agent (by ID or phone lookup)
3. Update PhoneNumber: status, total_attempts++, timestamps, assigned_agent_id, last_user_message
4. Clear batch assignment (assigned_at, assigned_batch_id)
5. Create CallAttempt record
6. Update global enabled flag if call_allowed provided
7. Increment schedule version if config changed

**Safety features:**
- Auto-create numbers if missing (handles race conditions)
- Row-level locking prevents conflicts
- IntegrityError handling for duplicates

---

## Business Logic & Workflows

### User Management

**Superuser creation:**
- First admin created via CLI becomes superuser automatically
- Migration 0003 applies this to existing first admin
- Superuser cannot be deleted or deactivated
- Superuser bypasses all status mutability restrictions

**Agent vs Admin:**
- **Admins:** Full access to all features
- **Agents:** Restricted to Numbers page, only see assigned numbers, cannot add/import/bulk-delete

**Role-based routing (frontend):**
- `/` Dashboard - ADMIN only
- `/numbers` - ADMIN + AGENT
- `/schedule` - ADMIN only
- `/admins` - ADMIN only
- `/profile` - ADMIN + AGENT

### Phone Number Validation

**Normalization flow:**
```
Input formats:
  0912...       → 09xxxxxxxxx
  +98912...     → 09xxxxxxxxx
  0098912...    → 09xxxxxxxxx
  912...        → 09xxxxxxxxx

Validation:
  - Must be 11 digits after normalization
  - Must start with 09
  - Persian/Arabic digits normalized to English
```

**Deduplication:**
- Phone numbers unique at DB level
- Bulk import uses `ON CONFLICT DO NOTHING`
- Returns count of added/duplicates/invalid

### Call Scheduling

**Time window evaluation:**
```python
def is_call_allowed(current_time: datetime) -> tuple[bool, str]:
    # 1. Check enabled flag
    if not schedule_config.enabled:
        return False, "disabled"

    # 2. Check shared Iran holidays (Jalali calendar)
    if schedule_config.skip_holidays and is_holiday(current_time):
        return False, "holiday"

    # 3. Get day of week (0=Saturday in Persian calendar)
    day_of_week = current_time.weekday()  # adjusted for Persian week

    # 4. Find windows for this day
    windows = get_windows_for_day(day_of_week)
    if not windows:
        return False, "no_window"

    # 5. Check if current time falls in any window
    current_time_only = current_time.time()
    for window in windows:
        if window.start_time <= current_time_only <= window.end_time:
            return True, None

    return False, "outside_allowed_time_window"
```

**Retry logic:**
- If insufficient_funds/disabled → `short_retry_seconds` (300s)
- If holiday/no_window/outside_allowed_time_window → `long_retry_seconds` (900s)

**Schedule version:**
- Increments on any config/window change
- Dialer uses this to detect config updates
- Returned in every next-batch response

### Batch Assignment

**Concurrent-safe selection:**
```sql
SELECT * FROM phone_numbers
WHERE status = 'IN_QUEUE'
  AND (assigned_at IS NULL OR assigned_at < NOW() - INTERVAL '60 minutes')
ORDER BY created_at ASC
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

**Key features:**
- `SKIP LOCKED` prevents deadlocks with concurrent requests
- Stale assignments (>60min) auto-unlock
- Batch ID (UUID) for audit trail
- Returns active agents roster for call routing

**Assignment timeout:**
- Default: 60 minutes (configurable via `ASSIGNMENT_TIMEOUT_MINUTES`)
- Numbers returned to queue if no result reported
- Next batch request unlocks stale assignments before selecting

### Result Processing

**Report flow:**
```
1. Receive report from dialer
2. Find number by ID or phone (auto-create if missing)
3. Resolve agent:
   - If agent_id provided → lookup AdminUser
   - Else if agent_phone → lookup by phone_number
   - Validate is_active
4. Update PhoneNumber:
   - status ← reported status
   - total_attempts++
   - last_attempt_at ← attempted_at
   - last_status_change_at ← now
   - assigned_agent_id ← resolved agent
   - last_user_message ← user_message
   - Clear: assigned_at, assigned_batch_id
5. Create CallAttempt record:
   - phone_number_id
   - status
   - reason
   - user_message
   - agent_id
   - attempted_at
6. If call_allowed provided:
   - Update schedule_config.enabled
   - Increment schedule_config.version
7. Commit transaction
```

**Error handling:**
- Missing number → auto-create with IN_QUEUE status
- Duplicate phone on create → retry with SELECT
- Inactive agent → 400 error
- Invalid token → 401 error

### Bulk Operations

**Selection modes:**
1. **Specific IDs:** `{ "ids": [1, 2, 3] }`
2. **Select all filtered:** `{ "select_all": true, "status": "IN_QUEUE", "excluded_ids": [5] }`

**Actions:**
- `update_status` - change to specified status (mutable only, unless superuser)
- `reset` - reset to IN_QUEUE, clear attempts/timestamps
- `delete` - remove from DB (mutable only, unless superuser)

**Permission checks:**
- Agents: only assigned numbers, mutable statuses
- Admins: all numbers, mutable statuses
- Superusers: all numbers, all statuses

**Transaction safety:**
- All updates in single transaction
- Row-level locking for consistency
- Rollback on any failure

### Excel Export

**Selection semantics:**
- Mirrors bulk operation selection
- Supports `ids` or `select_all` with filters
- Respects `excluded_ids` when using select_all

**Columns:**
1. ID
2. Phone Number
3. Status
4. Total Attempts
5. Last Attempt At
6. Last Status Change At
7. Agent Name (full_name)
8. Agent Phone
9. User Message (latest)

**Implementation:**
- Uses openpyxl for XLSX generation
- Streaming response for large datasets
- Joins AdminUser for agent info

---

## Configuration

### Backend Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Security
SECRET_KEY=random-secret-key-here
DIALER_TOKEN=shared-token-for-dialer

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 1 day

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:80"]

# Scheduling
ASSIGNMENT_TIMEOUT_MINUTES=60
DEFAULT_SKIP_HOLIDAYS=true

# App
APP_NAME="Salehi Dialer Admin"
DEBUG=false
```

### Frontend Environment Variables (.env)

```bash
VITE_API_BASE=http://localhost:8000
```

### Ansible Variables (group_vars/)

**prod.yml (agrad branch):**
```yaml
ansible_host: 1.2.3.4
ansible_user: root
repo_url: git@github.com:user/repo.git
repo_branch: agrad
db_name: dialer_agrad
db_user: dialer
db_password: secure_password
backend_domain: api.agrad.example.com
frontend_domain: panel.agrad.example.com
dialer_token: "{{ vault_dialer_token }}"
ssl_email: admin@example.com
```

**prod_salehi.yml (salehi branch):**
```yaml
# Same structure, different values
repo_branch: salehi
db_name: dialer_salehi
backend_domain: api.salehi.example.com
frontend_domain: panel.salehi.example.com
```

---

## Development Workflow

### Local Development Setup

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DB credentials
PYTHONPATH=. python -m app.main  # Creates tables
PYTHONPATH=. python -m app.utils.create_admin admin password123
PYTHONPATH=. uvicorn app.main:app --reload --env-file .env
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with API URL
npm run dev
```

### Database Migrations

**Create migration:**
```bash
cd backend
../venv/bin/alembic revision --autogenerate -m "description"
../venv/bin/alembic upgrade head
```

**Rollback:**
```bash
../venv/bin/alembic downgrade -1
```

### Testing

```bash
cd backend
PYTHONPATH=. pytest tests/
```

### Deployment

**First install:**
```bash
cd deploy/ansible
ansible-playbook -i inventory.ini playbook.yml \
  -e env_variant=salehi \
  --tags init,deploy,frontend,ssl
```

**Routine updates:**
```bash
ansible-playbook -i inventory.ini playbook.yml \
  -e env_variant=salehi \
  --tags deploy,frontend \
  --skip-tags init,ssl
```

---

## Code Patterns & Conventions

### Backend

**Service layer pattern:**
```python
# app/services/example_service.py
from sqlalchemy.orm import Session
from app.models import Example
from app.schemas import ExampleCreate

class ExampleService:
    @staticmethod
    def create(db: Session, data: ExampleCreate) -> Example:
        obj = Example(**data.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
```

**API route pattern:**
```python
# app/api/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.services.example_service import ExampleService
from app.schemas import ExampleCreate, ExampleResponse

router = APIRouter(prefix="/api/examples", tags=["examples"])

@router.post("/", response_model=ExampleResponse)
def create_example(
    data: ExampleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    return ExampleService.create(db, data)
```

**Dependency injection:**
```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models import AdminUser

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    token = credentials.credentials
    username = decode_access_token(token)
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

def get_current_active_user(
    current_user: AdminUser = Depends(get_current_user)
) -> AdminUser:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user

def require_admin(
    current_user: AdminUser = Depends(get_current_active_user)
) -> AdminUser:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

### Frontend

**API client pattern:**
```typescript
// src/api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

**Auth context:**
```typescript
// src/hooks/useAuth.tsx
import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/client';

interface User {
  id: number;
  username: string;
  role: 'ADMIN' | 'AGENT';
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>(null!);

export const AuthProvider: React.FC = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/api/auth/me').then(res => setUser(res.data));
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api.post('/api/auth/login', { username, password });
    localStorage.setItem('token', res.data.access_token);
    const userRes = await api.get('/api/auth/me');
    setUser(userRes.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

---

## Performance Optimizations

### Database

1. **Row-level locking with SKIP LOCKED:**
   - Prevents deadlocks in concurrent batch requests
   - Each request gets unique subset of records

2. **Bulk insert optimization:**
   - Uses `ON CONFLICT DO NOTHING` for deduplication
   - Single transaction for large imports

3. **Connection pooling:**
   - SQLAlchemy `pool_pre_ping=True` for stale connection detection
   - Default pool size: 5, max overflow: 10

4. **Indexes:**
   - phone_numbers: phone_number, status, assigned_agent_id
   - admin_users: username, phone_number
   - call_attempts: phone_number_id, agent_id
   - schedule_windows: day_of_week

### Backend

1. **Pydantic v2:**
   - Fast validation with Rust core
   - Type safety at runtime

2. **FastAPI:**
   - Async support (not fully utilized yet)
   - Automatic OpenAPI docs

3. **Streaming responses:**
   - Excel export streams bytes
   - Prevents memory issues with large datasets

### Frontend

1. **React.memo:**
   - Chart components memoized to prevent re-renders

2. **Pagination:**
   - 50 records per page (configurable)
   - Lazy loading of filtered data

3. **Debouncing:**
   - Search inputs debounced (300ms)

---

## Security Considerations

### Authentication

- **JWT with HS256:** Signed tokens, 1-day expiry
- **Bcrypt:** Password hashing with salt rounds (default 12)
- **Token storage:** LocalStorage (frontend), consider httpOnly cookies for production

### Authorization

- **Role-based access control (RBAC):**
  - Superuser → bypass all restrictions
  - Admin → full access except superuser features
  - Agent → restricted to assigned numbers

- **Route guards:**
  - Backend: Dependency injection with role checks
  - Frontend: ProtectedRoute component

### API Security

- **DIALER_TOKEN:** Shared secret for dialer endpoints
- **CORS allowlist:** Configured via .env
- **SQL injection:** Prevented by SQLAlchemy ORM
- **XSS:** React escapes by default, Tailwind uses classes

### Data Validation

- **Phone numbers:** Normalized and validated before storage
- **Pydantic schemas:** Request/response validation
- **Enum types:** Prevent invalid status values

---

## Common Issues & Solutions

### Issue: Stale batch assignments

**Symptom:** Numbers stuck in "assigned" state, not returned to queue

**Solution:**
- Auto-unlock after 60min timeout
- Manual reset via `/api/numbers/{id}/reset`
- Check `ASSIGNMENT_TIMEOUT_MINUTES` in .env

### Issue: Permission denied on status update

**Symptom:** 403 error when updating CONNECTED/FAILED numbers

**Solution:**
- These are immutable statuses
- Only superuser can update them
- Check status mutability rules in documentation

### Issue: Duplicate numbers on import

**Symptom:** CSV import reports many duplicates

**Solution:**
- Phone numbers are unique at DB level
- Duplicates are silently ignored (ON CONFLICT DO NOTHING)
- Response includes count of added/duplicates/invalid

### Issue: Dialer not receiving batches

**Symptom:** next-batch returns call_allowed=false

**Solution:**
- Check schedule windows (current time must fall in a window)
- Check enabled flag (schedule config)
- Check holiday flag (if applicable)
- Verify timezone is Asia/Tehran on both server and dialer

### Issue: Agent can't see numbers

**Symptom:** Agent sees empty list in Numbers page

**Solution:**
- Numbers must be assigned to agent (assigned_agent_id)
- Assignment happens via dialer report (agent_id or agent_phone)
- Check agent's phone_number matches what dialer sends

---

## Future Enhancements

### Potential improvements (not currently implemented):

1. **Async processing:**
   - Celery for background jobs (batch unlock, scheduled exports)
   - Redis for task queue

2. **Holiday detection:**
   - Iranian calendar integration (jdatetime)
   - Configurable holiday list

3. **WebSocket notifications:**
   - Real-time dashboard updates
   - Live call status changes

4. **Advanced analytics:**
   - Agent performance metrics
   - Campaign comparison
   - Conversion funnel

5. **Call recording integration:**
   - Store CDR (Call Detail Records)
   - Link to VoIP system recordings

6. **Multi-tenant support:**
   - Organization model
   - Isolated campaigns

7. **SMS integration:**
   - Send SMS after missed calls
   - SMS-based follow-up campaigns

8. **Import scheduling:**
   - Cron-based CSV imports
   - FTP/SFTP integration

---

## Troubleshooting

### Backend won't start

**Check:**
1. Database connection: `psql -U user -d dbname`
2. Environment variables: `cat backend/.env`
3. Port 8000 available: `lsof -i :8000`
4. Python version: `python --version` (need 3.12+)
5. Dependencies: `pip list`

**Logs:**
```bash
journalctl -u dialer-backend -f  # systemd
tail -f /var/log/dialer/backend.log  # if configured
```

### Frontend build fails

**Check:**
1. Node version: `node --version` (need 18+)
2. Dependencies: `npm install`
3. Environment: `cat frontend/.env`
4. Build errors: `npm run build`

### Database migrations fail

**Check:**
1. Alembic version: `alembic current`
2. Database connection: verify DATABASE_URL
3. Migration history: `alembic history`
4. Manual upgrade: `alembic upgrade head`

**Fix stuck migrations:**
```bash
# Downgrade one step
alembic downgrade -1

# Re-run upgrade
alembic upgrade head
```

### Permission issues (systemd)

**Fix:**
```bash
# Check service status
systemctl status dialer-backend

# Check file permissions
ls -la /opt/dialer/backend

# Fix ownership
chown -R dialer:dialer /opt/dialer

# Restart service
systemctl restart dialer-backend
```

---

## Testing

### Backend Tests

**Run all tests:**
```bash
cd backend
PYTHONPATH=. pytest tests/
```

**Run specific test file:**
```bash
PYTHONPATH=. pytest tests/test_phone_validation.py
```

**Coverage:**
```bash
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html
```

### Test Files

1. **tests/test_phone_validation.py**
   - Phone number normalization
   - Invalid format detection
   - Duplicate handling

2. **tests/test_permissions.py**
   - Role-based access control
   - Superuser bypass
   - Agent restrictions

### Manual Testing

**API endpoints (Postman/curl):**
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'

# Get numbers (use token from login)
curl http://localhost:8000/api/numbers \
  -H "Authorization: Bearer <token>"

# Dialer next-batch
curl http://localhost:8000/api/dialer/next-batch?size=10 \
  -H "Authorization: Bearer <DIALER_TOKEN>"
```

---

## Git Workflow

### Branch Strategy

- **main/master:** Production-ready code (if exists)
- **agrad:** Agrad deployment branch
- **salehi:** Salehi deployment branch
- **feature/*:** Feature development
- **hotfix/*:** Urgent fixes

### Recent Commits (from git log)

```
003b580 Auto-create numbers on dialer report and raise nginx upload size
9f76dfb Speed up number upload with bulk insert and on-conflict
444e094 Fix export request schema to include date filters
052c781 Allow dialer reports with empty phone when id present
12df5f3 Handle dialer results concurrently without 404
```

### Deployment Flow

1. Develop on feature branch
2. Merge to agrad/salehi
3. Push to remote
4. Ansible pulls and deploys
5. Systemd restarts service

---

## Documentation Files

- **README.md:** Main documentation, setup instructions, API overview
- **docs/callcenter_agent.md:** Dialer integration guide for external systems
- **claude.md:** This file - comprehensive context for AI assistants
- **backend/alembic/README:** Alembic migration guide (auto-generated)

---

## Key Metrics (as of last analysis)

- **Total backend code:** ~2,237 lines
- **Total frontend code:** ~1,868 lines
- **Database tables:** 6
- **API endpoints:** 25+
- **Supported statuses:** 11
- **Default batch size:** 100 (capped at 500)
- **Default page size:** 50
- **JWT expiry:** 1 day
- **Assignment timeout:** 60 minutes
- **Retry intervals:** 300s (short), 900s (long)

---

## Contact & Support

For questions or issues:
- Check this document first
- Review README.md and docs/
- Check git history for recent changes
- Test in local environment before production

---

**Last Updated:** 2026-02-17
**Branch:** salehi
**Architecture:** Multi-company (migration 0004 applied). Numbers are shared globally, call data is per-company in `call_results`.
---

## Multi-Company Architecture (Migration 0004)

### Overview
The system supports multiple companies sharing a common pool of phone numbers, with company-specific call tracking and deduplication.

### Database Schema

#### `numbers` table (SHARED across all companies)
```sql
CREATE TABLE numbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(32) UNIQUE NOT NULL,
    global_status globalstatus NOT NULL DEFAULT 'ACTIVE',
    last_called_at TIMESTAMP WITH TIME ZONE,
    last_called_company_id INTEGER REFERENCES companies(id),
    assigned_at TIMESTAMP WITH TIME ZONE,
    assigned_batch_id VARCHAR(64)
);
```

**Key points:**
- **NO `company_id`** - numbers are shared globally
- `global_status` = ACTIVE/POWER_OFF/COMPLAINED (affects ALL companies)
- `last_called_at` = global cooldown timestamp (e.g., 3 days across all companies)
- `last_called_company_id` = which company called it last
- `assigned_at` + `assigned_batch_id` = temporary batch assignment

#### `call_results` table (company-specific call history)
```sql
CREATE TABLE call_results (
    id SERIAL PRIMARY KEY,
    phone_number_id INTEGER REFERENCES numbers(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    scenario_id INTEGER REFERENCES scenarios(id),
    outbound_line_id INTEGER REFERENCES outbound_lines(id),
    status VARCHAR(32),  -- CallStatus enum
    reason VARCHAR(500),
    user_message VARCHAR(1000),
    agent_id INTEGER REFERENCES admin_users(id),
    attempted_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_call_results_company_attempted ON call_results(company_id, attempted_at);
CREATE INDEX ix_call_results_phone_company ON call_results(phone_number_id, company_id);
```

**Key points:**
- Every call belongs to one company (`company_id NOT NULL`)
- Per-company deduplication via `(phone_number_id, company_id)` index
- Per-company status tracking via `status` column

### Batch Queue Logic

**File:** `backend/app/services/dialer_service.py` → `fetch_next_batch()`

```python
# Global checks (apply to ALL companies):
WHERE numbers.global_status = 'ACTIVE'              # No COMPLAINED/POWER_OFF
  AND (numbers.last_called_at IS NULL 
       OR numbers.last_called_at < NOW() - INTERVAL '3 days')  # Global cooldown

# Per-company checks:
  AND numbers.id NOT IN (
      SELECT phone_number_id 
      FROM call_results 
      WHERE company_id = ?                           # Never called by THIS company
  )
  AND numbers.assigned_at IS NULL                   # Not in active batch
```

**What this achieves:**
1. **Shared numbers**: All companies see same 1.96M number pool
2. **Global cooldown**: If ANY company calls a number, NO company can call it for 3 days
3. **Global blocks**: COMPLAINED/POWER_OFF blocks number for ALL companies
4. **Per-company dedup**: Each company only gets numbers they've never called
5. **Batch locking**: `assigned_at` prevents double-assignment during batching

### Company-Specific Status View

**Problem:** `numbers.status` is outdated/misleading for multi-company

**Solution:** Calculate status per-company from latest `call_results`:

```sql
-- Get latest status for company X:
SELECT COALESCE(
    (SELECT status 
     FROM call_results 
     WHERE phone_number_id = numbers.id 
       AND company_id = X 
     ORDER BY attempted_at DESC 
     LIMIT 1
    ),
    'IN_QUEUE'  -- Default if never called
) AS status_for_company_x
```

**DONE:** `phone_service.list_numbers()` uses `_enrich_with_call_data()` to populate virtual fields (status, total_attempts, last_attempt_at, last_user_message, assigned_agent_id) from call_results per company.

**CRITICAL:** Use `max(id)` NOT `max(attempted_at)` to identify the latest call_result — some rows share the same timestamp (migration artifact).

### Key Tables

#### `companies`
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {"cost_per_connected": 500}
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

#### `scenarios`
```sql
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(128) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE(company_id, name)
);
```

#### `outbound_lines`
```sql
CREATE TABLE outbound_lines (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    phone_number VARCHAR(32) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE(company_id, phone_number)
);
```

### Removed Fields (Cleanup)

**From `numbers` table:**
- ❌ `company_id` - numbers are shared, not owned
- ❌ `status` - misleading, use call_results per-company
- ❌ `total_attempts` - wrong, must count per-company
- ❌ `last_attempt_at` - duplicate of `last_called_at`
- ❌ `last_status_change_at` - unused
- ❌ `created_at` - can use `id` for ordering
- ❌ `updated_at` - unused
- ❌ `note` - unused
- ❌ `last_user_message` - unused
- ❌ `assigned_agent_id` - old single-company feature

**From `call_results` table:**
- ❌ `created_at` - duplicate of `attempted_at`

### Migration Notes

**Production deployment:**
1. Backup database: `pg_dump salehi_panel > backup.sql`
2. Run migration: `alembic upgrade head`
3. Create companies: `INSERT INTO companies (name, display_name) VALUES ('salehi', 'صالحی')`
4. Create default scenario + outbound lines
5. Assign existing users to company
6. Assign existing call_results to company + scenario + outbound_line
7. Update company settings: `{"cost_per_connected": 500}`

**Batched updates for large tables (2M+ rows):**
```sql
-- Example: Assign call_results to scenario
UPDATE call_results 
SET scenario_id = 1 
WHERE scenario_id IS NULL 
  AND company_id = 1;

-- Use MOD for outbound line distribution:
UPDATE call_results
SET outbound_line_id = ((id % 4) + 1)
WHERE outbound_line_id IS NULL;
```

---
