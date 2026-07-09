# HR Agent — System Architecture Skeleton

## Project Overview
智能简历投递系统 — Auto-matching positions and submitting resumes for job seekers; AI-powered evaluation for recruiters.

## Tech Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + LangGraph
- **Frontend**: React 19 + TypeScript + Vite + shadcn/ui + Zustand + TanStack Query
- **LLM**: DeepSeek API (via httpx)
- **Database**: PostgreSQL 18 + pgvector

---

## Backend Structure (`backend/app/`)

### Models (`models/`)
- `base.py` — Base + TimestampMixin (UUID id, created_at, updated_at)
- `user.py` — User (email, password_hash, role, name, avatar_url)
- `seeker_profile.py` — SeekerProfile (resume_text, skills, experience_years, education)
- `recruiter_profile.py` — RecruiterProfile (company, position, bio)
- `job.py` — Job (title, company, description, requirements, salary range, status)
- `application.py` — Application (job_id, applicant_id, resume_text, structured_resume, status, AI fields)
- `evaluation_task.py` — EvaluationTask (batch AI evaluation tracking)
- `conversation.py` — Conversation (chat history for AI recruiter)
- `resume.py` — Resume (user_id, name, file_name, file_type, file_data, parsed_text, structured_data) ← NEW

### API Routes (`api/`)
- `auth.py` — POST /api/auth/register, /login, /refresh
- `jobs.py` — CRUD for jobs, search, filtering
- `applications.py` — POST apply, GET my/list, PATCH status
- `agent.py` — POST evaluate, GET task status, POST confirm
- `chat.py` — WebSocket chat with AI recruiter
- `resumes.py` — POST parse, POST create, GET list/detail/download, PUT update, DELETE ← NEW

### Schemas (`schemas/`)
- `auth.py` — AuthRequest, AuthResponse, RegisterRequest
- `job.py` — JobCreate/Update/Response/List, SearchParams
- `application.py` — StructuredResume, ApplicationCreate/Response/List
- `agent.py` — DimensionScore, ResumeEvaluation, BorderlineReview
- `chat.py` — ChatRequest/Response
- `resume.py` — ResumeListItem, ResumeResponse, ResumeListResponse, ParseResumeResponse ← NEW

### Services (`services/`)
- `auth_service.py` — JWT token generation/verification, password hashing
- `job_service.py` — Job CRUD + search logic
- `application_service.py` — Create/get/update applications, status counting
- `agent_service.py` — LangGraph workflow orchestration for batch evaluation
- `resume_service.py` — File text extraction (PDF/DOCX/TXT) + LLM parsing ← NEW
- `agent/` — LangGraph graph, nodes, state, prompts
- `conversation/` — Chat agent, conversation management, prompts

### LLM (`llm/`)
- `base.py` — BaseLLMProvider (abstract: evaluate_resume, review_borderline, summarize_conversation, parse_resume)
- `deepseek.py` — DeepSeekProvider implementation via httpx
- `schemas.py` — Re-exports from app.schemas.agent

---

## Frontend Structure (`frontend/src/`)

### Pages (`pages/`)
- `LoginPage.tsx` — Login form
- `RegisterPage.tsx` — Registration form
- `JobMarketPage.tsx` — Job listing with search/filter
- `JobDetailPage.tsx` — Job details + apply button
- `ApplyPage.tsx` — Multi-step application form (with ResumeUploader) ← MODIFIED
- `MyApplicationsPage.tsx` — Seeker's application history
- `ProfilePage.tsx` — Resume management center ← NEW
- `JobDashboardPage.tsx` — Recruiter's job dashboard
- `PostJobPage.tsx` — Job posting form
- `ApplicantsPage.tsx` — Recruiter's applicant list
- `EvaluationResultPage.tsx` — AI evaluation results

### Features (`features/`)
- `auth/` — Auth store (Zustand), login/register/logout hooks, types
- `jobs/` — Job queries and mutations
- `applications/` — Application API, hooks, types
- `chat/` — AI recruiter chat
- `resumes/` — Resume API, hooks, components ← NEW
  - `api/resumes.ts` — API client (parseResume, uploadResume, getResumeList, etc.)
  - `hooks/useResumes.ts` — React Query hooks
  - `components/ResumeUploader.tsx` — Drag-and-drop upload + parse + fill form
  - `components/ResumeCard.tsx` — Resume card with rename/download/delete

### Shared (`shared/`)
- `api/client.ts` — Axios instance with JWT refresh interceptor
- `api/error.ts` — Error message extraction
- `constants/queryKeys.ts` — TanStack Query key factories
- `ui/layout/SeekerLayout.tsx` — Top-bar layout with nav + avatar dropdown (profile menu)
- `ui/layout/RecruiterLayout.tsx` — Sidebar layout for recruiters
- `ui/StepForm.tsx` — Multi-step form wrapper

---

## Key Data Flows

### Resume Upload + Parse → Auto-fill
1. User drops/selects file on ApplyPage
2. ResumeUploader validates type/size, POSTs to /api/resumes/parse
3. Backend extracts text (PDF/DOCX/TXT), calls DeepSeek LLM for structured JSON
4. Returns parsed_text + structured_data to frontend
5. Frontend calls form.reset() with structured_data → auto-fills all fields

### Resume Library (Profile Center)
1. ProfilePage loads user's resumes via GET /api/resumes/
2. Displays grid of ResumeCard components
3. Upload dialog supports drag-drop + naming
4. Each card supports: inline rename, download (base64 → Blob), delete (with confirm)
