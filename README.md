# SkillLock

A small skill-assessment platform foundation with a FastAPI API and React/Vite frontend. Candidates can authenticate, view a dashboard and profile, upload a resume for basic rule-based profile extraction, and complete backend-supported MCQ assessments.

## Run locally

1. Start the API:

   ```sh
   cd backend
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. In another terminal, start the frontend:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

   Open the Vite URL shown in the terminal (usually http://localhost:5173).

SQLite data and uploaded files are stored under `backend/` by default. `SKILLLOCK_DATABASE` and `SKILLLOCK_UPLOADS` can override those paths. Set `SKILLLOCK_SECURE_COOKIE=1` when serving the API over HTTPS.

Backend routes, Pydantic schemas, database models, and service helpers live under `backend/app/`. Seed accounts, application skills, and four assessments are in `backend/seed_data.json`. PDF and DOCX resume parsing uses pypdf and python-docx in the isolated resume extraction service. Assessment APIs support single-answer MCQs, candidate-owned attempts, answer persistence, focus/tab event recording, scoring, and history. The React app keeps authentication, dashboard, and profile features under `frontend/src/features/`, with shared components and API calls in their own folders. Dashboard-only placeholder cards are in `frontend/src/features/dashboard/dashboard_placeholders.json`.

The backend feature-folder structure and planned API contracts are documented in [`backend/FEATURE_API_PLAN.md`](./backend/FEATURE_API_PLAN.md).

## Demo account

The demo candidate credentials are in [`backend/seed_data.json`](./backend/seed_data.json). The database and initial skill catalog are initialized from that file at API startup.

## Scope

Candidates can sign up with profile details, skills, projects, experience, education, certifications, a profile picture, and a resume; log in/out; view a dashboard and their profile; and use the assessment backend API. Uploading or replacing a PDF/DOCX resume adds clearly recognized details without replacing existing profile entries. Assessment and job sections remain UI placeholders; frontend assessment-taking, job matching, general profile editing, and AI extraction are not included.
