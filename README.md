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
- Dialer APIs protected by `DIALER_TOKEN`

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
  - Dialer must obey `call_allowed` and back off using `retry_after_seconds`.
- `POST /api/dialer/report-result`
  - Payload: `{ "number_id": 1, "phone_number": "0912...", "status": "CONNECTED" | "FAILED" | "NOT_INTERESTED" | "MISSED", "reason": "optional", "attempted_at": "ISO8601" }`
  - Updates number status, increments attempts, clears assignment, and logs attempt.

## Number validation & dedupe
- Accepted formats: `0912...`, `+98912...`, `0098912...`, or `912...` (normalized to `09` + 9 digits)
- Invalid entries rejected; duplicates ignored and reported in response.

## Scheduling
- Intervals stored per weekday (Saturday=0 … Friday=6), evaluated in Tehran time.
- `skip_holidays` flag is stored; holiday detection hook is stubbed for now. Default is taken from `.env` on first boot.
- Global enable/disable switch: when disabled, `/api/dialer/next-batch` returns `call_allowed=false` with reason `disabled` so no numbers reach the dialer.
- `schedule_version` increments on changes and is echoed in `/api/dialer/next-batch` responses.

## CORS
- Backend CORS allowlist is controlled via `CORS_ORIGINS` in `.env` (JSON array). Default allows localhost ports 5173/80 for the Vite dev server. Add your deployed frontend domain when hosting.

## Migrations (Alembic)
- Tables auto-create on startup via `Base.metadata.create_all` for local/dev. In production, prefer Alembic to manage schema changes. Initialize Alembic (`alembic init`) and create revision scripts when evolving models; then run `alembic upgrade head`. No migration scripts are included yet.

## Tests
- Basic tests cover phone normalization and schedule next-start helper: `PYTHONPATH=backend pytest backend/tests` (deps required).

## Notes
- All sensitive config via `.env`; never commit real secrets.
- REST layer is thin; business logic sits in `app/services/*`.
- Tables auto-create on startup via `Base.metadata.create_all`; migrate with Alembic later if needed.

## Deployment (systemd + nginx)
- Use `deploy/systemd/salehi-panel.service.example` as a template for systemd (Gunicorn with Uvicorn workers, points to backend/.env and venv).
- Use `deploy/nginx/panel.conf.example` as a template to serve the built frontend and proxy `/api` to the backend.
- Update paths, domain, and SSL certs as needed.

## Migrations (Alembic)
- Alembic scaffold added under `backend/alembic/`. To apply the current schema on a server:
  ```bash
  cd backend
  # set DATABASE_URL in .env (postgresql+psycopg2://...)
  ../venv/bin/alembic upgrade head
  ```
- When models change, generate a new revision: `../venv/bin/alembic revision --autogenerate -m "desc"` then `../venv/bin/alembic upgrade head`.

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
