# Agent Guide

This repo hosts a separate admin panel for a VoIP dialer. Backend is FastAPI + SQLAlchemy + PostgreSQL; frontend is React (Vite) + TypeScript + Tailwind. Timezone is always Asia/Tehran and UI dates are Jalali via dayjs + jalaliday. Dialer scheduling stays in this panel (never on the VoIP server).

## Architecture
- `backend/app/main.py` – FastAPI app, mounts routers and creates tables.
- Core: `core/config.py` (Pydantic settings via `.env`), `core/db.py` (SQLAlchemy engine/session), `core/security.py` (bcrypt + JWT).
- Models: `models/*` (AdminUser, PhoneNumber + CallStatus enum, ScheduleConfig/Window, CallAttempt, DialerBatch).
- Schemas: `schemas/*` Pydantic v2 models matching the API.
- Services: business logic in `services/*` (auth, phone number validation/dedup, schedule evaluation, dialer batch selection and result logging, stats aggregations).
- API layer: thin routers in `api/*` for auth, admins, schedule, numbers, dialer endpoints, and stats; dependencies in `api/deps.py`.
- Frontend: Vite React app in `frontend/` with auth context, protected routes, basic pages for dashboard, numbers, schedule, and admin users. Tailwind config defines a `brand` palette.

## Where to put things
- New backend routes → `app/api/<area>.py`; schemas in `app/schemas`, logic in `app/services`, DB access in `app/models` (and `repositories` if you add that layer).
- New business logic → services; keep HTTP handlers thin.
- New DB entities → `app/models`, export via `app/models/__init__.py`; update Pydantic schemas and services accordingly.
- Frontend pages/components → `frontend/src/pages` and `frontend/src/components`; API helpers in `frontend/src/api`.

## Adding/Modifying APIs
1. Define/extend Pydantic schemas under `app/schemas`.
2. Implement logic in services/repositories.
3. Add FastAPI route with proper dependencies (JWT admins or dialer token).
4. Update docs (README.md) and if architecture shifts, edit this file.

## Scheduling rules
- Schedule lives in `services/schedule_service.py`; day mapping is Saturday=0 … Friday=6 using Tehran time. `is_call_allowed` checks intervals, `enabled` (global switch), and `skip_holidays` (holiday detection stubbed) and returns retry hints. `schedule_version` increments on changes.
- `/api/dialer/next-batch` **must** enforce schedule before selecting numbers and always returns `call_allowed` + `retry_after_seconds` (reason can be `disabled`, `holiday`, `outside_allowed_time_window`, etc.). Never move scheduling logic to the dialer side.
- Global enable flag (`enabled`/`call_allowed`): when false, `/api/dialer/next-batch` returns `call_allowed=false` with reason `disabled`. Dialer can send `call_allowed` in `/api/dialer/report-result` to toggle this flag remotely; bump `schedule_version` when it changes.

## Number logic
- Validation/normalization in `services/phone_service.py` (Iran mobile: normalized to `09` + 9 digits). Duplicates are ignored; response reports inserted/duplicate/invalid counts. Status updates allowed via admin API and dialer report.
- Bulk admin ops: `/api/numbers/bulk` supports `update_status`, `reset`, `delete` on selected ids or `select_all` with filters (status/search) and optional `excluded_ids`. `/api/numbers/stats` returns total for the current filter (used for select-all across pages). Keep bulk logic in `phone_service.bulk_action`.

## Auth
- Admins: JWT bearer. `get_current_active_user` from `core/security.py` guards admin routes. Passwords hashed with bcrypt.
- Dialer API: shared token from `.env` validated by `api/deps.get_dialer_auth`.

## Config & environment
- Backend `.env` (see `backend/.env.example`): DB URL, `SECRET_KEY`, `DIALER_TOKEN`, batch sizes, timezone, `CORS_ORIGINS` (JSON array for allowed frontend origins).
- JWT expiry defaults to 1 day (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- Frontend `.env` (see `frontend/.env.example`): `VITE_API_BASE`.
- `.gitignore` already ignores envs, node_modules, venv, builds. Keep it updated when new tools are added. Ansible secrets: `deploy/ansible/group_vars/prod.yml` is ignored; use the provided `prod.sample.yml` as a template and/or Ansible Vault for secrets.

## Testing
- Basic pytest suite under `backend/tests` (phone normalization, scheduling helper). Run with `PYTHONPATH=backend pytest backend/tests`. Extend with service-level tests when altering logic.

## Deployment/Server
- ASGI ready (uvicorn/gunicorn). Tables auto-create via `Base.metadata.create_all`; add Alembic migrations for production changes.
- Keep dialer token secret; do not expose dialer routes without auth.
- Ops automation lives under `deploy/ansible/` (roles for backend/frontend/nginx/systemd/ssl); systemd + nginx templates are in `roles/backend/templates/gunicorn.service.j2` and `roles/nginx/templates/site.conf.j2`.
- Alembic scaffold (with initial `0001_initial`) is under `backend/alembic/`. Use `alembic revision --autogenerate` + `alembic upgrade head` when models change; ensure `DATABASE_URL` is set in `.env`.
- Ansible tags: `init` (one-time: DB/user creation, systemd unit, SSL/ACME, optional admin seed), `deploy` (git pull, pip with gunicorn, Alembic upgrade, systemd restart, nginx config/reload and removes default site), `frontend` (npm install/build), `ssl` (ACME/Arvan). For updates run `--tags deploy,frontend --skip-tags init,ssl`; first install run `--tags init,deploy,frontend,ssl`. Keep `initial_admin_user/password` empty after first seed to avoid repeats.
- Queue safety: numbers assigned to a batch are locked; stale assignments auto-unlock after `ASSIGNMENT_TIMEOUT_MINUTES` (default 60) so they can return to IN_QUEUE if the dialer crashes.
- Branch/vars discipline: `agrad` branch uses `deploy/ansible/group_vars/prod.yml`; `salehi` branch uses `deploy/ansible/group_vars/prod_salehi.yml`. Run Ansible with `-e env_variant=agrad|salehi` to pick the right vars.

## Always
- Update README.md when behavior/config changes.
- Update this agent.md when architecture or workflows change.
- Never commit secrets or real `.env` content.
- Keep schedule logic centralized in the panel (services + `/api/dialer/next-batch` contract) and reflect any changes in docs.
