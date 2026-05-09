<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=HireNexus&fontSize=80&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Next-Generation%20AI%20Recruitment%20Infrastructure&descAlignY=60&descSize=18" width="100%"/>

# ⚡ HireNexus

### *The AI-Native Hiring Intelligence Platform*

> **Reimagining talent acquisition** — from resume ingestion to AI voice interviews, powered by production-grade ML pipelines, semantic search, and autonomous scoring engines.

<br/>

[![Stars](https://img.shields.io/github/stars/yourusername/hirenexus?style=for-the-badge&logo=starship&color=FFD700&labelColor=0d1117)](https://github.com/yourusername/hirenexus/stargazers)
[![Forks](https://img.shields.io/github/forks/yourusername/hirenexus?style=for-the-badge&logo=git&color=00C9FF&labelColor=0d1117)](https://github.com/yourusername/hirenexus/network)
[![License](https://img.shields.io/badge/License-MIT-blueviolet?style=for-the-badge&labelColor=0d1117)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge&labelColor=0d1117)](CONTRIBUTING.md)
[![Made in India](https://img.shields.io/badge/Made%20in-India%20🇮🇳-FF9933?style=for-the-badge&labelColor=0d1117)](https://github.com/yourusername/hirenexus)

<br/>

![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat-square&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B35?style=flat-square&logo=databricks&logoColor=white)
![Vapi](https://img.shields.io/badge/Vapi_AI-8B5CF6?style=flat-square&logo=audiomack&logoColor=white)

<br/>

[**🚀 Live Demo**](https://hirenexus.dev) · [**📖 Docs**](https://docs.hirenexus.dev) · [**🐛 Report Bug**](https://github.com/yourusername/hirenexus/issues) · [**✨ Request Feature**](https://github.com/yourusername/hirenexus/discussions)

</div>

---

## 📌 Executive Overview

The global recruitment industry is fundamentally broken. Recruiters spend **72% of their time** on manual screening. Candidates are ghosted after applying to hundreds of roles. Bias, inefficiency, and information asymmetry cost companies **$240B annually** in bad hires.

**HireNexus** is the answer.

It is a **production-grade, AI-native hiring intelligence platform** that automates the entire talent acquisition lifecycle — from the moment a resume is uploaded to the moment an interview is scored and a decision is made. Built for the scale of modern hiring, HireNexus combines:

- 🧠 **Multi-strategy NLP resume parsing** with LLM enrichment
- 📐 **Multi-dimensional eligibility scoring** with capped, weighted ML formulas
- 🎙️ **Vapi-powered AI voice interviews** with dynamic, role-aware prompts
- 🔍 **Hybrid RAG career guidance** with ChromaDB + BM25 + Gemini
- ⚡ **Real-time WebSocket notifications** via Redis pub/sub
- 📊 **Role-specific analytics dashboards** for both candidates and recruiters

This isn't a job board. This is **recruiting infrastructure**.

---

## ✨ Feature Showcase

### 🔍 Resume Intelligence Engine
> *Multi-strategy NLP pipeline that understands your resume the way a senior engineer would.*

- **Triple-strategy skill extraction**: spaCy PhraseMatcher → Direct lexicon matching → Section delimiter parsing
- **LLM Enrichment**: Groq `llama-3.1-8b-instant` converts raw resume text into structured JSON (name, email, skills, experience, projects, certifications)
- **Multi-format ingestion**: PDF (pdfplumber → PyPDF2 fallback), DOCX, TXT
- **Impact**: 10× faster candidate profiling vs. manual screening

---

### 📐 AI Eligibility Scoring Engine
> *A weighted, capped, multi-dimensional matching algorithm that eliminates false positives.*

| Dimension | Algorithm | Weight |
|-----------|-----------|--------|
| Skill Match | Fuzzy matching (SequenceMatcher ≥ 0.82) | 50% |
| Experience | Smooth curve `score = 100 × (ratio^0.75)` | 30% |
| Education | Numeric hierarchy (PhD→HS) | 20% |
| Semantic Similarity | sentence-transformers cosine / TF-IDF fallback | Modifier |
| Keyword Overlap | Jaccard similarity (stop-words removed) | Modifier |

Hard caps prevent inflated scores for weak candidates. No more noise in your applicant pipeline.

---

### 🎙️ Vapi AI Voice Interview System
> *"Sarah" — your 24/7 AI technical interviewer who never has a bad day.*

- Dynamic system prompts built at runtime from **candidate resume + job description + skill gap analysis**
- Structured 30-minute interview: Intro → Resume Deep-Dive → 4–5 Technical → Scenario → Behavioral → Close
- **Mock Interview Mode**: coaching feedback, difficulty-adjustable, full summary at end
- Role-specific question banks: Frontend, Backend, Fullstack, DevOps, ML, Data, Android, iOS, Blockchain, SDE
- Bilingual support: English + Hindi skip-intent detection (`"nahi pata"`, `"mujhe nahi malum"`)
- Post-interview: transcript parsed, answers scored, full report stored in DB

---

### 🧠 Interview Answer Scoring Engine
> *5-dimensional answer evaluation. Rubric-based. Gemini-first. Locally fallback-safe.*

| Component | Weight | Method |
|-----------|--------|--------|
| Semantic Similarity | 35% | sentence-transformers cosine sim vs rubric |
| Keyword Coverage | 25% | Direct + partial token overlap |
| Completeness | 22% | % of rubric points addressed |
| Coherence | 10% | Lexical diversity + length curve + sentence structure |
| Technical Depth | 8% | Specificity markers ("because", "trade-off", "deployed") |

- **Bonus**: +8% if completeness ≥ 60 AND semantic ≥ 50 AND 30+ words
- **Penalty**: Short answers (< 8 words) → score × 0.4
- **Hard Cap**: coverage < 8 AND semantic < 12 → max score 22

---

### 🔭 Career RAG Guidance Chatbot
> *A hybrid retrieval-augmented generation system for India-specific career intelligence.*

```
User Query → Intent Detection → Role Normalization → Audience Mapping
    → Hybrid Search (ChromaDB vector 60% + BM25 40%)
    → Top-5 chunk retrieval
    → Gemini prompt construction (user profile + chat history + context)
    → 1500+ word India-specific career response
```

---

### ⚡ Real-Time Infrastructure
> *Redis pub/sub + WebSocket notification engine for zero-latency pipeline events.*

- HR notified the instant a candidate completes their interview
- Candidates notified on application status changes
- Candidate ↔ HR messaging via REST + WebSocket conversation threads

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HireNexus Platform                              │
├────────────────────────┬────────────────────────────────────────────────┤
│   FRONTEND             │   BACKEND                                      │
│   React 19 + Vite      │   FastAPI + Python 3.11                        │
│   TypeScript           │   SQLAlchemy ORM + Alembic                     │
│   TailwindCSS          │   MySQL (primary DB)                           │
│   Framer Motion        │   Redis (pub/sub + cache)                      │
│   Three.js / R3F       │   Uvicorn ASGI                                 │
│   Vapi Web SDK         │   WebSocket server                             │
└────────────┬───────────┴──────────────┬─────────────────────────────────┘
             │                          │
             └──────────┬───────────────┘
                        │
        ┌───────────────┼───────────────────┐
        │               │                   │
┌───────▼──────┐ ┌──────▼──────┐  ┌────────▼──────────┐
│  ML Pipeline │ │  RAG System │  │  Vapi AI Interview │
│  resume_     │ │  ChromaDB   │  │  Voice Call Engine │
│  parser.py   │ │  BM25Okapi  │  │  Dynamic Prompts   │
│  eligibility │ │  Gemini LLM │  │  Transcript Parser │
│  scoring.py  │ │             │  │  Score Engine      │
│  question_   │ └─────────────┘  └───────────────────┘
│  generator   │
└──────────────┘
```

### 🔄 Mermaid — Request Lifecycle

```mermaid
graph TD
    A[Candidate Uploads Resume] --> B[pdfplumber / PyPDF2 Extraction]
    B --> C[spaCy NLP + Lexicon Skill Extraction]
    C --> D[Groq LLM JSON Enrichment]
    D --> E[ParsedResume Stored in MySQL]
    E --> F[Candidate Views Jobs]
    F --> G[compute_eligibility runs per job]
    G --> H[Skill + Experience + Education + Semantic + Jaccard]
    H --> I[Weighted + Capped Score Displayed]
    I --> J[Candidate Applies]
    J --> K[HR Reviews Applicant Pipeline]
    K --> L[HR Triggers Interview]
    L --> M[Backend Builds Dynamic Vapi Prompt]
    M --> N[Vapi Voice Call with Sarah AI]
    N --> O[Webhook fires on Call End]
    O --> P[Transcript Parsed + Answers Extracted]
    P --> Q[Gemini Scoring / Local Fallback]
    Q --> R[ScoreResult Stored in DB]
    R --> S[HR Notified via WebSocket]
    R --> T[Candidate Views Full Report]
```

### 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant DB as MySQL
    participant R as Redis

    C->>API: POST /auth/login {email, password}
    API->>DB: Fetch user record
    DB-->>API: User + hashed_password
    API->>API: bcrypt.verify(password, hash)
    API->>API: python-jose JWT encode (role, user_id, exp)
    API-->>C: {access_token, token_type}
    C->>API: GET /protected (Bearer token)
    API->>API: Decode + validate JWT
    API->>R: Check token blacklist
    API-->>C: 200 OK + protected data
```

---

## 🧠 AI Engineering Deep-Dive

### Resume Parsing Pipeline

```
Multi-Strategy Skill Extraction:
  Strategy 1 → spaCy PhraseMatcher against SKILL_LEXICON (NLP phrase matching)
  Strategy 2 → Direct lexicon token matching (single & multi-word skills)
  Strategy 3 → Skills-section delimiter parsing (comma/pipe/slash/bullet split)

Experience Estimation:
  Strategy 1 → Regex: "X years" pattern
  Strategy 2 → Date-range math: "2021–2024" = 3 years

Education Level Detection:
  PhD(4) > Masters(3) > Bachelors(2) > Associates(1) > High School(0)

LLM Enrichment Layer:
  Model: llama-3.1-8b-instant via Groq API
  Output: Structured JSON {name, email, experience[], projects[], skills[], certs[]}
```

### Eligibility Scoring Formula

```python
base_score = (skill_pct * 0.5) + (experience_pct * 0.3) + (education_pct * 0.2)

# Downward caps — prevents noise from weak candidates
if skill_pct < 25:   final = 0
elif skill_pct < 50: final = min(base, 20)
elif skill_pct < 70: final = min(base, 45)
else:                final = min(base, 65)

if experience_pct < 40:     final = min(final, 55)
if alignment_score < 0.10:  final = min(final, 20)
```

### Question Generation — Difficulty Banding

```
< 2 years:   easy → easy → medium → medium → medium → hard
2–5 years:   easy → medium → medium → hard → hard
5+ years:    medium → hard → hard → expert → expert

Provider Cascade: Gemini → Groq → Local LLM → Template fallback
```

### Hybrid RAG Search Scoring

```python
final_score = (0.6 * chromadb_cosine_score) + (0.4 * bm25_okapi_score)
# Top-5 chunks passed to Gemini for response generation
```

---

## ⚙️ Tech Stack

### Frontend
![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_7-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS_3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Framer Motion](https://img.shields.io/badge/Framer_Motion-0055FF?style=for-the-badge&logo=framer&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=threedotjs&logoColor=white)

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-CC2927?style=for-the-badge&logo=databricks&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)

### Database & Cache
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B35?style=for-the-badge&logo=databricks&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite_Analytics-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

### AI / ML
![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_LLaMA3-F55036?style=for-the-badge&logo=meta&logoColor=white)
![Vapi](https://img.shields.io/badge/Vapi_Voice_AI-8B5CF6?style=for-the-badge&logo=audiomack&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy_NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/Sentence_Transformers-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

### DevOps & Deployment
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic_Migrations-6DB33F?style=for-the-badge&logo=liquibase&logoColor=white)

---

## 📂 Project Structure

```
hirenexus/
├── 📁 frontend/                     # React 19 + Vite + TypeScript SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── candidate/           # Dashboard, Jobs, Resumes, Interviews, Career Guide, Chat
│   │   │   └── hr/                  # Dashboard, Posted Jobs, Applicants, Interviews, Chat
│   │   ├── components/              # Reusable UI components (cards, modals, charts)
│   │   ├── layouts/                 # AuthLayout, AppLayout (role-based)
│   │   ├── hooks/                   # Custom React hooks (useAuth, useWebSocket, etc.)
│   │   ├── services/                # API client layer (Axios instances, typed endpoints)
│   │   └── types/                   # Shared TypeScript interfaces & enums
│   ├── public/                      # Static assets
│   └── vite.config.ts               # Vite build config
│
├── 📁 backend/                      # FastAPI Python backend
│   └── app/
│       ├── main.py                  # App factory: CORS, routers, lifespan events
│       ├── routes/                  # 20+ route modules (HR + Candidate + WebSocket)
│       ├── models/                  # SQLAlchemy ORM models (User, Job, Resume, Interview...)
│       ├── schemas/                 # Pydantic v2 request/response schemas
│       ├── services/
│       │   ├── ml/                  # resume_parser, eligibility, scoring, question_generator
│       │   ├── career_rag/          # ChromaDB + BM25 + Gemini RAG pipeline
│       │   ├── vapi/                # Prompt builder, Vapi client, call scorer
│       │   └── realtime/            # Redis WebSocket pub/sub notification engine
│       └── core/                    # Config (pydantic-settings), logging (structlog), exceptions
│
├── 📁 chroma_db/                    # Persistent ChromaDB vector store (career guidance data)
├── 📄 analytics.db                  # SQLite analytics (RAG query tracking, trends)
├── 📄 docker-compose.yml            # Orchestrates MySQL + Redis + Backend + Frontend + Nginx
└── 📄 .env.example                  # Environment variable template
```

---

## 🚀 Quick Start

### Prerequisites

```bash
node >= 20.0.0
python >= 3.11
docker >= 24.0
docker-compose >= 2.0
```

### 🐳 Docker Setup (Recommended — One Command)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/hirenexus.git
cd hirenexus

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your API keys (Groq, Gemini, Vapi)

# 3. Launch all services
docker-compose up --build

# Services started:
#  → Frontend:  http://localhost:5173
#  → Backend:   http://localhost:8000
#  → API Docs:  http://localhost:8000/docs
#  → MySQL:     localhost:3306
#  → Redis:     localhost:6379
```

### 🛠️ Local Development Setup

**Backend**

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# → http://localhost:5173
```

### 🔑 Environment Variables

```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/hirenexus

# Redis
REDIS_URL=redis://localhost:6379

# AI APIs
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
VAPI_API_KEY=...
VAPI_ASSISTANT_ID=...

# Security
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# App
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

---

## 🔐 Security Architecture

| Layer | Mechanism |
|-------|-----------|
| **Authentication** | JWT via `python-jose` (HS256, configurable expiry) |
| **Password Storage** | `bcrypt` hashing via `passlib` — no plaintext ever stored |
| **Authorization** | Role-based route guards (candidate / hr) on frontend + backend |
| **API Security** | CORS whitelist, rate limiting on auth endpoints |
| **Transport** | HTTPS in production (Nginx TLS termination) |
| **Secrets** | Environment-variable injection — no hardcoded credentials |
| **WebSocket Auth** | Token validated on WS handshake before pub/sub subscription |

---

## 📊 Roadmap

```
2024 Q4  ✅ Core Platform — Resume parsing, eligibility scoring, Vapi interviews
2025 Q1  ✅ RAG Career Chatbot — ChromaDB + BM25 + Gemini hybrid search
2025 Q2  ✅ Real-time Notifications — Redis WebSocket pub/sub
2025 Q3  🔄 Multimodal AI — Video interview analysis (facial, tone, sentiment)
2025 Q4  🔄 LLM Recruiter Copilot — AI-generated shortlisting summaries
2026 Q1  🔮 Autonomous Hiring Agents — End-to-end AI-driven hiring workflows
2026 Q2  🔮 Enterprise SSO — SAML / OAuth2 for enterprise customers
2026 Q3  🔮 Analytics Engine — Funnel analytics, DEI dashboards, hiring velocity
2026 Q4  🔮 Marketplace — Third-party assessment integrations (HackerRank, Codility)
```

| Feature | Status | ETA |
|---------|--------|-----|
| AI Video Interview Analysis | 🔄 In Progress | Q3 2025 |
| GPT-4o Resume Co-pilot | 🔮 Planned | Q4 2025 |
| Voice Cloning for Interviewers | 🔮 Planned | Q1 2026 |
| Autonomous Hiring Agent | 🔮 Planned | Q2 2026 |
| Enterprise SAML SSO | 🔮 Planned | Q2 2026 |
| Hiring Analytics Dashboard | 🔮 Planned | Q3 2026 |

---

## 📸 Screenshots

| Dashboard | AI Matching | Interview Report |
|-----------|-------------|-----------------|
| ![Candidate Dashboard](docs/screenshots/candidate-dashboard.png) | ![AI Matching](docs/screenshots/ai-matching.png) | ![Interview Report](docs/screenshots/interview-report.png) |

| Recruiter Workspace | Career Chatbot | Analytics |
|---------------------|----------------|-----------|
| ![HR Dashboard](docs/screenshots/hr-dashboard.png) | ![Career Chatbot](docs/screenshots/career-chatbot.png) | ![Analytics](docs/screenshots/analytics.png) |

---

## 🧪 Engineering Standards

### Clean Architecture Principles
- **Separation of Concerns**: Routes → Services → Models — no business logic in route handlers
- **Dependency Injection**: FastAPI `Depends()` for DB sessions, auth context, service instances
- **Schema Validation**: Pydantic v2 for all API boundaries — no raw dict passing
- **Structured Logging**: `structlog` + `orjson` for machine-parseable JSON logs

### Testing Strategy

```bash
# Backend tests
pytest tests/ -v --cov=app --cov-report=html

# Frontend tests
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright end-to-end
```

### Code Quality

```bash
# Python
ruff check .         # Linting
black .              # Formatting
mypy app/            # Type checking

# TypeScript
npm run lint         # ESLint
npm run typecheck    # tsc --noEmit
```

---

## 🌍 Contributing

We welcome contributions from the community. HireNexus is built with engineering excellence in mind.

### Branch Naming Convention

```
feature/short-description       # New features
fix/issue-number-description    # Bug fixes
chore/task-description          # Maintenance
docs/what-you-documented        # Documentation
refactor/component-name         # Refactoring
```

### Contribution Workflow

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/hirenexus.git

# 2. Create feature branch
git checkout -b feature/ai-resume-scoring-v2

# 3. Make changes with tests
# 4. Ensure all checks pass
ruff check . && black . && pytest tests/

# 5. Commit with conventional commits
git commit -m "feat(ml): add confidence calibration to eligibility scorer"

# 6. Push and open PR
git push origin feature/ai-resume-scoring-v2
```

### PR Requirements

- [ ] Tests pass (`pytest` + `npm test`)
- [ ] Type checks pass (`mypy` + `tsc`)
- [ ] Linting clean (`ruff` + `eslint`)
- [ ] PR description explains *why*, not just *what*
- [ ] No hardcoded secrets or credentials

---

## 📄 License

```
MIT License — Copyright (c) 2025 HireNexus Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies — subject to the conditions in the LICENSE file.
```

---

<div align="center">

### Built with ❤️ by engineers who believe hiring should be intelligent.

**[⭐ Star this repo](https://github.com/yourusername/hirenexus)** to support the project · **[📬 Contact](mailto:hello@hirenexus.dev)** for enterprise inquiries

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

</div>
