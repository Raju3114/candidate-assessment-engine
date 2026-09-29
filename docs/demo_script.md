# 5-Minute Live Project Demo Script

## Demo Script Flow (For Hiring Managers & Engineering Leads)

### 0:00 - 0:45 | Introduction & Architecture
- Present high-level architecture diagram. Highlight FastAPI async performance, PostgreSQL schema design, and Redis Pub/Sub WebSocket horizontal scaling.

### 0:45 - 1:30 | Recruiter & Candidate Onboarding
- Register Recruiter (`POST /api/v1/auth/register`) with `role="RECRUITER"`. Show Argon2id password hash and JWT access/refresh token pair issuance.
- Create Recruiter profile (`POST /api/v1/recruiters/profile`).
- Register Candidate user and create Candidate profile with skills `["Python", "FastAPI", "PostgreSQL", "Redis"]`.

### 1:30 - 2:30 | Session Creation & AI Question Generation
- Create Interview Session (`POST /api/v1/interviews`) for target role `"Staff Backend Engineer"`.
- Trigger AI Question Generation (`POST /api/v1/interviews/{id}/generate-questions`).
- Demonstrate Gemini API structured JSON output generating 5 tailored technical questions.

### 2:30 - 3:30 | Real-Time WebSocket Interview Room
- Connect Candidate client to WebSocket URI `ws://localhost:8000/ws/interviews/{id}?token=<jwt>`.
- Show room state recovery from Redis.
- Recruiter starts interview (`PATCH /api/v1/interviews/{id}/start`). Candidate receives `QUESTION_DELIVERED` socket event live.
- Candidate submits answer text over socket (`ANSWER_SUBMITTED`). Recruiter socket receives instant `ANSWER_RECEIVED` notification.

### 3:30 - 4:30 | Asynchronous AI Evaluation Engine
- Async AI worker evaluates candidate answer against technical rubric using Gemini 1.5 Pro.
- Show `EVALUATION_COMPLETED` WebSocket message pushing technical score (`8.5/10.0`) and qualitative feedback to the recruiter dashboard in real time.

### 4:30 - 5:00 | Final Executive Report & Analytics
- Trigger Report Generation (`POST /api/v1/interviews/{id}/generate-report`).
- Show category score breakdown (`Python: 8.5`, `FastAPI: 8.0`, `PostgreSQL: 9.1`), deterministic hiring decision (`STRONG_HIRE`), executive summary, and Redis cache acceleration.
