# Backend Feature Folder and API Plan

This plan follows the current backend conventions: FastAPI routers are registered
from `app/main.py`, API paths use the `/api` prefix, authenticated candidate
routes use the existing session cookie, and request/response models belong in
`app/schemas/`. Existing shared authentication, profile, database, and storage
code stays in place. Each feature below owns one folder directly under
`app/features/`; feature-specific route handlers and services stay together in
that folder.

The resume, assessments, job-matching, and JD-analysis features are implemented and active.
The AI interview and stored matching-jobs features below are proposed only.

## Proposed Backend Tree

```text
backend/
├── FEATURE_API_PLAN.md
├── seed_data.json
└── app/
    ├── api/
    │   └── routes/
    │       ├── auth.py                 # Existing auth, signup, candidate profile
    │       └── skills.py               # Existing shared skill catalog
    ├── core/
    │   ├── config.py
    │   └── database.py
    ├── features/
    │   ├── resume/                     # Implemented
    │   │   ├── __init__.py
    │   │   ├── routes.py
    │   │   └── service.py
    │   ├── job_matching/               # Implemented
    │   │   ├── routes.py
    │   │   └── service.py
    │   ├── jd_analysis/                # Implemented
    │   │   └── routes.py
    │   ├── assessments/                # Implemented
    │   │   └── routes.py
    │   ├── ai_interview/               # Proposed
    │   │   └── routes.py
    │   └── matching_jobs/              # Proposed
    │       └── routes.py
    ├── models/                         # Shared database models
    ├── schemas/                        # Shared and feature request/response schemas
    ├── services/                       # Shared auth, user, and generic upload helpers
    └── main.py                         # Registers active feature routers
```

For proposed features, add a feature-specific `service.py` in the same
folder only when implementing its business logic. Keep feature-specific
request/response schemas in the existing `app/schemas/` convention unless they
become large enough to justify colocating them; do not add another nested
feature hierarchy.

## 1. Resume Upload and Extraction

- **Folder name:** `resume`
- **Folder location:** `app/features/resume/` (relative to `backend/`)
- **Included functionality:** Accept a PDF or DOCX resume, store the uploaded
  file privately, parse text locally, send only recognized professional resume
  sections and the user's skills, projects, experience, education, and
  certifications to Gemini, then merge the schema-validated combined profile
  and return a summary of additions. Personal/contact fields, profile links,
  passwords, and the personal-information resume section are excluded; existing
  user-entered values are retained. The generic file-writing helper remains
  shared under `app/services/uploads.py`.
- **Endpoint file:** `app/features/resume/routes.py`
- **Service file:** `app/features/resume/service.py`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/me/resume` | Authenticated candidate uploads or replaces a PDF/DOCX resume. Stores the file, extracts and deduplicates profile entries, persists the resume URL and profile, then returns the updated profile and `extracted_added` summary. |
| `POST` | `/api/signup` | Existing auth-owned signup endpoint in `app/api/routes/auth.py`. The optional resume field uses `app/features/resume/service.py` to store and extract the resume; the endpoint returns the created profile and extraction summary. It remains in the auth router because account creation/authentication own signup. |

`app/main.py` registers `app/features/resume/routes.py`. The existing `/api/me/resume`
path and response shape are preserved.

## 2. JD and LinkedIn Job Matching

**Status: Implemented.** The authenticated frontend analysis page calls these
routes. Public LinkedIn job and post pages, including supported `lnkd.in/p/`
links, are fetched anonymously with a bounded response size and timeout.
Requests do not include login cookies and follow only a limited number of
redirects to validated LinkedIn destinations. If LinkedIn does not expose a
readable description, the caller can paste the job text instead. When a public
listing is fetched, its visible text and any pasted description are sent to Gemini for structured
job metadata and skill extraction. Pasted-description-only requests also use
Gemini. When both sources are provided, Gemini checks that they describe the
same job opening and combines their requirements. Matching is permissive: a few
meaningful overlapping job terms are enough, while unrelated roles with no
meaningful overlap produce a clear validation error. Candidate profile
comparison stays local; candidate profile details are not sent to Gemini.

- **Folder name:** `job_matching`
- **Folder location:** `app/features/job_matching/` (relative to `backend/`)
- **Included functionality:** Accept an optional pasted job-description text
  and/or a public LinkedIn listing URL, extract its public job description and
  compare stated requirements with the authenticated candidate's saved profile
  and extracted resume
  details. Return matched skills, skill gaps, a weighted skill match score,
  readiness feedback, and suggestions. Required skills count twice as much as
  preferred skills; the score is unavailable when no recognized skills exist.
  Do not sign in or bypass LinkedIn access restrictions. Follow
  only redirects that pass the LinkedIn host and path checks. Callers can provide
  the listing text when URL content is not publicly available. Gemini API
  configuration is read from `GEMINI_API_KEY`
  and `GEMINI_MODEL` in `backend/.env`; every request with at least one source
  requires Gemini.
- **Endpoint file:** `app/features/job_matching/routes.py`
- **Endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/job-matching/analyze` | Analyze a supplied job description and/or a publicly readable LinkedIn job listing against the current candidate's profile; return listing metadata, weighted skill match score, matched and missing skills, readiness feedback, and actionable suggestions. |
| `PUT` | `/api/job-matching/learning-progress` | Persist the candidate's status for a recognized roadmap skill. |

The request requires at least one of `job_description` or `linkedin_url`.
When both are supplied, both texts are analyzed. The response is an analysis
result, not a saved job listing.

## 3. JD Analysis

**Status: Implemented.** This authenticated feature reuses job matching's
validated public LinkedIn scraper and Gemini extraction flow without comparing
requirements to a candidate profile. Gemini returns structured job metadata,
required and preferred skills, and practical preparation suggestions. A pasted
description, LinkedIn URL, or both may be supplied; when both are supplied,
the existing source-consistency check is applied.

- **Folder name:** `jd_analysis`
- **Folder location:** `app/features/jd_analysis/` (relative to `backend/`)
- **Endpoint file:** `app/features/jd_analysis/routes.py`
- **Request/response schemas:** `app/schemas/jd_analysis.py`
- **Endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/jd-analysis/analyze` | Analyze pasted job-description text and/or a public LinkedIn job/post URL; return structured requirements, job summary, and Gemini-generated suggestions without candidate profile matching. |

At least one input (`job_description` or `linkedin_url`) is required.
LinkedIn scraping follows the safety, redirect, and public-content limits
documented under Job Matching. Gemini configuration is shared with the
job-matching feature.

## 4. Assessments

- **Folder name:** `assessments`
- **Folder location:** `app/features/assessments/` (relative to `backend/`)
- **Included functionality:** Browse available assessments by skill/topic, create
  and track candidate attempts, fetch and navigate questions, save answers,
  submit/score completed attempts, record focus/tab-switch events, and view
  assessment history.
- **Endpoint file:** `app/features/assessments/routes.py`
- **Service file:** `app/features/assessments/service.py`
- **Endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/assessments` | List available assessments; optionally filter by `skill` or `topic` query parameters. |
| `GET` | `/api/assessments/{assessment_id}` | Get assessment title, topic, instructions, duration, and question count without exposing answers. |
| `POST` | `/api/assessments/{assessment_id}/attempts` | Start an authenticated candidate attempt and return its attempt ID and initial state. |
| `GET` | `/api/assessments/attempts/{attempt_id}/questions` | Fetch the attempt's question list/order and current navigation state without answer keys. |
| `GET` | `/api/assessments/attempts/{attempt_id}/questions/{question_id}` | Fetch a particular question in the attempt to support previous/next navigation. |
| `PUT` | `/api/assessments/attempts/{attempt_id}/answers/{question_id}` | Save or replace the candidate's answer for a question and return the saved state. |
| `POST` | `/api/assessments/attempts/{attempt_id}/events` | Record client-observed events such as tab visibility changes and window blur/focus, with event type and timestamp. |
| `POST` | `/api/assessments/attempts/{attempt_id}/submit` | Finalize an attempt, calculate its score, persist the result, and return a completion summary. |
| `GET` | `/api/me/assessment-history` | List the current candidate's completed and in-progress attempts with dates, scores, and status. |

Attempt and question endpoints must verify ownership against the current
candidate session. Event tracking records reported browser signals; it should
not claim to prove candidate intent or prevent switching.

## 5. AI Interview

- **Folder name:** `ai_interview`
- **Folder location:** `app/features/ai_interview/` (relative to `backend/`)
- **Included functionality:** Create an interview for a chosen skill or role,
  provide interview questions, accept candidate voice responses, process
  responses, complete the session, and return feedback/report history. Keep any
  future AI/provider integration behind the feature's own service; this plan
  does not add a provider or implement AI behavior.
- **Endpoint file:** `app/features/ai_interview/routes.py`
- **Proposed endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/ai-interviews` | Start an interview for a requested skill or job role; return interview ID and initial question/prompt. |
| `GET` | `/api/ai-interviews` | List the current candidate's interview sessions and statuses. |
| `GET` | `/api/ai-interviews/{interview_id}` | Get session state and current progress for its owner. |
| `GET` | `/api/ai-interviews/{interview_id}/questions/current` | Get the current question/prompt so the client can present it as text or speech. |
| `POST` | `/api/ai-interviews/{interview_id}/responses` | Submit a voice recording (multipart audio) for processing; return the processed response/transcript and next question or completion state. |
| `POST` | `/api/ai-interviews/{interview_id}/submit` | End the interview and request final feedback/report generation. |
| `GET` | `/api/ai-interviews/{interview_id}/report` | Retrieve the completed interview's feedback and report. |

All session routes are candidate-authenticated and scoped to their owner.

## 6. Matching Jobs

- **Folder name:** `matching_jobs`
- **Folder location:** `app/features/matching_jobs/` (relative to `backend/`)
- **Included functionality:** List available job records matched against the
  candidate's skills, projects, education, and experience; provide job details
  and explanations for matches; and save or unsave jobs for the candidate.
- **Endpoint file:** `app/features/matching_jobs/routes.py`
- **Proposed endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/matched-jobs` | List jobs matched to the authenticated candidate, including a match summary and explanation; accept simple pagination/filter query parameters if needed. |
| `GET` | `/api/matched-jobs/{job_id}` | Return job details and the candidate-specific reasons for the match. |
| `GET` | `/api/me/saved-jobs` | List jobs saved by the current candidate. |
| `PUT` | `/api/matched-jobs/{job_id}/save` | Save a job for the current candidate; repeated saves should be idempotent. |
| `DELETE` | `/api/matched-jobs/{job_id}/save` | Remove a saved job for the current candidate. |

Candidate endpoints use the existing session-cookie authentication convention.
Job matching and job-description analysis remain separate: `job_matching`
analyzes a candidate-supplied role description, while `matching_jobs` lists
available stored job records.

## Seed data

Keep seed accounts and initial application data in `backend/seed_data.json`,
which is already read by the database initializer. If a future feature needs
static frontend-only placeholders, keep that data in a separate feature-local
JSON file and document it in the root README; it is not backend seed data.
