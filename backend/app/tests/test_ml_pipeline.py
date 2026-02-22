from __future__ import annotations

from pathlib import Path

from app.services.ml import (
    QuestionContext,
    QuestionItem,
    compute_eligibility,
    generate_questions,
    parse_resume,
    score_interview,
)


ROOT = Path(__file__).resolve().parents[2]
RESUME_PATH = ROOT / "testdata" / "resumes" / "resume_backend.txt"
JD_PATH = ROOT / "testdata" / "jds" / "jd_backend.txt"


def test_parse_resume_extracts_core_signals() -> None:
    parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")

    skills = set(parsed.skills)
    assert {"python", "fastapi", "mysql", "redis", "docker", "aws"}.issubset(skills)
    assert parsed.estimated_experience_years >= 6
    assert parsed.education_level == "bachelors"
    assert parsed.projects, "Expected projects to be extracted"
    assert parsed.keywords, "Expected keywords to be extracted"


def test_eligibility_formula_is_exact() -> None:
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    jd_text = JD_PATH.read_text(encoding="utf-8")

    parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")

    job_like = {
        "description": jd_text,
        "required_skills": ["python", "fastapi", "mysql", "redis", "docker", "aws"],
        "minimum_experience_years": 4,
        "education_requirement": "Bachelor's degree in Computer Science",
    }
    resume_like = {
        "raw_text": resume_text,
        "skills": parsed.skills,
        "estimated_experience_years": parsed.estimated_experience_years,
        "education_level": parsed.education_level,
    }

    result = compute_eligibility(resume_like=resume_like, job_like=job_like)

    expected = (
        (result.skill_match_percentage * 0.5)
        + (result.experience_match_percentage * 0.3)
        + (result.education_match_percentage * 0.2)
    )
    assert result.eligibility_percentage == round(expected, 2)


def test_skill_overlap_and_missing_skills() -> None:
    resume_like = {
        "raw_text": "Python FastAPI backend APIs",
        "skills": ["python", "fastapi"],
        "estimated_experience_years": 3,
        "education_level": "bachelors",
    }
    job_like = {
        "description": "We need Python, FastAPI, and Redis experience",
        "required_skills": ["python", "fastapi", "redis"],
        "minimum_experience_years": 2,
        "education_requirement": "Bachelor's",
    }

    result = compute_eligibility(resume_like=resume_like, job_like=job_like)

    assert "redis" in result.missing_skills
    assert result.skill_match_percentage == 66.67


def test_question_generation_is_seed_deterministic() -> None:
    context = QuestionContext(
        role="Backend Engineer",
        years_experience=4,
        resume_skills=["python", "fastapi", "mysql", "redis"],
        resume_projects=["Resume Intelligence Service", "Interview Coach"],
        resume_highlights=["Improved latency by 35%"],
        job_required_skills=["python", "fastapi", "redis", "docker"],
        job_responsibilities=["Build microservices and APIs"],
        job_description=JD_PATH.read_text(encoding="utf-8"),
    )

    q1 = generate_questions(context=context, count=6, seed=42)
    q2 = generate_questions(context=context, count=6, seed=42)
    q3 = generate_questions(context=context, count=6, seed=7)

    assert [q.question for q in q1] == [q.question for q in q2]
    assert [q.question for q in q1] != [q.question for q in q3]


def test_scoring_edge_cases() -> None:
    questions = [
        QuestionItem(
            id="q1",
            question="How would you design a FastAPI service?",
            difficulty="medium",
            category="system_design",
            rubric_points=[
                "Explain core concepts of fastapi",
                "Describe trade-offs and best practices for fastapi",
                "Reference real experience applying fastapi",
            ],
        )
    ]

    empty_result = score_interview(questions=questions, answers=[""], transcript="")
    assert empty_result.overall_score == 0.0

    strong_answer = (
        "In FastAPI I define clear Pydantic schemas, add dependency injection for auth, "
        "design REST endpoints, and discuss trade-offs like async I/O, validation, and testing. "
        "In production I used FastAPI with MySQL and Redis and improved latency by 35%."
    )
    strong_result = score_interview(questions=questions, answers=[strong_answer], transcript=strong_answer)

    assert strong_result.overall_score > 50
    assert strong_result.confidence_score > 50
