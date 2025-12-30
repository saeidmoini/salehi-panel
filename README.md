# Salehi Dialer Admin Panel

Admin panel for managing outbound dialing campaigns: phone number queueing, call scheduling, admin users, and dialer-facing APIs. Backend is FastAPI + SQLAlchemy + PostgreSQL. Frontend is React (Vite) + TypeScript + Tailwind.

## Tech Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL, Pydantic v2, JWT auth, passlib bcrypt
- Frontend: React 18 + Vite + TypeScript + Tailwind CSS
- Timezone: Asia/Tehran for logic; UI shows Jalali (Shamsi) dates via dayjs + jalaliday

## Backend – Run locally
1. Copy `backend/.env.example` to `backend/.env` and fill values (DB URL, `SECRET_KEY`, `DIALER_TOKEN`).
2. Install deps (inside a virtualenv):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Create DB schema on first run:
   ```bash
   PYTHONPATH=. python -m app.main  # or let uvicorn create tables on startup
   ```
4. Create the first admin user:
   ```bash
   PYTHONPATH=. python -m app.utils.create_admin admin password123
   ```
5. Start API:
   ```bash
   PYTHONPATH=. uvicorn app.main:app --reload --env-file .env
   ```

## Frontend – Run locally
1. Copy `frontend/.env.example` to `frontend/.env` and point `VITE_API_BASE` to the backend (e.g. `http://localhost:8000`).
2. Install deps and run dev server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Key Features
- Admin authentication (JWT), user CRUD, activate/deactivate, password hashing (bcrypt)
- Call scheduling: weekday intervals (Saturday–Friday), skip-holidays flag, schedule versioning, service that answers `is_call_allowed`
- Numbers management: add manually or CSV/XLSX import, dedupe, validation for Iranian mobile numbers, status updates, pagination/search
- Bulk actions on numbers (select page, select all filtered across pages): change to any status, reset to queue, or delete
- Dialer APIs protected by `DIALER_TOKEN`
- Stats APIs for totals and reporting: number status distribution and daily call-attempt percentages
- Single global switch (`enabled`/`call_allowed`) controls whether numbers are dispatched to the dialer; can be toggled from the UI or by the dialer via result reporting

## Dialer API (scheduling enforced)
- `GET /api/dialer/next-batch?size=100`
  - Checks schedule (Asia/Tehran). If outside window/holiday, returns:
    ```json
    {
      "call_allowed": false,
      "timezone": "Asia/Tehran",
      "server_time": "...",
      "schedule_version": 3,
      "reason": "outside_allowed_time_window",
      "retry_after_seconds": 600
    }
    ```
  - If allowed, returns and locks `IN_QUEUE` numbers:
    ```json
    {
      "call_allowed": true,
      "timezone": "Asia/Tehran",
      "server_time": "...",
      "schedule_version": 3,
      "batch": {
        "batch_id": "<uuid>",
        "size_requested": 100,
        "size_returned": 73,
        "numbers": [{"id": 1, "phone_number": "09123456789"}]
      }
    }
  ```
  - Reasons may be `disabled`, `holiday`, `no_window`, or `outside_allowed_time_window`; retry hints use `short_retry_seconds` (120s) or `long_retry_seconds` (900s) depending on schedule.
  - Dialer must obey `call_allowed` and back off using `retry_after_seconds`.
- `POST /api/dialer/report-result`
  - Payload: `{ "number_id": 1, "phone_number": "0912...", "status": "CONNECTED" | "FAILED" | "NOT_INTERESTED" | "MISSED" | "HANGUP" | "DISCONNECTED", "reason": "optional", "attempted_at": "ISO8601", "call_allowed": false }`
  - Updates number status, increments attempts, clears assignment, logs attempt, and if `call_allowed` is sent (true/false) it updates the global enable flag accordingly (e.g., dialer can shut off dispatch by sending `call_allowed=false`).

## Number validation & dedupe
- Accepted formats: `0912...`, `+98912...`, `0098912...`, or `912...` (normalized to `09` + 9 digits)
- Invalid entries rejected; duplicates ignored and reported in response.

### Admin number endpoints (high level)
- `GET /api/numbers` list with `status`, `search`, `skip`, `limit`
- `GET /api/numbers/stats` returns `{ "total": <count> }` for the current filter (used for select-all across pages)
- `POST /api/numbers` add manually; `POST /api/numbers/upload` CSV/XLSX single-column import
- `PUT /api/numbers/{id}/status`, `POST /api/numbers/{id}/reset`, `DELETE /api/numbers/{id}`
- `POST /api/numbers/bulk` with `action` (`update_status` | `reset` | `delete`), `status` (when updating), `ids` or `select_all` + filters to act on all filtered rows (even across pages)

## Scheduling
- Intervals stored per weekday (Saturday=0 … Friday=6), evaluated in Tehran time.
- `skip_holidays` flag is stored; holiday detection hook is stubbed for now. Default is taken from `.env` on first boot.
- Global enable/disable switch (`enabled`/`call_allowed`): when disabled, `/api/dialer/next-batch` returns `call_allowed=false` with reason `disabled` so no numbers reach the dialer. Dialer may also send `call_allowed=false` in report-result to turn it off remotely.
- `schedule_version` increments on changes and is echoed in `/api/dialer/next-batch` responses.
- Assigned numbers auto-unlock after `ASSIGNMENT_TIMEOUT_MINUTES` (default 60) if no result is reported, returning them to the queue.

## CORS
- Backend CORS allowlist is controlled via `CORS_ORIGINS` in `.env` (JSON array). Default allows localhost ports 5173/80 for the Vite dev server. Add your deployed frontend domain when hosting.

## Migrations (Alembic)
- Alembic scaffold with initial revision `0001_initial` lives in `backend/alembic/`. Tables also auto-create on startup via `Base.metadata.create_all` for local/dev, but for deployments run migrations:
  ```bash
  cd backend
  # ensure DATABASE_URL is set (e.g., via .env)
  ../venv/bin/alembic upgrade head
  ```
- When models change, generate a new revision: `../venv/bin/alembic revision --autogenerate -m "desc"` then `../venv/bin/alembic upgrade head`.

## Tests
- Basic tests cover phone normalization and schedule next-start helper: `PYTHONPATH=backend pytest backend/tests` (deps required).

## Notes
- All sensitive config via `.env`; never commit real secrets.
- REST layer is thin; business logic sits in `app/services/*`.
- Tables auto-create on startup via `Base.metadata.create_all`; migrate with Alembic later if needed.
- JWT tokens default to 1-day expiry (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 1440).

## Deployment (systemd + nginx)
- Systemd and nginx templates live inside the Ansible roles: `deploy/ansible/roles/backend/templates/gunicorn.service.j2` and `deploy/ansible/roles/nginx/templates/site.conf.j2`. Render them via Ansible or adapt manually.
- Update paths, domain, and SSL certs as needed.
- Branch/vars discipline: `agrad` branch uses `deploy/ansible/group_vars/prod.yml`. `salehi` branch uses `deploy/ansible/group_vars/prod_salehi.yml`. When running Ansible, pick the right vars via `-e env_variant=agrad` (default) or `-e env_variant=salehi`.

## Ansible (repeatable deploy)
- A ready-to-use Ansible skeleton is under `deploy/ansible/` (inventory, playbook, roles for common packages, postgres, backend, frontend, nginx, ssl).
- Copy `deploy/ansible/group_vars/prod.sample.yml` to `deploy/ansible/group_vars/prod.yml` (ignored by git) and fill in your server IP, repo URL, DB creds, domains, ports, and tokens (or use Ansible Vault).
- Tags:
  - `init`: one-time tasks (DB/user creation, systemd unit, SSL/ACME, optional initial admin seed)
  - `deploy`: git pull, pip (gunicorn ensured), Alembic upgrade, systemd restart, nginx config/reload (removes default site)
  - `frontend`: npm install/build, frontend .env render
  - `ssl`: ACME/Arvan issuance/renewal
- First install: `cd deploy/ansible && ansible-playbook -i inventory.ini playbook.yml --tags init,deploy,frontend,ssl`
- Routine updates: `cd deploy/ansible && ansible-playbook -i inventory.ini playbook.yml --tags deploy,frontend --skip-tags init,ssl`
