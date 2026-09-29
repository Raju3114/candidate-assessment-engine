# System Architecture & Scaling Strategy

## 1. High-Level Architecture (HLD)

The platform follows **Clean Architecture** principles, enforcing separation of concerns between core domain entities, application use cases, infrastructure adapters, and web interfaces.

```mermaid
flowchart TB
    subgraph ClientLayer["Client Layer"]
        C_WEB["Candidate Web App"]
        R_WEB["Recruiter Dashboard"]
    end

    subgraph IngressLayer["Ingress & Edge Router"]
        NGINX["Nginx Gateway\n(TLS 1.3, Rate Limiting, WS Upgrade)"]
    end

    subgraph CoreNodes["FastAPI Backend Node Pool"]
        API_ROUTER["API Router"]
        WS_HANDLER["WebSocket Router"]
        AUTH_SVC["Auth Service"]
        SESSION_SVC["Session Service"]
        QUESTION_SVC["Question Service"]
        EVAL_SVC["Evaluation Service"]
        REPORT_SVC["Report Service"]
    end

    subgraph StorageLayer["Data & Cache Infrastructure"]
        PG[(PostgreSQL 16\nPrimary DB)]
        REDIS[(Redis 7 Cluster\nCache, PubSub, Rate Limits)]
    end

    subgraph ExternalServices["External AI Provider"]
        GEMINI["Google Gemini API\n(Gemini 1.5 Pro)"]
    end

    C_WEB -->|HTTP REST / HTTPS| NGINX
    R_WEB -->|HTTP REST / HTTPS| NGINX
    C_WEB <-->|WebSocket WSS| NGINX
    R_WEB <-->|WebSocket WSS| NGINX

    NGINX --> API_ROUTER
    NGINX <--> WS_HANDLER

    API_ROUTER --> AUTH_SVC
    API_ROUTER --> SESSION_SVC
    API_ROUTER --> QUESTION_SVC
    API_ROUTER --> EVAL_SVC
    API_ROUTER --> REPORT_SVC

    AUTH_SVC <--> PG
    SESSION_SVC <--> PG
    QUESTION_SVC <--> PG
    EVAL_SVC <--> PG
    REPORT_SVC <--> PG

    QUESTION_SVC <--> GEMINI
    EVAL_SVC <--> GEMINI
    REPORT_SVC <--> GEMINI

    WS_HANDLER <--> REDIS
    QUESTION_SVC <--> REDIS
    EVAL_SVC <--> REDIS
    REPORT_SVC <--> REDIS
```

---

## 2. Request Lifecycle & Execution Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client as Candidate Client
    participant Gateway as Nginx API Gateway
    participant FastAPI as FastAPI Route / Service
    participant Redis as Redis Cache / PubSub
    participant DB as PostgreSQL DB
    participant Gemini as Gemini AI API

    Client->>Gateway: POST /api/v1/auth/login
    Gateway->>FastAPI: Forward Request
    FastAPI->>DB: Query User & Verify Argon2id Hash
    DB-->>FastAPI: Return User Entity
    FastAPI->>Redis: Store Refresh Token JTI (TTL 7d)
    FastAPI-->>Client: Return Access & Refresh Tokens

    Client->>Gateway: WS /ws/interviews/{id}?token=<jwt> (Handshake)
    Gateway->>FastAPI: Upgrade WebSocket Connection
    FastAPI->>Redis: Restore Session Room State
    FastAPI-->>Client: Send JOIN_ROOM ACK

    Client->>FastAPI: WS Submit Answer
    FastAPI->>DB: Save Answer Entity
    FastAPI->>Gemini: Async Call Evaluate Answer
    Gemini-->>FastAPI: Return Structured Scores JSON
    FastAPI->>DB: Save AIEvaluation Entity
    FastAPI->>Redis: Cache Evaluation (TTL 1h) & Publish Event
    FastAPI-->>Client: Push EVALUATION_COMPLETED to Room
```

---

## 3. Redis Architecture & Use Cases

Redis 7 operates as the high-speed data backbone serving 4 critical functions:

1. **Active Session Caching (Cache-Aside)**:
   - Stores active question sequences and final reports (`report:{interview_id}`, TTL 6 hours).
2. **WebSocket Multi-Node Pub/Sub**:
   - Acts as a message bus across multiple FastAPI instances (`ws_channel:room:{interview_id}`).
3. **Sliding Window Rate Limiting**:
   - Enforces login limits (5/min), AI limits (20/hr), and global limits (100/min).
4. **JWT Revocation & Rotation**:
   - Blacklists revoked access token JTIs and enforces refresh token rotation.

---

## 4. Horizontal Scaling Strategy

```mermaid
flowchart LR
    Client1["Candidate App"] <-->|WS Server Node 1| App1["FastAPI Node 1"]
    Client2["Recruiter App"] <-->|WS Server Node 2| App2["FastAPI Node 2"]

    App1 <-->|Pub / Sub| RedisBus[("Redis Distributed Pub/Sub Bus")]
    App2 <-->|Pub / Sub| RedisBus
```

By decoupling WebSocket message broadcasting through Redis Pub/Sub, client socket connections can scale horizontally across $N$ stateless FastAPI container instances behind Nginx or an AWS Application Load Balancer (ALB).
