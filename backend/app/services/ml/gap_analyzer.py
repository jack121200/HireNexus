"""Gap Analyzer — enriches skill gaps with smart learning suggestions.

Called after eligibility computation to add context:
- time_to_learn
- difficulty
- learning resources
- resume tip
- personalized note based on what the candidate already knows
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Suggestion knowledge base ─────────────────────────────────────────────────

_GAP_SUGGESTIONS: dict[str, dict] = {
    "typescript": {
        "time_to_learn": "2–3 weeks",
        "difficulty": "easy",
        "prerequisite": "JavaScript",
        "resources": [
            "TypeScript official docs — typescriptlang.org/docs",
            "Matt Pocock — Total TypeScript (free YouTube)",
            "Execute Program — TypeScript course",
        ],
        "resume_tip": "Add: 'Proficient in JavaScript with hands-on TypeScript. Actively deepening TS expertise.'",
        "project_idea": "Convert any existing JS project to TypeScript and push to GitHub.",
    },
    "docker": {
        "time_to_learn": "1–2 weeks",
        "difficulty": "easy",
        "prerequisite": "Basic Linux",
        "resources": [
            "Docker official Get Started guide",
            "TechWorld with Nana — Docker Tutorial (YouTube, free)",
            "Play with Docker — labs.play-with-docker.com",
        ],
        "resume_tip": "Containerize an existing project, push to Docker Hub, mention it in resume.",
        "project_idea": "Dockerize your portfolio project with docker-compose.",
    },
    "kubernetes": {
        "time_to_learn": "3–4 weeks",
        "difficulty": "medium",
        "prerequisite": "Docker",
        "resources": [
            "Kubernetes official tutorials — kubernetes.io/docs/tutorials",
            "TechWorld with Nana — Kubernetes (YouTube, free)",
            "KodeKloud — Kubernetes for Beginners (free)",
        ],
        "resume_tip": "Start with Minikube locally. Add 'Hands-on Kubernetes for container orchestration'.",
        "project_idea": "Deploy a multi-container app on Minikube.",
    },
    "aws": {
        "time_to_learn": "4–8 weeks",
        "difficulty": "medium",
        "prerequisite": "Basic Linux / Networking",
        "resources": [
            "AWS Free Tier — 12 months free to practice",
            "AWS Skill Builder — free official courses",
            "A Cloud Guru — AWS Cloud Practitioner (free trial)",
        ],
        "resume_tip": "Get AWS Cloud Practitioner certification (2–3 weeks study, ~$100 exam). Adds instant credibility.",
        "project_idea": "Deploy any existing project on EC2 or S3+CloudFront.",
    },
    "system design": {
        "time_to_learn": "4–8 weeks (ongoing)",
        "difficulty": "medium",
        "prerequisite": "General software engineering experience",
        "resources": [
            "Gaurav Sen — System Design (YouTube, free)",
            "ByteByteGo — System Design Interview book",
            "Grokking System Design (educative.io)",
        ],
        "resume_tip": "Add: 'Designed architecture for [project] handling X users/requests'. Be specific with numbers.",
        "project_idea": "Write a GitHub README explaining your project's architecture as a system design doc.",
    },
    "react": {
        "time_to_learn": "3–4 weeks",
        "difficulty": "easy",
        "prerequisite": "JavaScript, HTML, CSS",
        "resources": [
            "React official docs — react.dev",
            "Scrimba — Learn React for free",
            "Jack Herrington — React videos (YouTube, free)",
        ],
        "resume_tip": "Build 2 projects: a todo app and a real API-connected app (weather, movies). Both on GitHub.",
        "project_idea": "Build a personal dashboard using React with live API data.",
    },
    "node.js": {
        "time_to_learn": "2–3 weeks",
        "difficulty": "easy",
        "prerequisite": "JavaScript",
        "resources": [
            "Node.js official docs — nodejs.org/docs",
            "The Odin Project — NodeJS module (free)",
            "Traversy Media — Node.js Crash Course (YouTube)",
        ],
        "resume_tip": "Build a REST API with Node.js + Express + any database. Put it on GitHub with README.",
        "project_idea": "Build user auth + CRUD REST API.",
    },
    "postgresql": {
        "time_to_learn": "1–2 weeks",
        "difficulty": "easy",
        "prerequisite": "Basic SQL",
        "resources": [
            "postgresqltutorial.com — free comprehensive guide",
            "PostgreSQL official tutorial — postgresql.org/docs",
            "Hussein Nasser — PostgreSQL (YouTube)",
        ],
        "resume_tip": "If you know MySQL, say: 'Experienced in SQL databases (MySQL, PostgreSQL)'.",
        "project_idea": "Migrate any MySQL project to PostgreSQL and document the process.",
    },
    "graphql": {
        "time_to_learn": "1–2 weeks",
        "difficulty": "easy",
        "prerequisite": "REST APIs, Node.js or Python",
        "resources": [
            "GraphQL official docs — graphql.org/learn",
            "Apollo GraphQL tutorials (free)",
            "Traversy Media — GraphQL Crash Course (YouTube)",
        ],
        "resume_tip": "Add GraphQL to an existing project. Mention: 'Built GraphQL API with Apollo Server for [project]'.",
        "project_idea": "Wrap an existing REST API with a GraphQL layer.",
    },
    "machine learning": {
        "time_to_learn": "8–12 weeks",
        "difficulty": "hard",
        "prerequisite": "Python, basic math/statistics",
        "resources": [
            "Andrew Ng — ML Specialization on Coursera (audit free)",
            "fast.ai — Practical Deep Learning (free)",
            "Kaggle — Learn ML (free courses + datasets)",
        ],
        "resume_tip": "Complete a Kaggle competition and mention rank. Even top 50% is worth listing.",
        "project_idea": "Build end-to-end ML project: data → model → prediction API. Deploy it publicly.",
    },
    "redis": {
        "time_to_learn": "1 week",
        "difficulty": "easy",
        "prerequisite": "Basic backend development",
        "resources": [
            "Redis official docs — redis.io/docs",
            "TechWorld with Nana — Redis Tutorial (YouTube)",
            "Redis University — free online courses",
        ],
        "resume_tip": "Add caching to any existing API with Redis. Mention the latency improvement in resume.",
        "project_idea": "Add Redis caching to an existing REST API.",
    },
    "fastapi": {
        "time_to_learn": "1–2 weeks",
        "difficulty": "easy",
        "prerequisite": "Python",
        "resources": [
            "FastAPI official docs — fastapi.tiangolo.com",
            "Sebastián Ramírez — FastAPI tutorials (YouTube)",
            "TestDriven.io — FastAPI course (partly free)",
        ],
        "resume_tip": "Build a REST API with FastAPI + Pydantic. Mention auto-generated OpenAPI docs.",
        "project_idea": "Build a CRUD API with FastAPI + SQLAlchemy + PostgreSQL.",
    },
}

_DEFAULT_SUGGESTION: dict = {
    "time_to_learn": "2–6 weeks",
    "difficulty": "medium",
    "prerequisite": "Check job requirements for context",
    "resources": [
        "Official documentation",
        "YouTube tutorials (free)",
        "Udemy or Coursera course",
    ],
    "resume_tip": "Learn basics, build a small project, add to resume with GitHub link.",
    "project_idea": "Build a small project that demonstrates this skill.",
}


@dataclass
class SkillGap:
    skill: str
    gap_type: str           # "hard" | "soft"
    candidate_has: str      # What candidate already has that's adjacent (or "none")
    similarity_score: float
    suggestion: dict = field(default_factory=dict)


def enrich_gaps_with_suggestions(
    missing_skills: list[str],
    candidate_skills: list[str],
) -> list[SkillGap]:
    """
    Takes raw missing skill names → returns SkillGap list with rich suggestions.

    Args:
        missing_skills: Skills the candidate is missing from the JD.
        candidate_skills: Skills the candidate already has (for personalization).

    Returns:
        List of SkillGap with enriched suggestion dicts.
    """
    candidate_lower = [s.lower().strip() for s in candidate_skills]
    gaps: list[SkillGap] = []

    for skill in missing_skills:
        skill_key = skill.lower().strip()
        suggestion = dict(_GAP_SUGGESTIONS.get(skill_key, _DEFAULT_SUGGESTION))

        # Personalize: check if candidate already has the prerequisite
        prereq = suggestion.get("prerequisite", "").lower()
        if prereq and prereq != "check job requirements for context":
            prereq_words = [w.strip() for w in prereq.replace("/", ",").split(",")]
            has_prereq = any(
                any(pw in cs or cs in pw for cs in candidate_lower)
                for pw in prereq_words
                if len(pw) > 2
            )
            if has_prereq:
                suggestion["personalized_note"] = (
                    f"✅ You already know {suggestion['prerequisite']} — the main prerequisite! "
                    f"This should be quick to pick up."
                )
            else:
                suggestion["personalized_note"] = None
        else:
            suggestion["personalized_note"] = None

        gaps.append(
            SkillGap(
                skill=skill,
                gap_type="hard",
                candidate_has="none",
                similarity_score=0.0,
                suggestion=suggestion,
            )
        )

    return gaps


def gaps_to_dict(gaps: list[SkillGap]) -> list[dict]:
    """Serialize SkillGap list to JSON-safe list of dicts."""
    return [
        {
            "skill": g.skill,
            "gap_type": g.gap_type,
            "candidate_has": g.candidate_has,
            "similarity_score": g.similarity_score,
            "suggestion": g.suggestion,
        }
        for g in gaps
    ]
