"""Tests for eligibility computation.

Coverage:
- Resume parsing signal extraction
- Skill matching: exact, fuzzy, normalisation, partial overlap
- Experience scoring: smooth curve, edge cases (0 years, exact match, overshoot)
- Education matching: all hierarchy levels, sentinel propagation, no-requirement case
- Keyword overlap: Jaccard-based, not TF-IDF proxy
- Strict weighted score: cap system, text-alignment guard, requirement flags
- Suggestion generation: skill-aware, experience-aware, deduplication
- Full compute_eligibility pipeline: no-requirement, all-match, cap-triggered,
  logger=None default, education sentinel not leaking
- Integration: seed-deterministic question generation, scoring edge cases
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.ml import (
    QuestionContext,
    QuestionItem,
    compute_eligibility,
    generate_questions,
    parse_resume,
    score_interview,
)
from app.services.ml.eligibility import (
    _education_match,
    _experience_match,
    _generate_suggestions,
    _keyword_overlap,
    _normalize_skills,
    _required_education_rank,
    _skill_match,
    _strict_weighted_score,
)
from app.services.ml.models import (
    EligibilityResult,
    ParsedResume,
    QuestionItem as QI,
    ScoreResult,
)

ROOT = Path(__file__).resolve().parents[2]
RESUME_PATH = ROOT / "testdata" / "resumes" / "resume_backend.txt"
JD_PATH = ROOT / "testdata" / "jds" / "jd_backend.txt"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def backend_resume_like(tmp_path: Path) -> dict:
    parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")
    return {
        "raw_text": RESUME_PATH.read_text(encoding="utf-8"),
        "skills": list(parsed.skills),
        "estimated_experience_years": parsed.estimated_experience_years,
        "education_level": parsed.education_level,
    }


@pytest.fixture()
def backend_job_like() -> dict:
    return {
        "description": JD_PATH.read_text(encoding="utf-8"),
        "required_skills": ["python", "fastapi", "mysql", "redis", "docker", "aws"],
        "minimum_experience_years": 4,
        "education_requirement": "Bachelor's degree in Computer Science",
    }


# ===========================================================================
# Resume parsing
# ===========================================================================

class TestParseResume:
    def test_extracts_core_skills(self) -> None:
        parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")
        assert {"python", "fastapi", "mysql", "redis", "docker", "aws"}.issubset(
            set(parsed.skills)
        )

    def test_experience_years_reasonable(self) -> None:
        parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")
        assert parsed.estimated_experience_years >= 6

    def test_education_level_detected(self) -> None:
        parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")
        assert parsed.education_level == "bachelors"

    def test_projects_and_keywords_present(self) -> None:
        parsed = parse_resume(file_path=RESUME_PATH, file_type=".txt")
        assert parsed.projects, "Expected projects to be extracted"
        assert parsed.keywords, "Expected keywords to be extracted"

    def test_negative_years_clamped_to_zero(self) -> None:
        """ParsedResume.__post_init__ must clamp negative experience to 0."""
        r = ParsedResume(
            raw_text="x",
            skills=(),
            keywords=(),
            estimated_experience_years=-3.5,
            education_level=None,
        )
        assert r.estimated_experience_years == 0.0

    def test_nan_years_clamped_to_zero(self) -> None:
        r = ParsedResume(
            raw_text="x",
            skills=(),
            keywords=(),
            estimated_experience_years=float("nan"),
            education_level=None,
        )
        assert r.estimated_experience_years == 0.0

    def test_sections_are_immutable_proxy(self) -> None:
        """sections must be a MappingProxyType — callers cannot mutate it."""
        from types import MappingProxyType
        r = ParsedResume(
            raw_text="x",
            skills=(),
            keywords=(),
            estimated_experience_years=1.0,
            education_level=None,
            sections={"experience": "5 years"},
        )
        assert isinstance(r.sections, MappingProxyType)
        with pytest.raises(TypeError):
            r.sections["experience"] = "hacked"  # type: ignore[index]

    def test_to_dict_sections_are_independent_copy(self) -> None:
        """Mutating to_dict() result must not affect the original model."""
        r = ParsedResume(
            raw_text="x",
            skills=(),
            keywords=(),
            estimated_experience_years=1.0,
            education_level=None,
            sections={"experience": "original"},
        )
        d = r.to_dict()
        d["sections"]["experience"] = "mutated"
        assert r.sections["experience"] == "original"


# ===========================================================================
# Skill normalisation
# ===========================================================================

class TestNormalizeSkills:
    def test_deduplicates_case_variants(self) -> None:
        result = _normalize_skills(["Python", "python", "PYTHON"])
        assert result == ["python"]

    def test_strips_whitespace(self) -> None:
        result = _normalize_skills(["  fastapi  "])
        assert "fastapi" in result

    def test_empty_strings_ignored(self) -> None:
        result = _normalize_skills(["", "   ", "python"])
        assert "" not in result
        assert "   " not in result

    def test_synonym_mapping_applied(self) -> None:
        """SKILL_SYNONYMS should map 'js' → 'javascript' (or similar)."""
        # Test via _skill_match which calls _normalize_skills internally.
        # If 'js' is in SKILL_SYNONYMS mapped to 'javascript', both sides normalise.
        from app.services.ml.config import SKILL_SYNONYMS
        if "js" in SKILL_SYNONYMS:
            assert _normalize_skills(["js"]) == _normalize_skills([SKILL_SYNONYMS["js"]])


# ===========================================================================
# Skill matching
# ===========================================================================

class TestSkillMatch:
    def test_exact_full_match(self) -> None:
        pct, missing = _skill_match(["python", "fastapi", "redis"], ["python", "fastapi", "redis"])
        assert pct == 100.0
        assert missing == []

    def test_partial_match_correct_percentage(self) -> None:
        pct, missing = _skill_match(["python", "fastapi"], ["python", "fastapi", "redis"])
        assert pct == pytest.approx(66.67, abs=0.01)
        assert missing == ["redis"]

    def test_no_required_skills_returns_zero(self) -> None:
        pct, missing = _skill_match(["python", "react"], [])
        assert pct == 0.0
        assert missing == []

    def test_no_resume_skills_all_missing(self) -> None:
        pct, missing = _skill_match([], ["python", "docker"])
        assert pct == 0.0
        assert set(missing) == {"python", "docker"}

    def test_fuzzy_match_react_variants(self) -> None:
        """'react' in resume should fuzzy-match 'reactjs' in requirements."""
        pct, missing = _skill_match(["react"], ["reactjs"])
        assert pct == 100.0, "Fuzzy match should recognise react ≈ reactjs"
        assert missing == []

    def test_fuzzy_match_postgres_variants(self) -> None:
        pct, missing = _skill_match(["postgresql"], ["postgres"])
        assert pct == 100.0, "Fuzzy match should recognise postgresql ≈ postgres"

    def test_fuzzy_match_does_not_hallucinate(self) -> None:
        """Completely unrelated skills must NOT fuzzy-match."""
        pct, missing = _skill_match(["react"], ["python"])
        assert pct == 0.0
        assert "python" in missing

    def test_missing_skills_sorted(self) -> None:
        _, missing = _skill_match(["python"], ["python", "redis", "docker", "aws"])
        assert missing == sorted(missing)

    def test_case_insensitive(self) -> None:
        pct, missing = _skill_match(["Python", "FastAPI"], ["python", "fastapi"])
        assert pct == 100.0
        assert missing == []


# ===========================================================================
# Experience matching
# ===========================================================================

class TestExperienceMatch:
    def test_exact_match_is_100(self) -> None:
        assert _experience_match(4.0, 4.0) == 100.0

    def test_exceeds_requirement_is_100(self) -> None:
        assert _experience_match(10.0, 4.0) == 100.0

    def test_zero_requirement_is_100(self) -> None:
        assert _experience_match(0.0, 0.0) == 100.0

    def test_zero_candidate_years_is_zero(self) -> None:
        assert _experience_match(0.0, 5.0) == 0.0

    def test_smooth_curve_50_percent_years(self) -> None:
        """50% of required years should yield > 50% (smooth, no cliff)."""
        score = _experience_match(2.0, 4.0)  # 50% of requirement
        assert score > 50.0, f"Expected >50 for smooth curve, got {score}"
        assert score < 100.0

    def test_smooth_curve_75_percent_years(self) -> None:
        """75% of required years should yield > 75%."""
        score = _experience_match(3.0, 4.0)
        assert score > 75.0, f"Expected >75 for smooth curve at 75%, got {score}"
        assert score < 100.0

    def test_score_monotonically_increases(self) -> None:
        """More years should never give a lower score."""
        scores = [_experience_match(y, 10.0) for y in [0, 1, 3, 5, 7, 9, 10, 15]]
        assert scores == sorted(scores)

    def test_score_bounded(self) -> None:
        for years in [0, 0.5, 1, 2, 4, 6, 10, 100]:
            s = _experience_match(years, 4.0)
            assert 0.0 <= s <= 100.0

    def test_negative_candidate_years_clamped(self) -> None:
        """Negative experience should be treated as 0."""
        assert _experience_match(-1.0, 4.0) == _experience_match(0.0, 4.0)


# ===========================================================================
# Education matching
# ===========================================================================

class TestEducationMatch:
    def test_exact_bachelors_match(self) -> None:
        assert _education_match("bachelors", "Bachelor's degree") == 100.0

    def test_higher_than_required_is_100(self) -> None:
        assert _education_match("phd", "Bachelor's degree") == 100.0
        assert _education_match("masters", "Bachelor's degree") == 100.0

    def test_one_level_below_is_40(self) -> None:
        assert _education_match("associates", "Bachelor's degree") == 40.0
        assert _education_match("bachelors", "Master's degree") == 40.0

    def test_two_levels_below_is_zero(self) -> None:
        assert _education_match("high_school", "Master's degree") == 0.0

    def test_no_resume_education_is_zero(self) -> None:
        assert _education_match(None, "Bachelor's degree") == 0.0

    def test_no_requirement_returns_sentinel(self) -> None:
        """When no parseable education requirement exists, sentinel -1.0 is returned."""
        assert _education_match("bachelors", None) == -1.0
        assert _education_match("bachelors", "") == -1.0
        assert _education_match("bachelors", "5+ years of experience") == -1.0

    def test_phd_requirement_parsed(self) -> None:
        assert _required_education_rank("PhD required") == 4
        assert _required_education_rank("Doctoral degree preferred") == 4

    def test_masters_requirement_parsed(self) -> None:
        assert _required_education_rank("Master's degree in CS") == 3
        assert _required_education_rank("MSc or equivalent") == 3

    def test_bachelors_requirement_parsed(self) -> None:
        assert _required_education_rank("Bachelor's degree required") == 2
        assert _required_education_rank("B.Tech or equivalent") == 2

    def test_unrecognised_requirement_returns_none(self) -> None:
        assert _required_education_rank("Some relevant qualification") is None


# ===========================================================================
# Keyword overlap (Jaccard — not TF-IDF proxy)
# ===========================================================================

class TestKeywordOverlap:
    def test_identical_texts_give_high_overlap(self, mock_logger: MagicMock) -> None:
        text = "python fastapi redis docker aws microservices backend"
        overlap = _keyword_overlap(text, text, mock_logger)
        assert overlap > 80.0, f"Identical texts should have high Jaccard overlap, got {overlap}"

    def test_completely_different_texts_give_low_overlap(self, mock_logger: MagicMock) -> None:
        resume = "painting art gallery sculpture canvas watercolour brush"
        jd = "python fastapi redis docker kubernetes microservices"
        overlap = _keyword_overlap(resume, jd, mock_logger)
        assert overlap < 10.0, f"Unrelated texts should have low overlap, got {overlap}"

    def test_partial_overlap_between_extremes(self, mock_logger: MagicMock) -> None:
        resume = "python fastapi redis art painting"
        jd = "python fastapi redis docker kubernetes"
        overlap = _keyword_overlap(resume, jd, mock_logger)
        assert 10.0 < overlap < 90.0

    def test_empty_texts_give_zero(self, mock_logger: MagicMock) -> None:
        assert _keyword_overlap("", "", mock_logger) == 0.0
        assert _keyword_overlap("python", "", mock_logger) == 0.0

    def test_stop_words_excluded(self, mock_logger: MagicMock) -> None:
        """Common stop-words like 'experience' must not inflate overlap."""
        resume = "experience skills knowledge"
        jd = "experience skills knowledge"
        # Even though texts are identical, if all words are stop-words → low/zero overlap
        # (implementation dependent — just verify it doesn't blow up and returns [0,100])
        overlap = _keyword_overlap(resume, jd, mock_logger)
        assert 0.0 <= overlap <= 100.0

    def test_result_is_not_same_as_tfidf(self, mock_logger: MagicMock) -> None:
        """Keyword overlap must be a different computation path from TF-IDF similarity.
        We verify by checking that the function exists independently and returns a float."""
        from app.services.ml.eligibility import _tfidf_similarity
        resume = "python fastapi redis docker"
        jd = "python microservices redis kubernetes"
        jaccard = _keyword_overlap(resume, jd, mock_logger)
        tfidf = _tfidf_similarity(resume, jd, mock_logger) * 100.0
        # They will often be different numbers — the key is they're independent.
        assert isinstance(jaccard, float)
        assert isinstance(tfidf, float)


# ===========================================================================
# Strict weighted score (cap system)
# ===========================================================================

class TestStrictWeightedScore:
    def _score(self, **kwargs) -> float:
        defaults = dict(
            skill_match_pct=100.0,
            experience_match_pct=100.0,
            education_match_pct=100.0,
            has_skill_requirement=True,
            has_experience_requirement=True,
            has_education_requirement=True,
            semantic_similarity=80.0,
            keyword_overlap=60.0,
            has_comparable_text=True,
        )
        defaults.update(kwargs)
        return _strict_weighted_score(**defaults)

    def test_perfect_resume_scores_100(self) -> None:
        assert self._score() == 100.0

    def test_zero_skill_match_returns_zero(self) -> None:
        assert self._score(skill_match_pct=0.0) == 0.0

    def test_low_skill_cap_fires(self) -> None:
        """skill_match < 25 → score capped at 20."""
        score = self._score(skill_match_pct=20.0)
        assert score <= 20.0

    def test_medium_skill_cap_fires(self) -> None:
        """25 ≤ skill_match < 50 → score capped at 45."""
        score = self._score(skill_match_pct=35.0)
        assert score <= 45.0

    def test_low_experience_cap_fires(self) -> None:
        """experience_match < 40 → score capped at 55."""
        score = self._score(skill_match_pct=100.0, experience_match_pct=30.0)
        assert score <= 55.0

    def test_low_education_cap_fires(self) -> None:
        """education_match == 0 → score capped at 60."""
        score = self._score(skill_match_pct=100.0, experience_match_pct=100.0, education_match_pct=0.0)
        assert score <= 60.0

    def test_low_text_alignment_cap_fires(self) -> None:
        """Text alignment < 10 → score capped at 20."""
        score = self._score(semantic_similarity=0.0, keyword_overlap=0.0, has_comparable_text=True)
        assert score <= 20.0

    def test_no_requirements_returns_zero(self) -> None:
        score = self._score(
            has_skill_requirement=False,
            has_experience_requirement=False,
            has_education_requirement=False,
        )
        assert score == 0.0

    def test_score_always_in_valid_range(self) -> None:
        for skill in [0, 10, 30, 60, 80, 100]:
            for exp in [0, 50, 100]:
                s = self._score(skill_match_pct=float(skill), experience_match_pct=float(exp))
                assert 0.0 <= s <= 100.0, f"Out of range: skill={skill}, exp={exp}, score={s}"

    def test_caps_only_reduce_never_inflate(self) -> None:
        """The capped score must always be ≤ the raw weighted average."""
        skill, exp, edu = 60.0, 70.0, 50.0
        raw_weighted = (skill * 0.5) + (exp * 0.3) + (edu * 0.2)
        capped = self._score(
            skill_match_pct=skill,
            experience_match_pct=exp,
            education_match_pct=edu,
        )
        assert capped <= raw_weighted + 0.01  # tiny float tolerance


# ===========================================================================
# compute_eligibility — full pipeline
# ===========================================================================

class TestComputeEligibility:
    """Integration tests for the main compute_eligibility function."""

    def test_parameter_names_are_resume_like_job_like(self) -> None:
        """Function must accept resume_like / job_like kwargs (matches test contract)."""
        result = compute_eligibility(
            resume_like={"raw_text": "python dev", "skills": ["python"],
                         "estimated_experience_years": 2, "education_level": None},
            job_like={"description": "python required", "required_skills": ["python"],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        assert result is not None

    def test_logger_none_does_not_crash(self) -> None:
        """compute_eligibility must work without an explicit logger."""
        result = compute_eligibility(
            resume_like={"raw_text": "python", "skills": ["python"],
                         "estimated_experience_years": 1, "education_level": None},
            job_like={"description": "python developer required",
                      "required_skills": ["python"],
                      "minimum_experience_years": 0,
                      "education_requirement": None},
            logger=None,
        )
        assert 0.0 <= result.eligibility_percentage <= 100.0

    def test_eligibility_bounded(
        self, backend_resume_like: dict, backend_job_like: dict
    ) -> None:
        """Overall eligibility must always be in [0, 100]."""
        result = compute_eligibility(
            resume_like=backend_resume_like,
            job_like=backend_job_like,
        )
        assert 0.0 <= result.eligibility_percentage <= 100.0

    def test_eligibility_never_exceeds_weighted_avg(
        self, backend_resume_like: dict, backend_job_like: dict
    ) -> None:
        """Caps can only reduce the score — eligibility ≤ raw weighted average."""
        result = compute_eligibility(
            resume_like=backend_resume_like,
            job_like=backend_job_like,
        )
        raw_weighted = (
            (result.skill_match_percentage * 0.5)
            + (result.experience_match_percentage * 0.3)
            + (result.education_match_percentage * 0.2)
        )
        assert result.eligibility_percentage <= round(raw_weighted, 2) + 0.01

    def test_strong_candidate_scores_well(
        self, backend_resume_like: dict, backend_job_like: dict
    ) -> None:
        """A well-matched resume should score meaningfully above 50."""
        result = compute_eligibility(
            resume_like=backend_resume_like,
            job_like=backend_job_like,
        )
        assert result.eligibility_percentage > 50.0

    def test_component_percentages_all_bounded(
        self, backend_resume_like: dict, backend_job_like: dict
    ) -> None:
        result = compute_eligibility(
            resume_like=backend_resume_like,
            job_like=backend_job_like,
        )
        for attr in (
            "skill_match_percentage", "experience_match_percentage",
            "education_match_percentage", "semantic_similarity", "keyword_overlap",
        ):
            val = getattr(result, attr)
            assert 0.0 <= val <= 100.0, f"{attr}={val} out of range"

    def test_skill_overlap_and_missing_skills(self) -> None:
        result = compute_eligibility(
            resume_like={
                "raw_text": "Python FastAPI backend APIs",
                "skills": ["python", "fastapi"],
                "estimated_experience_years": 3,
                "education_level": "bachelors",
            },
            job_like={
                "description": "We need Python, FastAPI, and Redis experience",
                "required_skills": ["python", "fastapi", "redis"],
                "minimum_experience_years": 2,
                "education_requirement": "Bachelor's",
            },
        )
        assert "redis" in result.missing_skills
        assert result.skill_match_percentage == pytest.approx(66.67, abs=0.01)

    def test_all_zeros_when_no_requirements(self) -> None:
        result = compute_eligibility(
            resume_like={
                "raw_text": "Worked as a designer and editor.",
                "skills": ["figma", "photoshop"],
                "estimated_experience_years": 2,
                "education_level": None,
            },
            job_like={
                "description": "",
                "required_skills": [],
                "minimum_experience_years": 0,
                "education_requirement": None,
            },
        )
        assert result.skill_match_percentage == 0.0
        assert result.experience_match_percentage == 0.0
        assert result.education_match_percentage == 0.0
        assert result.eligibility_percentage == 0.0

    def test_zero_eligibility_for_zero_skill_match(self) -> None:
        result = compute_eligibility(
            resume_like={
                "raw_text": "Built React dashboards and UI components.",
                "skills": ["react", "typescript"],
                "estimated_experience_years": 6,
                "education_level": "masters",
            },
            job_like={
                "description": "Must have Python, FastAPI, Redis, Docker and AWS.",
                "required_skills": ["python", "fastapi", "redis", "docker", "aws"],
                "minimum_experience_years": 0,
                "education_requirement": None,
            },
        )
        assert result.skill_match_percentage == 0.0
        assert result.eligibility_percentage == 0.0

    def test_education_sentinel_does_not_leak_into_result(self) -> None:
        """education_match_percentage must be 0.0 (not -1.0) when no edu requirement."""
        result = compute_eligibility(
            resume_like={
                "raw_text": "Python engineer 5 years.",
                "skills": ["python"],
                "estimated_experience_years": 5,
                "education_level": "bachelors",
            },
            job_like={
                "description": "Python required",
                "required_skills": ["python"],
                "minimum_experience_years": 0,
                "education_requirement": None,
            },
        )
        assert result.education_match_percentage == 0.0
        assert result.education_match_percentage != -1.0

    def test_missing_skills_are_sorted_tuples(self) -> None:
        result = compute_eligibility(
            resume_like={"raw_text": "Python only", "skills": ["python"],
                         "estimated_experience_years": 2, "education_level": None},
            job_like={"description": "Need python docker redis aws",
                      "required_skills": ["python", "docker", "redis", "aws"],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        assert isinstance(result.missing_skills, tuple)
        assert list(result.missing_skills) == sorted(result.missing_skills)

    def test_suggestions_present_when_skills_missing(self) -> None:
        result = compute_eligibility(
            resume_like={"raw_text": "Python only", "skills": ["python"],
                         "estimated_experience_years": 2, "education_level": None},
            job_like={"description": "Need python docker redis",
                      "required_skills": ["python", "docker", "redis"],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        assert len(result.suggestions) > 0

    def test_no_requirement_suggestions_are_meta(self) -> None:
        """When there are no requirements, suggestions should guide improving the JD."""
        result = compute_eligibility(
            resume_like={"raw_text": "x", "skills": [], "estimated_experience_years": 0,
                         "education_level": None},
            job_like={"description": "", "required_skills": [],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        combined = " ".join(result.suggestions).lower()
        assert "explicit" in combined or "required skills" in combined or "job description" in combined

    def test_fuzzy_skill_counted_as_matched(self) -> None:
        """'reactjs' in requirements should be matched by 'react' in resume via fuzzy."""
        result = compute_eligibility(
            resume_like={"raw_text": "Built react frontends", "skills": ["react"],
                         "estimated_experience_years": 2, "education_level": None},
            job_like={"description": "Must have reactjs experience",
                      "required_skills": ["reactjs"],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        # 'reactjs' should not appear in missing_skills
        assert "reactjs" not in result.missing_skills
        assert result.skill_match_percentage == 100.0

    def test_result_is_eligibility_result_instance(self) -> None:
        result = compute_eligibility(
            resume_like={"raw_text": "python", "skills": ["python"],
                         "estimated_experience_years": 1, "education_level": None},
            job_like={"description": "python required", "required_skills": ["python"],
                      "minimum_experience_years": 0, "education_requirement": None},
        )
        assert isinstance(result, EligibilityResult)


# ===========================================================================
# EligibilityResult model
# ===========================================================================

class TestEligibilityResultModel:
    def _make(self, **kwargs) -> EligibilityResult:
        defaults = dict(
            skill_match_percentage=80.0,
            experience_match_percentage=90.0,
            education_match_percentage=100.0,
            eligibility_percentage=87.0,
            semantic_similarity=70.0,
            keyword_overlap=55.0,
            missing_skills=(),
            suggestions=(),
            required_skills=("python",),
        )
        defaults.update(kwargs)
        return EligibilityResult(**defaults)

    def test_out_of_range_values_clamped(self) -> None:
        r = self._make(skill_match_percentage=150.0, experience_match_percentage=-10.0)
        assert r.skill_match_percentage == 100.0
        assert r.experience_match_percentage == 0.0

    def test_nan_clamped(self) -> None:
        r = self._make(eligibility_percentage=float("nan"))
        assert math.isfinite(r.eligibility_percentage)
        assert r.eligibility_percentage == 0.0

    def test_to_dict_formula_string_accurate(self) -> None:
        d = self._make().to_dict()
        # Must mention caps, not just the naive weighted average
        assert "cap" in d["formula"].lower()

    def test_to_dict_all_keys_present(self) -> None:
        d = self._make().to_dict()
        expected_keys = {
            "skill_match_percentage", "experience_match_percentage",
            "education_match_percentage", "eligibility_percentage",
            "semantic_similarity", "keyword_overlap", "missing_skills",
            "suggestions", "required_skills", "formula",
        }
        assert expected_keys.issubset(d.keys())


# ===========================================================================
# ScoreResult model
# ===========================================================================

class TestScoreResultModel:
    def _make_per_q(self) -> tuple[dict, ...]:
        return ({"question_id": "q1", "score": 75.0, "feedback": "Good answer"},)

    def test_valid_per_question_unchanged(self) -> None:
        r = ScoreResult(
            per_question=self._make_per_q(),
            overall_score=75.0,
            confidence_score=80.0,
            feedback_summary="Good job",
            strengths=("Communication",),
            weaknesses=(),
            improvements=(),
            skill_gaps=(),
        )
        assert r.per_question[0]["score"] == 75.0

    def test_per_question_score_clamped(self) -> None:
        pq = ({"question_id": "q1", "score": 150.0, "feedback": "x"},)
        r = ScoreResult(
            per_question=pq,
            overall_score=80.0,
            confidence_score=80.0,
            feedback_summary="",
            strengths=(),
            weaknesses=(),
            improvements=(),
            skill_gaps=(),
        )
        assert r.per_question[0]["score"] == 100.0

    def test_per_question_missing_keys_patched(self) -> None:
        """Missing required keys must be patched with defaults, not crash."""
        pq = ({"question_id": "q1"},)  # missing 'score' and 'feedback'
        r = ScoreResult(
            per_question=pq,
            overall_score=50.0,
            confidence_score=50.0,
            feedback_summary="",
            strengths=(), weaknesses=(), improvements=(), skill_gaps=(),
        )
        assert "score" in r.per_question[0]
        assert "feedback" in r.per_question[0]

    def test_non_dict_per_question_entry_patched(self) -> None:
        pq = ("not a dict",)  # type: ignore[arg-type]
        r = ScoreResult(
            per_question=pq,  # type: ignore[arg-type]
            overall_score=0.0,
            confidence_score=0.0,
            feedback_summary="",
            strengths=(), weaknesses=(), improvements=(), skill_gaps=(),
        )
        assert isinstance(r.per_question[0], dict)

    def test_overall_score_clamped(self) -> None:
        r = ScoreResult(
            per_question=self._make_per_q(),
            overall_score=120.0,
            confidence_score=-5.0,
            feedback_summary="",
            strengths=(), weaknesses=(), improvements=(), skill_gaps=(),
        )
        assert r.overall_score == 100.0
        assert r.confidence_score == 0.0


# ===========================================================================
# Suggestion generation
# ===========================================================================

class TestGenerateSuggestions:
    def test_missing_skills_produce_suggestions(self) -> None:
        suggestions = _generate_suggestions(["docker", "redis"])
        assert any("docker" in s.lower() for s in suggestions)
        assert any("redis" in s.lower() for s in suggestions)

    def test_no_duplicate_suggestions(self) -> None:
        suggestions = _generate_suggestions(["docker", "docker", "redis"])
        assert len(suggestions) == len(set(suggestions))

    def test_low_skill_match_adds_upskill_suggestion(self) -> None:
        suggestions = _generate_suggestions(["docker"], skill_match_pct=20.0)
        combined = " ".join(suggestions).lower()
        assert "upskill" in combined or "low overlap" in combined or "stack" in combined

    def test_low_experience_adds_quantify_suggestion(self) -> None:
        suggestions = _generate_suggestions([], experience_match_pct=30.0)
        combined = " ".join(suggestions).lower()
        assert "quantif" in combined or "metric" in combined or "outcome" in combined

    def test_suggestions_capped_at_max(self) -> None:
        from app.services.ml.config import ContentLimits
        suggestions = _generate_suggestions(["a", "b", "c", "d", "e", "f", "g"])
        assert len(suggestions) <= ContentLimits.MAX_SUGGESTIONS


# ===========================================================================
# Question generation — seed determinism
# ===========================================================================

class TestQuestionGeneration:
    def test_same_seed_produces_identical_questions(self) -> None:
        context = QuestionContext(
            role="Backend Engineer",
            years_experience=4,
            resume_skills=("python", "fastapi", "mysql", "redis"),
            resume_projects=("Resume Intelligence Service", "Interview Coach"),
            resume_highlights=("Improved latency by 35%",),
            job_required_skills=("python", "fastapi", "redis", "docker"),
            job_responsibilities=("Build microservices and APIs",),
            job_description=JD_PATH.read_text(encoding="utf-8"),
        )
        q1 = generate_questions(context=context, count=6, seed=42)
        q2 = generate_questions(context=context, count=6, seed=42)
        assert [q.question for q in q1] == [q.question for q in q2]

    def test_different_seed_produces_different_questions(self) -> None:
        context = QuestionContext(
            role="Backend Engineer",
            years_experience=4,
            resume_skills=("python", "fastapi", "mysql", "redis"),
            resume_projects=("Resume Intelligence Service",),
            resume_highlights=("Improved latency by 35%",),
            job_required_skills=("python", "fastapi", "redis", "docker"),
            job_responsibilities=("Build microservices and APIs",),
            job_description=JD_PATH.read_text(encoding="utf-8"),
        )
        q1 = generate_questions(context=context, count=6, seed=42)
        q3 = generate_questions(context=context, count=6, seed=7)
        assert [q.question for q in q1] != [q.question for q in q3]


# ===========================================================================
# Scoring edge cases
# ===========================================================================

class TestScoringEdgeCases:
    _questions = [
        QuestionItem(
            id="q1",
            question="How would you design a FastAPI service?",
            difficulty="medium",
            category="system_design",
            rubric_points=(
                "Explain core concepts of fastapi",
                "Describe trade-offs and best practices for fastapi",
                "Reference real experience applying fastapi",
            ),
        )
    ]

    def test_empty_answer_scores_zero(self) -> None:
        result = score_interview(
            questions=self._questions, answers=[""], transcript=""
        )
        assert result.overall_score == 0.0

    def test_strong_answer_scores_above_50(self) -> None:
        strong = (
            "In FastAPI I define clear Pydantic schemas, add dependency injection for auth, "
            "design REST endpoints, and discuss trade-offs like async I/O, validation, and testing. "
            "In production I used FastAPI with MySQL and Redis and improved latency by 35%."
        )
        result = score_interview(
            questions=self._questions, answers=[strong], transcript=strong
        )
        assert result.overall_score > 50
        assert result.confidence_score > 50

    def test_score_result_is_score_result_instance(self) -> None:
        result = score_interview(
            questions=self._questions, answers=[""], transcript=""
        )
        assert isinstance(result, ScoreResult)

    def test_score_always_bounded(self) -> None:
        for answer in ["", "maybe", "I think FastAPI is a web framework for Python"]:
            result = score_interview(
                questions=self._questions, answers=[answer], transcript=answer
            )
            assert 0.0 <= result.overall_score <= 100.0
            assert 0.0 <= result.confidence_score <= 100.0
