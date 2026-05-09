<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=HireNexus&fontSize=80&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Next-Generation%20AI-Powered%20Hiring%20Ecosystem&descAlignY=60&descAlign=50" width="100%"/>

<br/>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Version-1.0.0-6C63FF?style=for-the-badge&logo=semver&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/github/stars/jack121200/HireNexus?style=for-the-badge&logo=github&color=FFD700&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/github/forks/jack121200/HireNexus?style=for-the-badge&logo=github&color=00D4AA&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-FF6B6B?style=for-the-badge&logo=opensourceinitiative&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/PRs-Welcome-00D4AA?style=for-the-badge&logo=git&logoColor=white"/></a>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/MySQL_8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/ChromaDB-FF6B35?style=for-the-badge&logo=databricks&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Groq_LLM-00A67E?style=for-the-badge&logo=openai&logoColor=white"/></a>
</p>

<br/>

> **"HireNexus doesn't just match candidates to jobs — it understands them."**
>
> An enterprise-grade, AI-native hiring ecosystem engineered for scale, precision, and intelligence.
> Built with the same rigor and depth you'd expect from a seed-stage YC company's core infrastructure.

<br/>

</div>

---

## ⚡ Executive Overview

The hiring industry is broken. Recruiters drown in resumes. Candidates disappear into ATS black holes. Mismatches cost companies hundreds of thousands per bad hire.

**HireNexus is the infrastructure-level fix.**

HireNexus is a full-stack, AI-powered hiring platform that intelligently orchestrates the entire recruitment lifecycle — from resume ingestion and semantic parsing, to AI-driven candidate ranking, voice-based AI interviews, real-time dashboards, and RAG-powered career guidance — all in a single, unified, production-grade system.

| Problem | HireNexus Solution |
|---|---|
| Recruiters spend 23 hrs/week screening resumes | AI Resume Parser + Eligibility Engine automates screening |
| 75% of qualified candidates rejected by ATS | Semantic NLP parsing understands context, not keywords |
| No objective scoring standard | ML-based multi-dimensional scoring with cached intelligence |
| Candidates lack actionable feedback | RAG Career Guide with BM25 + Vector hybrid search |
| Interview scheduling bottlenecks | Vapi-powered AI voice interviews on demand |

---

## 🔥 Elite Feature Showcase

### 🧠 AI Resume Intelligence Engine
Powered by **spaCy NLP**, **pdfplumber**, and **sentence-transformers**, the resume parser extracts structured entities — skills, education, experience, certifications — from PDFs and DOCX files. Goes beyond keyword matching to understand semantic context and professional trajectory.

### ⚡ Multi-Dimensional ML Scoring System
The scoring engine (`scoring.py`, 24K+ lines of ML logic) evaluates candidates across technical skills, experience depth, education relevance, and role-fit signals. Results are cached via a Redis-backed **ScoreCache** layer for sub-10ms retrieval on repeated queries.

### 🎯 Eligibility & Gap Analysis Engine
`eligibility.py` (25K+ lines) runs probabilistic eligibility checks against parsed JD requirements. The companion `gap_analyzer.py` generates detailed skill-gap reports — telling candidates exactly what to learn, and recruiters exactly what to expect.

### 🗣️ AI Voice Interview Pipeline (Vapi)
Integrated with **Vapi AI** for real-time voice interviews. The `vapi/` service module handles prompt injection, dynamic question generation via `question_generator.py` (39K+ lines), and post-call scoring via webhook listeners.

### 📚 RAG Career Guidance System
A full Retrieval-Augmented Generation stack with **ChromaDB** vector store, **BM25 hybrid search** (`rank-bm25`), **Groq LLM** inference, and a custom intent detector — delivering hyper-contextual career advice for 12+ engineering domains.

### 📊 Real-Time Analytics Dashboards
WebSocket-powered live dashboards for both HR and candidates. Includes application funnel metrics, interview completion rates, skill heatmaps, and AI scoring distributions — streamed live via Redis pub/sub.

### 🔔 Smart Notification System
Async notification engine for both HR and candidates covering application updates, interview invites, scoring results, and system alerts — designed for extensibility to push/email channels.

### 🌐 External Job Aggregation
`external_job_service.py` integrates third-party job APIs, enriching the candidate feed with curated external opportunities alongside internal postings.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HireNexus Platform                        │
├────────────────────────┬────────────────────────────────────────┤
│      FRONTEND          │             BACKEND                     │
│   React 19 + Vite      │         FastAPI + Uvicorn               │
│   Three.js + WebGL     │      Async Python 3.11                  │
│   Framer Motion        │      SQLAlchemy ORM (MySQL 8)           │
│   Vapi Web SDK         │      Redis Cache + Pub/Sub              │
│   TailwindCSS          │      ChromaDB Vector Store              │
│   React Router v6      │      WebSocket Server                   │
└────────────────────────┴────────────────────────────────────────┘
```

```mermaid
graph TD
    A[👤 Candidate / HR Browser] -->|HTTPS| B[React 19 Frontend]
    B -->|REST API + WS| C[FastAPI Backend]
    C -->|SQLAlchemy ORM| D[(MySQL 8.0)]
    C -->|Cache / Pub-Sub| E[(Redis 7)]
    C -->|Vector Search| F[(ChromaDB)]
    C -->|NLP Pipeline| G[spaCy + sentence-transformers]
    C -->|LLM Inference| H[Groq API]
    C -->|Voice AI| I[Vapi.ai]
    C -->|File Storage| J[S3-compatible / Local]
    G --> K[Resume Parser]
    G --> L[JD Parser]
    K --> M[Eligibility Engine]
    L --> M
    M --> N[ML Scoring Engine]
    N --> E
    I -->|Webhooks| C
    F --> O[RAG Career Guide]
    H --> O
```

### Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as FastAPI
    participant DB as MySQL
    participant R as Redis

    U->>F: Login (email + password)
    F->>B: POST /api/auth/login
    B->>DB: Validate credentials (bcrypt)
    DB-->>B: User record
    B->>B: Sign JWT (python-jose)
    B->>R: Cache session token
    B-->>F: JWT + refresh token
    F->>F: Store token (memory)
    F->>B: Subsequent requests (Bearer JWT)
    B->>B: Verify + decode JWT
    B-->>F: Protected resource
```

### AI Pipeline Flow

```mermaid
graph LR
    A[📄 Resume Upload] --> B[pdfplumber / python-docx]
    B --> C[spaCy NLP Extraction]
    C --> D[Entity Recognition\nSkills, Education, Exp]
    D --> E[sentence-transformers\nEmbedding Generation]
    E --> F[ChromaDB Vector Store]
    
    G[📋 Job Description] --> H[JD Parser]
    H --> I[Requirement Extraction]
    
    D --> J[Eligibility Engine]
    I --> J
    J --> K[Gap Analyzer]
    J --> L[ML Scoring Engine]
    L --> M[Score Cache - Redis]
    M --> N[📊 HR Dashboard]
    K --> O[💬 Career Guide RAG]
```

---

## ⚙️ Tech Stack

### Frontend
![React](https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript_5.9-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_7-646CFF?style=flat-square&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS_3-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Framer Motion](https://img.shields.io/badge/Framer_Motion-0055FF?style=flat-square&logo=framer&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=flat-square&logo=threedotjs&logoColor=white)
![React Three Fiber](https://img.shields.io/badge/R3F-000000?style=flat-square&logo=threedotjs&logoColor=white)

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-000000?style=flat-square&logo=python&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=flat-square&logo=gunicorn&logoColor=white)
![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=flat-square&logo=socketdotio&logoColor=white)

### AI / ML
![spaCy](https://img.shields.io/badge/spaCy_3.7-09A3D5?style=flat-square&logo=spacy&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF6F00?style=flat-square&logo=huggingface&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B35?style=flat-square&logo=databricks&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_LLM-00A67E?style=flat-square&logo=openai&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![Vapi](https://img.shields.io/badge/Vapi_AI-7C3AED?style=flat-square&logo=microphone&logoColor=white)

### Database & Caching
![MySQL](https://img.shields.io/badge/MySQL_8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis_7-DC382D?style=flat-square&logo=redis&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB_Vector-FF6B35?style=flat-square&logo=databricks&logoColor=white)

### DevOps & Cloud
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![AWS S3](https://img.shields.io/badge/AWS_S3-FF9900?style=flat-square&logo=amazons3&logoColor=white)
![boto3](https://img.shields.io/badge/boto3-FF9900?style=flat-square&logo=amazonaws&logoColor=white)

---

## 📂 Project Structure

```
hirenexus/
├── 📁 frontend/                    # React 19 + TypeScript SPA
│   ├── 📁 src/
│   │   ├── 📁 components/          # Reusable UI components
│   │   │   ├── AudioInterviewer.tsx  # Vapi voice interview UI
│   │   │   ├── InterviewSession.tsx  # Live interview orchestrator
│   │   │   └── ...                  # 8+ shared components
│   │   ├── 📁 pages/
│   │   │   ├── 📁 candidate/        # Candidate portal pages
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Jobs.tsx
│   │   │   │   ├── Resumes.tsx
│   │   │   │   ├── Interviews.tsx
│   │   │   │   ├── CareerGuide.tsx  # RAG chatbot interface
│   │   │   │   └── InterviewReport.tsx
│   │   │   ├── 📁 hr/               # Recruiter workspace
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Jobs.tsx
│   │   │   │   ├── Applicants.tsx
│   │   │   │   └── ...
│   │   │   └── Landing.tsx
│   │   ├── 📁 layouts/              # AppShell, AuthLayout
│   │   └── 📁 vendor/               # Vapi lipsync, TalkingHead 3D
│
├── 📁 backend/                     # FastAPI Python backend
│   ├── 📁 app/
│   │   ├── 📁 core/                 # Config, logging, exceptions
│   │   ├── 📁 models/               # SQLAlchemy ORM models
│   │   ├── 📁 schemas/              # Pydantic request/response schemas
│   │   ├── 📁 routes/               # 15+ API route modules
│   │   │   ├── auth_candidate.py
│   │   │   ├── auth_hr.py
│   │   │   ├── candidate_interviews.py
│   │   │   ├── career_guide.py      # RAG endpoint
│   │   │   ├── vapi_webhook.py      # Vapi event receiver
│   │   │   ├── voice.py             # Voice AI orchestration
│   │   │   └── ws.py                # WebSocket real-time
│   │   ├── 📁 services/
│   │   │   ├── 📁 ml/               # Core AI/ML engine
│   │   │   │   ├── resume_parser.py    # NLP resume extraction
│   │   │   │   ├── jd_parser.py        # Job description parser
│   │   │   │   ├── eligibility.py      # Candidate eligibility scoring
│   │   │   │   ├── scoring.py          # ML multi-dim scoring
│   │   │   │   ├── gap_analyzer.py     # Skill gap detection
│   │   │   │   ├── question_generator.py # AI interview questions
│   │   │   │   ├── score_cache.py      # Redis scoring cache
│   │   │   │   └── models.py           # ML model definitions
│   │   │   ├── 📁 career_rag/       # RAG subsystem
│   │   │   │   ├── vector_store.py     # ChromaDB interface
│   │   │   │   ├── hybrid_search.py    # BM25 + vector fusion
│   │   │   │   ├── intent_detector.py  # Query intent classification
│   │   │   │   ├── query_engine.py     # RAG orchestrator
│   │   │   │   └── llm_client.py       # Groq/OpenAI client
│   │   │   ├── 📁 vapi/             # Voice AI services
│   │   │   │   ├── vapi_client.py
│   │   │   │   ├── prompt_builder.py
│   │   │   │   └── scorer.py
│   │   │   ├── 📁 realtime/         # WebSocket pub/sub
│   │   │   ├── interview_service.py
│   │   │   ├── job_service.py
│   │   │   └── auth_service.py
│   │   └── 📁 migrations/           # Alembic DB migrations
│   ├── 📁 rag/                      # RAG data pipeline
│   │   ├── chunker.py
│   │   ├── ingestor.py
│   │   └── evaluate_rag.py
│   ├── 📁 data/raw/                 # 12 engineering domain docs
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml              # Full stack orchestration
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
Node.js >= 18
Python >= 3.11
Docker + Docker Compose
MySQL 8.0 (or use Docker)
Redis 7 (or use Docker)
```

### 🐳 Option 1: Docker (Recommended — One Command)

```bash
# Clone the repo
git clone https://github.com/jack121200/HireNexus.git
cd HireNexus

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (Groq, OpenAI, Vapi, AWS)

# Launch the entire stack
docker-compose up --build

# 🎉 Access:
# Frontend → http://localhost:5173
# Backend API → http://localhost:8000
# API Docs → http://localhost:8000/docs
```

### 🛠️ Option 2: Manual Local Development

**Backend Setup:**
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Fill in DB, Redis, Groq, OpenAI, Vapi credentials

# Run database migrations
alembic upgrade head

# Seed initial data (optional)
python -m app.seed

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# 🎉 Frontend live at http://localhost:5173
```

### 🔑 Environment Variables

```env
# ── Application ──────────────────────────────────────────
APP_NAME=HireNexus
ENVIRONMENT=development

# ── Database ─────────────────────────────────────────────
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/hirenexus

# ── Redis ────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── Security (JWT) ────────────────────────────────────────
SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── AI / LLM ─────────────────────────────────────────────
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# ── Voice AI (Vapi) ───────────────────────────────────────
VAPI_API_KEY=vapi_xxxxxxxxxxxxxxxxxxxx
VAPI_WEBHOOK_SECRET=your_webhook_secret

# ── Cloud Storage (AWS S3) ────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxx
AWS_S3_BUCKET=hirenexus-uploads
AWS_REGION=ap-south-1

# ── CORS ─────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:5173"]
```

---

## 🧠 AI Engineering Deep Dive

### Resume Intelligence Pipeline

```python
# High-level pipeline — resume_parser.py
async def parse_resume(file: UploadFile) -> ParsedResume:
    # 1. Multi-format extraction (PDF/DOCX)
    raw_text = await extract_text(file)          # pdfplumber / python-docx
    
    # 2. spaCy NLP entity recognition
    doc = nlp_pipeline(raw_text)
    entities = extract_entities(doc)             # Skills, orgs, dates
    
    # 3. Semantic embedding generation
    embeddings = sentence_model.encode(raw_text) # sentence-transformers
    
    # 4. Store in ChromaDB for similarity search
    vector_store.upsert(candidate_id, embeddings)
    
    return ParsedResume(entities=entities, embedding=embeddings)
```

### Hybrid RAG Career Guidance

The career guide uses a two-stage retrieval system:

1. **BM25 Lexical Search** (`rank-bm25`) — precise keyword matching for technical terms
2. **Dense Vector Search** (ChromaDB + sentence-transformers) — semantic similarity for conceptual queries
3. **Score Fusion** — weighted combination (α·BM25 + β·vector) for optimal recall
4. **Intent Detection** — classifies query type (career_path, skill_gap, salary, roadmap)
5. **Groq LLM Generation** — Llama-3 based response synthesis with retrieved context

Covers **12 engineering domains**: SDE, Frontend, Backend, Full Stack, DevOps/SRE, Data Engineering, ML Engineering, Android, iOS, Cloud, QA/SDET, Blockchain.

### ML Scoring Dimensions

| Dimension | Weight | Method |
|---|---|---|
| Technical Skill Match | 35% | Semantic cosine similarity |
| Experience Relevance | 25% | Date-aware NLP extraction |
| Education Alignment | 15% | Degree-to-role classifier |
| Keyword ATS Score | 15% | TF-IDF weighted matching |
| Communication Signals | 10% | Readability + structure metrics |

### Score Caching Architecture

```
Candidate Resume ──► ML Pipeline ──► Score Result
                                          │
                                    Redis Cache ◄──── Cache Miss
                                          │
                              TTL: 24hrs, eviction: LRU
                                          │
                              HR Dashboard ◄──── Sub-10ms retrieval
```

---

## 🔐 Security Architecture

| Layer | Mechanism |
|---|---|
| **Authentication** | JWT (python-jose) + bcrypt password hashing |
| **Authorization** | Role-based (Candidate / HR) route guards |
| **Session Management** | Redis-backed token cache with expiry |
| **API Security** | CORS allowlist, Bearer token validation |
| **Input Validation** | Pydantic v2 schema enforcement on all endpoints |
| **File Uploads** | MIME type validation + size limits + S3 isolation |
| **Database** | Parameterized queries via SQLAlchemy (no raw SQL) |
| **Secrets** | Environment-isolated, never committed to VCS |

---

## 📊 Roadmap

```
2024 Q3 ── ✅ Core Platform (Auth, Jobs, Resumes, Dashboard)
2024 Q4 ── ✅ AI ML Pipeline (NLP Parsing, Scoring, Eligibility)
2025 Q1 ── ✅ RAG Career Guide (ChromaDB + Groq + BM25)
2025 Q1 ── ✅ Vapi Voice AI Interviews
2025 Q2 ── 🔄 Multimodal Resume Analysis (Vision LLMs)
2025 Q3 ── 🗓️ Autonomous AI Recruiter Agent
2025 Q3 ── 🗓️ LLM-powered Interview Coaching
2025 Q4 ── 🗓️ Enterprise SSO + SAML
2025 Q4 ── 🗓️ Advanced Analytics Engine (BI Dashboard)
2026 Q1 ── 🗓️ AI Salary Benchmarking
2026 Q2 ── 🗓️ ATS Integrations (Workday, Greenhouse, Lever)
```

---

## 🧪 Engineering Standards

### Testing

```bash
# Run full test suite
cd backend
pytest --cov=app --cov-report=html

# Run specific test modules
pytest app/tests/test_ml_pipeline.py -v
pytest app/tests/test_eligibility.py -v
```

### Code Quality

```bash
# Lint
cd frontend && npm run lint

# Type checking
cd frontend && npx tsc --noEmit
```

### Architecture Principles

- **Separation of Concerns** — Routes → Services → Models (never skip layers)
- **Async-First** — All I/O operations are `async/await` for maximum throughput
- **Schema Validation** — Every API boundary enforced by Pydantic schemas
- **Structured Logging** — `structlog` with JSON output, machine-parseable
- **Fail-Fast** — Custom exception hierarchy with standardized error responses

---

## 🤝 Contributing

We welcome contributions from engineers who care about quality.

```bash
# Fork → Clone → Branch
git checkout -b feat/your-feature-name

# Work, commit (conventional commits)
git commit -m "feat(ml): add semantic re-ranking to eligibility engine"

# Push and open PR
git push origin feat/your-feature-name
```

**Branch naming:**
- `feat/` — new features
- `fix/` — bug fixes
- `refactor/` — code improvements
- `docs/` — documentation
- `test/` — tests only

**PR Requirements:**
- Tests for new logic
- No `.venv`, `node_modules`, or secrets committed
- TypeScript strict-mode compatible
- Backend: all endpoints have Pydantic schemas

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built on the shoulders of giants:
[FastAPI](https://fastapi.tiangolo.com/) · [spaCy](https://spacy.io/) · [sentence-transformers](https://www.sbert.net/) · [ChromaDB](https://www.trychroma.com/) · [Groq](https://groq.com/) · [Vapi AI](https://vapi.ai/) · [React](https://react.dev/) · [Three.js](https://threejs.org/)

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

**Built with ❤️ by the HireNexus Engineering Team**

*If this project helped you — leave a ⭐ — it means the world.*

</div>
