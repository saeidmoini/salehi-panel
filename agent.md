# Agent Guide

This repo hosts a separate admin panel for a VoIP dialer. Backend is FastAPI + SQLAlchemy + PostgreSQL; frontend is React (Vite) + TypeScript + Tailwind. Timezone is always Asia/Tehran and UI dates are Jalali via dayjs + jalaliday. Dialer scheduling stays in this panel (never on the VoIP server).

## Architecture
- `backend/app/main.py` – FastAPI app, mounts routers and creates tables.
- Core: `core/config.py` (Pydantic settings via `.env`), `core/db.py` (SQLAlchemy engine/session), `core/security.py` (bcrypt + JWT).
- Models: `models/*` (AdminUser, PhoneNumber + CallStatus enum, ScheduleConfig/Window, CallAttempt, DialerBatch).
- Schemas: `schemas/*` Pydantic v2 models matching the API.
- Services: business logic in `services/*` (auth, phone number validation/dedup, schedule evaluation, dialer batch selection and result logging).
- API layer: thin routers in `api/*` for auth, admins, schedule, numbers, and dialer endpoints; dependencies in `api/deps.py`.
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

## Number logic
- Validation/normalization in `services/phone_service.py` (Iran mobile: normalized to `09` + 9 digits). Duplicates are ignored; response reports inserted/duplicate/invalid counts. Status updates allowed via admin API and dialer report.

## Auth
- Admins: JWT bearer. `get_current_active_user` from `core/security.py` guards admin routes. Passwords hashed with bcrypt.
- Dialer API: shared token from `.env` validated by `api/deps.get_dialer_auth`.

## Config & environment
- Backend `.env` (see `backend/.env.example`): DB URL, `SECRET_KEY`, `DIALER_TOKEN`, batch sizes, timezone, `CORS_ORIGINS` (JSON array for allowed frontend origins).
- Frontend `.env` (see `frontend/.env.example`): `VITE_API_BASE`.
- `.gitignore` already ignores envs, node_modules, venv, builds. Keep it updated when new tools are added. Ansible secrets: `deploy/ansible/group_vars/prod.yml` is ignored; use the provided `prod.sample.yml` as a template and/or Ansible Vault for secrets.

## Testing
- Basic pytest suite under `backend/tests` (phone normalization, scheduling helper). Run with `PYTHONPATH=backend pytest backend/tests`. Extend with service-level tests when altering logic.

## Deployment/Server
- ASGI ready (uvicorn/gunicorn). Tables auto-create via `Base.metadata.create_all`; add Alembic migrations for production changes.
- Keep dialer token secret; do not expose dialer routes without auth.
- Templates for ops are under `deploy/` (systemd, nginx, and Ansible skeleton). Adjust paths/env/certs per environment.
- Alembic scaffold is under `backend/alembic/`. Use `alembic revision --autogenerate` + `alembic upgrade head` when models change; ensure `DATABASE_URL` is set in `.env`.

## Always
- Update README.md when behavior/config changes.
- Update this agent.md when architecture or workflows change.
- Never commit secrets or real `.env` content.
- Keep schedule logic centralized in the panel (services + `/api/dialer/next-batch` contract) and reflect any changes in docs.
