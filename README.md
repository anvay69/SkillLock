# SkillLock

A small skill-assessment platform foundation with a FastAPI API and React/Vite frontend. Candidates can authenticate, view a dashboard and profile, upload a resume for Gemini-powered professional profile extraction, and complete backend-supported MCQ assessments.

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

To enable Gemini-powered job and resume analysis, copy `backend/.env.example` to `backend/.env`, add your Gemini API key to `GEMINI_API_KEY`, and choose a model with `GEMINI_MODEL` (default: `gemini-2.5-flash`). Restart the API after changing the file. Keep `backend/.env` private; it is git-ignored. A pasted description or a public LinkedIn listing is sent to Gemini for structured job extraction; when both are supplied, Gemini combines them if they share even a few meaningful job-related terms and reports a mismatch only when they clearly describe unrelated roles. Resume extraction sends only recognized professional resume sections and the profile's skills, projects, experience, education, and certifications; personal/contact fields, profile links, and credentials are excluded.

Backend routes, Pydantic schemas, database models, and service helpers live under `backend/app/`. Seed accounts, application skills, and four assessments are in `backend/seed_data.json`. PDF and DOCX text extraction uses pypdf and python-docx; recognized professional sections and existing professional profile details are normalized and combined by Gemini, while personal/contact fields are excluded. Uploaded resumes remain private and available through authenticated, owner-scoped routes, and existing profile values are retained. Assessment APIs support single-answer MCQs, candidate-owned attempts, answer persistence, focus/tab event recording, scoring, and history. Job matching sends any provided pasted role description and/or scraped public LinkedIn page text to Gemini for structured job details and catalogued skill extraction; when both sources are present, a Gemini-detected mismatch is reported instead of comparing requirements. Candidate profile comparison and readiness calculation remain in the backend. Standalone JD Analysis uses the same public LinkedIn and Gemini extraction flow to show requirements and preparation suggestions without candidate-profile matching. LinkedIn retrieval is anonymous, limited to public job and post pages, and does not use login cookies or follow unvalidated redirects. The React app keeps authentication, dashboard, profile, assessments, JD Analysis, and job matching under `frontend/src/features/`, with shared components and API calls in their own folders.

The backend feature-folder structure and planned API contracts are documented in [`backend/FEATURE_API_PLAN.md`](./backend/FEATURE_API_PLAN.md).

## Demo account

The demo candidate credentials are in [`backend/seed_data.json`](./backend/seed_data.json). The database and initial skill catalog are initialized from that file at API startup.

## Scope

Candidates can sign up with profile details, skills, projects, experience, education, certifications, a profile picture, and an optional resume; log in/out; edit their profile; upload or replace a PDF/DOCX resume for Gemini-assisted extraction of professional sections; take assessments; analyze pasted descriptions or publicly readable LinkedIn job pages against their profile skills; and analyze JDs independently for requirements and preparation suggestions. When a listing is private, unavailable, or does not include readable job details, candidates can paste the description instead. Stored job listings and recommendations and AI interviews are not included. The dashboard links to job matching and JD Analysis; it does not display stored job listings.
