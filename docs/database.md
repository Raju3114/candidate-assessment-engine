# Database Design & Schema Specifications

## 1. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    users ||--o| candidates : "has candidate profile"
    users ||--o| recruiters : "has recruiter profile"

    recruiters ||--o{ interview_sessions : "manages"
    candidates ||--o{ interview_sessions : "attends"

    interview_sessions ||--|{ questions : "contains"
    interview_sessions ||--o| reports : "generates"

    questions ||--o| answers : "receives"
    answers ||--o| ai_evaluations : "graded by"

    users ||--o{ audit_logs : "triggers"

    users {
        uuid id PK
        string email UK
        string hashed_password
        string role
        boolean is_active
        timestamptz created_at
    }

    candidates {
        uuid id PK
        uuid user_id FK,UK
        string full_name
        numeric experience_years
        jsonb skills
    }

    recruiters {
        uuid id PK
        uuid user_id FK,UK
        string company_name
        string designation
    }

    interview_sessions {
        uuid id PK
        uuid recruiter_id FK
        uuid candidate_id FK
        string status
        string interview_type
        timestamptz scheduled_at
    }

    questions {
        uuid id PK
        uuid interview_id FK
        integer sequence_number
        text question_text
        jsonb expected_topics
    }

    answers {
        uuid id PK
        uuid question_id FK,UK
        uuid candidate_id FK
        text answer_text
    }

    ai_evaluations {
        uuid id PK
        uuid answer_id FK,UK
        numeric overall_score
        jsonb strengths
        jsonb weaknesses
    }

    reports {
        uuid id PK
        uuid interview_id FK,UK
        numeric overall_score
        string recommendation
        jsonb skill_breakdown
    }

    audit_logs {
        uuid id PK
        uuid user_id FK
        string action
        string resource
    }
```

---

## 2. Table Schemas & Constraints Summary

### `users`
- Primary Key: `id` (`UUIDv7`)
- Unique Index: `idx_users_email` on `email` WHERE `deleted_at IS NULL`
- Role constraint: `role IN ('CANDIDATE', 'RECRUITER', 'ADMIN')`

### `candidates`
- Foreign Key: `user_id` $\rightarrow$ `users(id)` (1:1 Unique, ON DELETE CASCADE)
- Index: `GIN` index on `skills` (`JSONB`) for fast candidate skill searches.

### `recruiters`
- Foreign Key: `user_id` $\rightarrow$ `users(id)` (1:1 Unique, ON DELETE CASCADE)

### `interview_sessions`
- Foreign Keys: `recruiter_id` $\rightarrow$ `recruiters(id)`, `candidate_id` $\rightarrow$ `candidates(id)`
- Indexes: B-Tree on (`recruiter_id`, `status`), (`candidate_id`, `status`), `scheduled_at`.

### `questions`
- Foreign Key: `interview_id` $\rightarrow$ `interview_sessions(id)` (ON DELETE CASCADE)
- Order Index: Composite B-Tree on (`interview_id`, `sequence_number`).

### `answers`
- Foreign Key: `question_id` $\rightarrow$ `questions(id)` (1:1 Unique, ON DELETE CASCADE)

### `ai_evaluations`
- Foreign Key: `answer_id` $\rightarrow$ `answers(id)` (1:1 Unique, ON DELETE CASCADE)

### `reports`
- Foreign Key: `interview_id` $\rightarrow$ `interview_sessions(id)` (1:1 Unique, ON DELETE CASCADE)

---

## 3. Query Optimization & Indexing Strategy

1. **UUIDv7 Time-Ordered Monotonicity**: Replaces standard UUIDv4 to eliminate B-Tree index fragmentation during high-volume inserts.
2. **Partial Indexes**: Soft delete queries check `WHERE deleted_at IS NULL`, using partial unique indexes to support re-registration without key collisions.
3. **JSONB Indexing**: GIN indexing on `candidates.skills` enables fast execution of candidate filtering queries (`Candidate.skills.contains(['Python'])`).
