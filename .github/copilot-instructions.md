# Project Guidelines

- Keep frontend features in small, focused React components under `frontend/src/features/`; place shared UI in `frontend/src/components/` and HTTP calls in `frontend/src/api/`.
- Keep feature-owned backend routes and logic together under `backend/app/features/<feature>/`; keep shared routes such as authentication and the skill catalog in `backend/app/api/routes/`. Put Pydantic request/response schemas in `backend/app/schemas/`, database models in `backend/app/models/`, and shared persistence/security helpers in focused modules under `backend/app/services/` or `backend/app/core/`.
- Keep SQLite and React/FastAPI as the existing stack. Prefer straightforward modules over extra abstraction layers.
- Update the relevant README when project structure or run instructions change.
