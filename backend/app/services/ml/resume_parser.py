"""Resume parsing functionality.

This module handles parsing of resume files in various formats (PDF, DOCX, TXT)
and extraction of relevant information.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from io import BytesIO

try:
    import pdfplumber  # Better multi-column extraction than PyPDF2
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False
    from PyPDF2 import PdfReader  # Fallback

from docx import Document

from .config import (
    ACTION_VERBS,
    EDUCATION_KEYWORDS,
    SECTION_HEADINGS,
    SKILL_LEXICON,
    SKILL_SYNONYMS,
    ContentLimits,
    EducationLevel,
    SectionType,
)
from .exceptions import FileReadError, ResumeParseError
from .models import ParsedResume
from .validators import validate_file_path

if TYPE_CHECKING:
    from logging import Logger

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except ImportError:
    spacy = None
    PhraseMatcher = None


@lru_cache(maxsize=1)
def get_nlp() -> spacy.Language | None:
    """Get or create spaCy NLP pipeline.

    Returns:
        spaCy Language object or None if unavailable

    Note:
        This function is cached to avoid reloading the model.
    """
    if not spacy:
        return None

    try:
        # Try to load the pre-trained model
        return spacy.load("en_core_web_sm")
    except OSError:
        # Fall back to blank pipeline if model not available
        return spacy.blank("en")


@lru_cache(maxsize=1)
def get_skill_matcher() -> PhraseMatcher | None:
    """Get or create skill phrase matcher.

    Returns:
        PhraseMatcher configured for skills or None if unavailable
    """
    nlp = get_nlp()
    if not nlp or not PhraseMatcher:
        return None

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in sorted(SKILL_LEXICON)]
    matcher.add("SKILLS", patterns)
    return matcher


def clear_caches() -> None:
    """Clear all cached NLP models and matchers.

    This should be called when you need to free memory or reload models.
    """
    get_nlp.cache_clear()
    get_skill_matcher.cache_clear()


def _read_pdf(file_path: Path, logger: Logger) -> str:
    """Read text from PDF using pdfplumber (better multi-column) with PyPDF2 fallback."""
    if _HAS_PDFPLUMBER:
        return _read_pdf_pdfplumber(file_path, logger)
    return _read_pdf_pypdf2(file_path, logger)


def _read_pdf_pdfplumber(file_path: Path, logger: Logger) -> str:
    """Extract text with pdfplumber — handles multi-column resumes correctly."""
    try:
        import pdfplumber
        pages_text: list[str] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text(
                    x_tolerance=3, y_tolerance=3
                )
                if text:
                    pages_text.append(text)
        if not pages_text:
            raise FileReadError("No text extracted via pdfplumber", {"path": str(file_path)})
        raw = "\n".join(pages_text)
        logger.debug("pdf_extracted_pdfplumber", extra={"chars": len(raw)})
        return raw
    except FileReadError:
        raise
    except Exception as exc:
        logger.warning("pdfplumber_failed_fallback", extra={"error": str(exc)})
        return _read_pdf_pypdf2(file_path, logger)


def _read_pdf_pypdf2(file_path: Path, logger: Logger) -> str:
    """PyPDF2 fallback PDF reader."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file_path))
        pages_text: list[str] = []
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            except Exception as exc:
                logger.warning("pdf_page_extract_failed", extra={"page": page_num, "error": str(exc)})
        if not pages_text:
            raise FileReadError("No text could be extracted from PDF", {"path": str(file_path)})
        return "\n".join(pages_text)
    except Exception as exc:
        if isinstance(exc, FileReadError):
            raise
        raise FileReadError(f"Failed to read PDF: {exc}", {"path": str(file_path)}) from exc


def _read_docx(file_path: Path, logger: Logger) -> str:
    """Read text from DOCX file.

    Args:
        file_path: Path to DOCX file
        logger: Logger instance

    Returns:
        Extracted text content

    Raises:
        FileReadError: If DOCX cannot be read
    """
    try:
        doc = Document(str(file_path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

        if not paragraphs:
            raise FileReadError(
                "No text found in DOCX file",
                {"path": str(file_path)}
            )

        return "\n".join(paragraphs)

    except Exception as exc:
        if isinstance(exc, FileReadError):
            raise
        raise FileReadError(
            f"Failed to read DOCX: {exc}",
            {"path": str(file_path)}
        ) from exc


def _read_txt(file_path: Path, logger: Logger) -> str:
    """Read text from plain text file.

    Args:
        file_path: Path to text file
        logger: Logger instance

    Returns:
        File content

    Raises:
        FileReadError: If text file cannot be read
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        if not content.strip():
            raise FileReadError(
                "Text file is empty",
                {"path": str(file_path)}
            )

        return content

    except Exception as exc:
        if isinstance(exc, FileReadError):
            raise
        raise FileReadError(
            f"Failed to read text file: {exc}",
            {"path": str(file_path)}
        ) from exc


def _normalize_text(text: str) -> str:
    """Normalize text by removing excessive whitespace.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Replace multiple whitespace with single space
    normalized = re.sub(r'\s+', ' ', text)
    return normalized.strip()


def _tokenize(text: str) -> list[str]:
    """Extract word tokens from text.

    Args:
        text: Text to tokenize

    Returns:
        List of lowercase tokens
    """
    # Match words that start with letter and may contain alphanumeric, +, /, ., -
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+/.-]{1,}", text.lower())
    return tokens


def _canonical_skill(skill: str) -> str:
    """Normalize skill name using synonym mapping.

    Args:
        skill: Skill name to normalize

    Returns:
        Canonical skill name
    """
    skill_lower = skill.strip().lower()
    return SKILL_SYNONYMS.get(skill_lower, skill_lower)


def _is_heading(line: str) -> str | None:
    """Check if line is a section heading.

    Args:
        line: Line to check

    Returns:
        Section type if heading detected, None otherwise
    """
    normalized = line.strip().lower().rstrip(":")

    for section, headings in SECTION_HEADINGS.items():
        if normalized in headings:
            return section

    return None


def _split_sections(raw_text: str) -> dict[str, str]:
    """Split resume into sections based on headings.

    Args:
        raw_text: Full resume text

    Returns:
        Dictionary mapping section types to content
    """
    sections: dict[str, list[str]] = {
        section_type.value: [] for section_type in SectionType
    }
    current_section = SectionType.SUMMARY.value

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line is a heading
        heading = _is_heading(stripped)
        if heading:
            current_section = heading
            continue

        # Add line to current section
        sections.setdefault(current_section, []).append(stripped)

    # Convert lists to strings
    return {
        section: "\n".join(lines)
        for section, lines in sections.items()
        if lines
    }


def _extract_skills_spacy(text: str, logger: Logger) -> list[str]:
    """Extract skills using spaCy phrase matching.

    Args:
        text: Text to extract skills from
        logger: Logger instance

    Returns:
        List of extracted skills
    """
    nlp = get_nlp()
    matcher = get_skill_matcher()

    if not nlp or not matcher:
        logger.debug("spacy_unavailable_for_skill_extraction")
        return []

    try:
        doc = nlp(text)
        matches = matcher(doc)
        skills = {doc[start:end].text.lower() for _, start, end in matches}
        return sorted({_canonical_skill(skill) for skill in skills})
    except Exception as exc:
        logger.warning("spacy_skill_extraction_failed", error=str(exc))
        return []


def _extract_skills_from_section(section_text: str) -> list[str]:
    """Extract skills from a skills section using delimiters.

    Args:
        section_text: Text from skills section

    Returns:
        List of extracted skills
    """
    # Split on common delimiters: comma, pipe, slash, newline, bullets
    delimiters = r"[,|/\\\n\u2022\u2023\u25E6\u2043\u2219]+"
    candidates = re.split(delimiters, section_text)

    # Normalize and filter
    normalized = [_canonical_skill(item) for item in candidates]
    return sorted({skill for skill in normalized if skill})


def _extract_skills(
    text: str,
    sections: dict[str, str],
    logger: Logger
) -> list[str]:
    """Extract skills from resume using multiple strategies.

    Args:
        text: Full resume text
        sections: Parsed resume sections
        logger: Logger instance

    Returns:
        List of unique skills
    """
    tokens = _tokenize(text)
    token_set = set(tokens)
    skills: set[str] = set()

    # Strategy 1: spaCy phrase matching
    skills.update(_extract_skills_spacy(text, logger))

    # Strategy 2: Direct lexicon matching
    for skill in SKILL_LEXICON:
        canonical = _canonical_skill(skill)

        # Single-word skills: check token set
        if " " not in canonical and canonical in token_set:
            skills.add(canonical)

        # Multi-word skills: check full text
        if " " in canonical and canonical in text.lower():
            skills.add(canonical)

    # Strategy 3: Parse skills section
    skills_section = sections.get(SectionType.SKILLS.value)
    if skills_section:
        skills.update(_extract_skills_from_section(skills_section))

    return sorted(skills)


def _estimate_experience_years(text: str) -> float:
    """Estimate years of experience from resume text.

    Args:
        text: Resume text

    Returns:
        Estimated years of experience
    """
    text_lower = text.lower()

    # Strategy 1: Look for explicit "X years" mentions
    year_mentions = re.findall(r"(\d+(?:\.\d+)?)\+?\s+years", text_lower)
    if year_mentions:
        years = [float(y) for y in year_mentions]
        return max(years)

    # Strategy 2: Calculate from date ranges
    date_pattern = r"(20\d{2})\s*[-\u2013]\s*(20\d{2}|present|current)"
    date_ranges = re.findall(date_pattern, text_lower)

    if date_ranges:
        current_year = datetime.now(timezone.utc).year
        spans: list[int] = []

        for start, end in date_ranges:
            start_year = int(start)
            end_year = current_year if end in {"present", "current"} else int(end)

            if end_year >= start_year:
                spans.append(end_year - start_year)

        if spans:
            return float(max(spans))

    return 0.0


def _education_level(text: str) -> str | None:
    """Detect highest education level from resume.

    Args:
        text: Resume text

    Returns:
        Education level or None if not detected
    """
    text_lower = text.lower()

    # Check each keyword pattern
    for keyword, level in EDUCATION_KEYWORDS:
        if keyword in text_lower:
            return level

    return None


def _extract_highlights(text: str) -> list[str]:
    """Extract key accomplishments and highlights.

    Args:
        text: Resume text

    Returns:
        List of highlight sentences
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Filter for sentences with action verbs and reasonable length
    filtered: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()

        # Must contain action verb
        if not any(verb in sentence.lower() for verb in ACTION_VERBS):
            continue

        # Must be substantial (at least 6 words)
        if len(sentence.split()) < 6:
            continue

        filtered.append(sentence)

    # Return top highlights
    return filtered[:ContentLimits.MAX_HIGHLIGHTS]


def _extract_projects(sections: dict[str, str], raw_text: str) -> list[str]:
    """Extract project descriptions from resume.

    Args:
        sections: Parsed resume sections
        raw_text: Full resume text

    Returns:
        List of project descriptions
    """
    # First try projects section
    projects_section = sections.get(SectionType.PROJECTS.value)
    if projects_section:
        lines = [
            line.strip()
            for line in projects_section.splitlines()
            if line.strip()
        ]
        return lines[:ContentLimits.MAX_PROJECTS]

    # Fallback: search for project-related lines
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    project_lines = [
        line for line in lines
        if "project" in line.lower() or "github" in line.lower()
    ]

    return project_lines[:8]


def _extract_keywords_spacy(text: str, logger: Logger) -> list[str]:
    """Extract keywords using spaCy NLP.

    Args:
        text: Text to extract keywords from
        logger: Logger instance

    Returns:
        List of keywords
    """
    nlp = get_nlp()
    if not nlp:
        return []

    try:
        doc = nlp(text)
        keywords: set[str] = set()

        # Extract noun chunks
        try:
            for chunk in doc.noun_chunks:
                if len(chunk.text) <= 60:
                    keywords.add(chunk.text.lower())
        except Exception as exc:
            logger.warning("noun_chunk_extraction_failed", error=str(exc))

        # Extract named entities
        for ent in getattr(doc, "ents", []):
            if len(ent.text) <= 60:
                keywords.add(ent.text.lower())

        # Extract important tokens
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
            if token.pos_ in {"NOUN", "PROPN", "VERB"} and len(token.text) > 2:
                keywords.add(token.text.lower())

        return sorted(keywords)[:ContentLimits.MAX_RESUME_KEYWORDS]

    except Exception as exc:
        logger.warning("spacy_keyword_extraction_failed", error=str(exc))
        return []


def parse_resume(
    file_path: Path,
    file_type: str,
    logger: Logger
) -> ParsedResume:
    """Parse resume file and extract information.

    Args:
        file_path: Path to resume file
        file_type: File extension (.pdf, .docx, .txt)
        logger: Logger instance

    Returns:
        ParsedResume object with extracted information

    Raises:
        ResumeParseError: If parsing fails
        FileReadError: If file cannot be read
    """
    # Validate file path
    allowed_extensions = {".pdf", ".docx", ".txt"}
    validate_file_path(file_path, allowed_extensions=allowed_extensions)

    try:
        # Read file based on type
        if file_type == ".pdf":
            raw_text = _read_pdf(file_path, logger)
        elif file_type == ".docx":
            raw_text = _read_docx(file_path, logger)
        else:
            raw_text = _read_txt(file_path, logger)

    except FileReadError:
        raise
    except Exception as exc:
        raise ResumeParseError(
            f"Unexpected error reading file: {exc}",
            {"path": str(file_path), "type": file_type}
        ) from exc

    try:
        # Parse sections
        sections = _split_sections(raw_text)
        normalized = _normalize_text(raw_text)

        # Extract information
        skills = _extract_skills(normalized, sections, logger)

        # Extract keywords (try spaCy first, fallback to tokenization)
        keywords = _extract_keywords_spacy(normalized, logger)
        if not keywords:
            keywords = sorted(set(_tokenize(normalized)))[:ContentLimits.MAX_RESUME_KEYWORDS]

        experience_years = _estimate_experience_years(normalized)
        education = _education_level(normalized)
        projects = _extract_projects(sections, raw_text)
        highlights = _extract_highlights(raw_text)

        # Enrich with Groq structured parsing (async/optional — fails silently)
        groq_data = _parse_with_groq(normalized, logger)

        parsed = ParsedResume(
            raw_text=normalized,
            skills=tuple(skills),
            keywords=tuple(keywords),
            estimated_experience_years=experience_years,
            education_level=education,
            sections=sections,
            projects=tuple(projects),
            highlights=tuple(highlights),
            groq_structured=groq_data,
        )
        return parsed

    except Exception as exc:
        logger.error(
            "resume_parsing_failed",
            error=str(exc),
            path=str(file_path)
        )
        raise ResumeParseError(
            f"Failed to parse resume: {exc}",
            {"path": str(file_path)}
        ) from exc


# ── Groq Structured Parsing ───────────────────────────────────────────────────

_GROQ_BASE = "https://api.groq.com/openai/v1"
_GROQ_RESUME_SCHEMA = """You are a resume parsing expert.
Extract ALL information. Return ONLY valid JSON — no markdown, no code fences, no explanation.

{
  "full_name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin": "string or null",
  "github": "string or null",
  "total_experience_years": 0,
  "current_role": "string or null",
  "professional_summary": "string or null",
  "skills": {
    "technical": ["programming languages, frameworks, libraries"],
    "tools": ["Git, Docker, Postman etc"],
    "databases": ["MySQL, MongoDB etc"],
    "cloud": ["AWS, GCP, Azure etc"]
  },
  "experience": [
    {
      "company": "string",
      "role": "string",
      "start_date": "string",
      "end_date": "string or Present",
      "responsibilities": ["bullet point 1"]
    }
  ],
  "education": [
    {
      "degree": "B.Tech / MCA etc",
      "field": "Computer Science etc",
      "institution": "string",
      "year_of_passing": null
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "1-2 sentences",
      "tech_stack": ["technologies used"]
    }
  ],
  "certifications": ["cert name and issuer"],
  "achievements": ["hackathons, awards"]
}"""


def _parse_with_groq(raw_text: str, logger: Logger) -> dict:
    """
    Call Groq llama-3.1-8b-instant to get structured resume data.
    Returns empty dict on any failure — heuristic parsing is the fallback.
    ~$0.00022 per call, ~1-2s. Completely optional enrichment.
    """
    import os
    import json

    api_key = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL_PARSING", "llama-3.1-8b-instant")

    if not api_key:
        logger.debug("groq_resume_parse: no api key, skipping")
        return {}

    try:
        import httpx

        payload = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _GROQ_RESUME_SCHEMA},
                {"role": "user", "content": f"Parse this resume:\n\n{raw_text[:8000]}"},
            ],
        }
        with httpx.Client(timeout=25) as client:
            resp = client.post(
                f"{_GROQ_BASE}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            logger.info("groq_resume_parse: success", extra={"name": data.get("full_name", "?")})
            return data

    except Exception as exc:
        logger.warning("groq_resume_parse: failed (non-fatal)", extra={"error": str(exc)})
        return {}

