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

Backend routes, Pydantic schemas, database models, and service helpers live under `backend/app/`. Seed accounts, application skills, and four assessments are in `backend/seed_data.json`. PDF and DOCX resume parsing uses pypdf and python-docx in the resume extraction service. Uploaded resumes are private and available through authenticated, owner-scoped routes; extraction adds recognized profile details without replacing existing entries. Assessment APIs support single-answer MCQs, candidate-owned attempts, answer persistence, focus/tab event recording, scoring, and history. Job matching analyzes pasted role descriptions against candidate skills, returns required/preferred skill gaps and a learning roadmap, and persists roadmap progress. LinkedIn URLs are accepted as context but LinkedIn page content is not fetched. The React app keeps authentication, dashboard, profile, assessments, and job matching under `frontend/src/features/`, with shared components and API calls in their own folders.

The backend feature-folder structure and planned API contracts are documented in [`backend/FEATURE_API_PLAN.md`](./backend/FEATURE_API_PLAN.md).

## Demo account

The demo candidate credentials are in [`backend/seed_data.json`](./backend/seed_data.json). The database and initial skill catalog are initialized from that file at API startup.

## Scope

Candidates can sign up with profile details, skills, projects, experience, education, certifications, a profile picture, and an optional resume; log in/out; edit their profile; upload or replace a PDF/DOCX resume for extraction; take assessments; and analyze pasted job descriptions against their profile skills. Job listings and recommendations, AI interviews, and AI-powered resume extraction are not included. The dashboard's opportunity area links to job-description analysis; it does not display stored job listings.
