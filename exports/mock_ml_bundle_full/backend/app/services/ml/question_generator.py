# file name is question_generator.py
from __future__ import annotations

import random
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

from .config import ContentLimits, LLMProvider, LLMTemperature
from .eligibility import _normalize_skills
from .llm_client import BaseLLMClient, create_llm_client
from .models import QuestionContext, QuestionItem
from .validators import sanitize_llm_input, validate_json_size


logger = get_logger(__name__)


def _client_for_provider(provider: str) -> BaseLLMClient | None:
    """Create LLM client for given provider with better error handling."""
    settings = get_settings()
    provider = provider.strip().lower()

    if provider == LLMProvider.GEMINI.value:
        if not settings.gemini_api_key:
            logger.info("gemini_api_key_not_configured")
            return None
        try:
            return create_llm_client(
                provider=LLMProvider.GEMINI.value,
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_api_base,
                model=settings.gemini_model,
                timeout=int(settings.qgen_timeout_seconds),
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_client_init_failed", provider=provider, error=str(exc))
            return None

    if provider in {LLMProvider.GROQ.value, "grok"}:
        if not settings.groq_api_key:
            logger.info("groq_api_key_not_configured")
            return None
        try:
            return create_llm_client(
                provider=LLMProvider.GROQ.value,
                api_key=settings.groq_api_key,
                base_url=settings.groq_api_base,
                model=settings.groq_model,
                timeout=int(settings.qgen_timeout_seconds),
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_client_init_failed", provider=provider, error=str(exc))
            return None

    if provider in {LLMProvider.LOCAL.value, "local_llm"}:
        try:
            return create_llm_client(
                provider=LLMProvider.LOCAL.value,
                api_key=settings.local_llm_api_key,
                base_url=settings.local_llm_base_url,
                model=settings.local_llm_model,
                timeout=int(settings.local_llm_timeout_seconds),
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_client_init_failed", provider=provider, error=str(exc))
            return None

    return None


def _difficulty_bands(years: float) -> list[str]:
    """Return difficulty progression based on experience."""
    if years < 2:
        return ["easy", "easy", "medium", "medium", "medium", "medium", "hard", "hard"]
    if years < 5:
        return ["easy", "medium", "medium", "medium", "hard", "hard", "hard", "hard"]
    return ["medium", "medium", "hard", "hard", "hard", "hard", "expert", "expert"]


def _rubric_for_skill(skill: str, difficulty: str = "medium") -> tuple[str, str, str]:
    """Generate difficulty-appropriate rubric points."""
    if difficulty == "easy":
        return (
            f"Define what {skill} is and when to use it",
            f"Describe basic concepts or features of {skill}",
            f"Give a simple example of using {skill}",
        )
    elif difficulty in ("hard", "expert"):
        return (
            f"Explain advanced patterns and anti-patterns in {skill}",
            f"Discuss scalability, performance, and trade-offs with {skill}",
            f"Reference production experience and lessons learned with {skill}",
        )
    else:  # medium
        return (
            f"Explain core concepts and best practices for {skill}",
            f"Describe trade-offs and when to use {skill}",
            f"Reference practical experience applying {skill}",
        )


def _categories_for_context(context: QuestionContext) -> list[str]:
    """Return appropriate categories based on experience level."""
    categories = ["fundamentals", "scenario", "project", "debugging", "technical"]
    if context.years_experience >= 3:
        categories.append("best_practices")
    if context.years_experience >= 5:
        categories.extend(["system_design", "architecture"])
    if context.years_experience >= 8:
        categories.append("leadership")
    return categories


def _generate_question_by_category(
    category: str, 
    skill: str, 
    role: str, 
    difficulty: str,
    context: QuestionContext,
    index: int,
) -> str:
    """Generate a question based on category with more variety."""
    
    if category == "fundamentals":
        templates = [
            f"Explain the key concepts of {skill} and how they apply to a {role} position.",
            f"What are the fundamental principles of {skill} that every {role} should know?",
            f"Walk me through how {skill} works and why it's important for this {role} role.",
            f"Describe the core features of {skill} and when you would use them in {role} work.",
        ]
        return templates[index % len(templates)]
    
    elif category == "scenario":
        templates = [
            f"You need to implement a feature using {skill}. How would you approach the design, implementation, and testing?",
            f"A {role} task requires you to use {skill} under tight deadlines. What's your approach?",
            f"Imagine you're building a critical system component with {skill}. Walk me through your decision-making process.",
            f"Your team needs to refactor existing code to use {skill}. How would you plan and execute this?",
        ]
        return templates[index % len(templates)]
    
    elif category == "project":
        if context.resume_projects and index < len(context.resume_projects):
            project_hint = context.resume_projects[index % len(context.resume_projects)]
            return f"Tell me about your work on {project_hint}. What was your specific contribution, what challenges did you face, and how did you measure success?"
        return f"Describe a significant project where you used {skill}. What was challenging and what was the measurable impact?"
    
    elif category == "debugging":
        templates = [
            f"A production issue occurs related to {skill}. How would you diagnose the root cause and implement a fix?",
            f"You encounter a critical bug involving {skill} in production. Walk me through your debugging process.",
            f"Performance issues are traced to {skill} usage. How do you identify and resolve the problem?",
            f"An intermittent error occurs with {skill}. How would you troubleshoot and prevent recurrence?",
        ]
        return templates[index % len(templates)]
    
    elif category == "technical":
        templates = [
            f"What are the key trade-offs when using {skill} compared to alternatives in {role} work?",
            f"How does {skill} handle edge cases and what are common pitfalls to avoid?",
            f"Explain the internal workings of {skill} and how it impacts performance.",
            f"Compare different approaches to implementing {skill} functionality. When would you use each?",
        ]
        return templates[index % len(templates)]
    
    elif category == "best_practices":
        templates = [
            f"What are the industry best practices for {skill} that you follow in your work?",
            f"How do you ensure code quality and maintainability when working with {skill}?",
            f"Describe your approach to testing and documenting {skill}-based solutions.",
            f"What standards and patterns do you follow when implementing {skill}?",
        ]
        return templates[index % len(templates)]
    
    elif category == "system_design":
        templates = [
            f"Design a scalable system for a {role} position that uses {skill} as a core component. Explain your architecture choices.",
            f"How would you architect a high-availability system using {skill}? Consider scalability and fault tolerance.",
            f"Design a distributed system that leverages {skill}. What are the key architectural decisions?",
            f"Create a system design for handling millions of requests using {skill}. Walk me through your choices.",
        ]
        return templates[index % len(templates)]
    
    elif category == "architecture":
        templates = [
            f"Explain how you would structure a large-scale application using {skill} principles.",
            f"What architectural patterns work best with {skill} and why?",
            f"How would you design the data flow and component interaction in a system using {skill}?",
            f"Describe your approach to architecting a maintainable solution with {skill}.",
        ]
        return templates[index % len(templates)]
    
    elif category == "leadership":
        templates = [
            f"How would you mentor a junior {role} learning {skill} for the first time?",
            f"Describe how you've introduced {skill} to a team or led a technical initiative around it.",
            f"How do you make technical decisions about using {skill} and get team buy-in?",
            f"Tell me about a time you had to resolve conflicting opinions about {skill} usage.",
        ]
        return templates[index % len(templates)]
    
    else:  # default/general
        return f"Describe your experience with {skill} in the context of {role} work."


def _local_template_questions(*, context: QuestionContext, count: int, seed: int) -> list[QuestionItem]:
    """Generate template questions with improved diversity and relevance."""
    rnd = random.Random(seed)

    # Get skills - prioritize job requirements, then resume skills
    job_skills = _normalize_skills(context.job_required_skills)
    resume_skills = _normalize_skills(context.resume_skills)
    
    # Combine with priority to job requirements
    skills = []
    for skill in job_skills:
        if skill not in skills:
            skills.append(skill)
    for skill in resume_skills:
        if skill not in skills:
            skills.append(skill)
    
    # Add role-based defaults if we don't have enough skills
    if not skills:
        role_lower = context.role.lower()
        if any(kw in role_lower for kw in ["engineer", "developer", "software"]):
            skills = ["programming", "problem solving", "algorithms", "data structures"]
        elif any(kw in role_lower for kw in ["data", "analyst"]):
            skills = ["data analysis", "sql", "statistics", "visualization"]
        elif any(kw in role_lower for kw in ["devops", "sre"]):
            skills = ["deployment", "monitoring", "automation", "infrastructure"]
        else:
            skills = [context.role.lower(), "technical skills", "problem solving", "communication"]
    
    # Shuffle for variety
    rnd.shuffle(skills)

    categories = _categories_for_context(context)
    rnd.shuffle(categories)
    
    difficulties = _difficulty_bands(context.years_experience)

    questions: list[QuestionItem] = []
    for idx in range(count):
        skill = skills[idx % len(skills)]
        category = categories[idx % len(categories)]
        difficulty = difficulties[idx % len(difficulties)]

        question_text = _generate_question_by_category(
            category=category,
            skill=skill,
            role=context.role,
            difficulty=difficulty,
            context=context,
            index=idx,
        )

        rubric = _rubric_for_skill(skill, difficulty)

        questions.append(
            QuestionItem(
                id=f"q{idx + 1}",
                question=question_text,
                difficulty=difficulty,
                category=category,
                rubric_points=rubric,
            )
        )

    return questions


def _build_questions_from_payload(
    *, payload: dict[str, Any], count: int, source: str
) -> list[QuestionItem] | None:
    """Build questions from LLM payload with validation."""
    questions_data = payload.get("questions")
    if not isinstance(questions_data, list):
        logger.warning("qgen_invalid_shape", source=source, type=type(questions_data).__name__)
        return None

    if not questions_data:
        logger.warning("qgen_empty_list", source=source)
        return None

    questions: list[QuestionItem] = []
    for idx, item in enumerate(questions_data[:count]):
        if not isinstance(item, dict):
            logger.warning("qgen_invalid_item", source=source, index=idx)
            continue
            
        question_text = str(item.get("question", "")).strip()
        rubric_points = [str(point).strip() for point in item.get("rubric_points", []) if str(point).strip()][:3]
        
        # Validate quality
        if not question_text or len(question_text) < 10:
            logger.warning("qgen_invalid_question_text", source=source, index=idx)
            continue
        if len(rubric_points) < 2:
            logger.warning("qgen_insufficient_rubric", source=source, index=idx, count=len(rubric_points))
            # Add default rubric points
            rubric_points = ["Clear explanation", "Practical examples", "Technical accuracy"]
        
        questions.append(
            QuestionItem(
                id=f"q{idx + 1}",
                question=question_text,
                difficulty=str(item.get("difficulty", "medium")).strip().lower(),
                category=str(item.get("category", "technical")).strip().lower(),
                rubric_points=tuple(rubric_points),
            )
        )

    if len(questions) < max(2, count // 3):
        logger.warning("qgen_insufficient_questions", source=source, got=len(questions), needed=count)
        return None

    logger.info("qgen_success", source=source, count=len(questions))
    return questions[:count]


def _question_from_payload(*, payload: dict[str, Any], qid: str, source: str) -> QuestionItem | None:
    """Extract single question from payload with validation."""
    if not isinstance(payload, dict):
        logger.warning("qgen_invalid_payload_type", source=source)
        return None
        
    question_text = str(payload.get("question", "")).strip()
    rubric_points = [str(point).strip() for point in payload.get("rubric_points", []) if str(point).strip()][:3]
    
    if not question_text or len(question_text) < 10:
        logger.warning("qgen_invalid_question", source=source, length=len(question_text))
        return None
        
    if len(rubric_points) < 2:
        # Provide defaults
        rubric_points = ["Clear explanation", "Practical application", "Technical depth"]

    return QuestionItem(
        id=qid,
        question=question_text,
        difficulty=str(payload.get("difficulty", "medium")).strip().lower(),
        category=str(payload.get("category", "technical")).strip().lower(),
        rubric_points=tuple(rubric_points),
    )


def _llm_generate_questions(*, context: QuestionContext, count: int, seed: int, provider: str) -> list[QuestionItem] | None:
    """Generate questions using LLM with improved prompting."""
    client = _client_for_provider(provider)
    if not client:
        logger.info("llm_client_unavailable", provider=provider)
        return None

    system_prompt = sanitize_llm_input(
        "You are an expert technical interviewer creating interview questions. "
        "Generate diverse, role-specific questions that test practical knowledge and problem-solving. "
        "Focus on real-world scenarios, not trivia. Questions should be clear and specific. "
        "Return ONLY valid JSON in this exact structure: "
        "{\"questions\": [{\"question\": \"...\", \"category\": \"...\", \"difficulty\": \"...\", \"rubric_points\": [\"...\", \"...\", \"...\"]}]} "
        "Categories: fundamentals, scenario, project, debugging, technical, best_practices, system_design, architecture. "
        "Difficulty: easy, medium, hard, expert. Each question needs exactly 3 rubric points."
    )

    user_payload = {
        "role": context.role,
        "years_experience": context.years_experience,
        "resume_skills": list(context.resume_skills)[:ContentLimits.MAX_SKILLS_CONTEXT],
        "resume_projects": list(context.resume_projects)[:ContentLimits.MAX_PROJECTS_CONTEXT],
        "resume_highlights": list(context.resume_highlights)[:ContentLimits.MAX_HIGHLIGHTS_CONTEXT],
        "job_required_skills": list(context.job_required_skills)[:ContentLimits.MAX_SKILLS_CONTEXT],
        "job_responsibilities": list(context.job_responsibilities)[:ContentLimits.MAX_RESPONSIBILITIES_CONTEXT],
        "job_description": context.job_description[:ContentLimits.MAX_JD_LENGTH],
        "count": count,
        "seed": seed,
        "instructions": "Create questions that assess understanding, problem-solving, and practical experience. Mix different categories and difficulty levels appropriately for the experience level.",
    }

    try:
        payload = validate_json_size(user_payload)
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=payload,
            temperature=LLMTemperature.QUESTION_GENERATION,
            seed=seed,
        )
        if not data:
            logger.warning("llm_qgen_no_data", provider=provider)
            return None
        return _build_questions_from_payload(payload=data, count=count, source=provider)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_qgen_failed", provider=provider, error=str(exc))
        return None


def _llm_generate_single_question(
    *,
    context: QuestionContext,
    asked_questions: list[QuestionItem],
    transcript: str,
    seed: int,
    index: int,
    target_count: int,
    provider: str,
) -> QuestionItem | None:
    """Generate single dynamic question with improved context."""
    client = _client_for_provider(provider)
    if not client:
        return None

    system_prompt = sanitize_llm_input(
        "You are conducting a live technical interview. Generate the next question based on: "
        "(1) the role and job requirements, (2) the candidate's resume, (3) questions already asked, "
        "and (4) the conversation so far. Create a specific, practical question that tests real understanding. "
        "Avoid repeating previous questions. Return ONLY JSON: "
        "{\"question\": \"...\", \"category\": \"...\", \"difficulty\": \"...\", \"rubric_points\": [\"...\", \"...\", \"...\"]}."
    )

    # Build context of what's been asked
    asked_summaries = []
    for q in asked_questions[-5:]:  # Last 5 questions
        asked_summaries.append(f"{q.category}: {q.question[:80]}")

    user_payload = {
        "role": context.role,
        "years_experience": context.years_experience,
        "resume_skills": list(context.resume_skills)[:ContentLimits.MAX_SKILLS_CONTEXT],
        "resume_projects": list(context.resume_projects)[:ContentLimits.MAX_PROJECTS_CONTEXT],
        "job_required_skills": list(context.job_required_skills)[:ContentLimits.MAX_SKILLS_CONTEXT],
        "job_description": context.job_description[:ContentLimits.MAX_JD_LENGTH],
        "already_asked": asked_summaries,
        "transcript_excerpt": transcript[-ContentLimits.MAX_TRANSCRIPT_TAIL:],
        "question_number": index + 1,
        "total_questions": target_count,
        "instructions": f"This is question {index + 1} of {target_count}. Generate a question that hasn't been asked yet and tests a different aspect of their skills.",
    }

    try:
        payload = validate_json_size(user_payload)
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=payload,
            temperature=LLMTemperature.SINGLE_QUESTION,
            seed=seed + index,
        )
        if not data:
            return None
        return _question_from_payload(payload=data, qid=f"q{index + 1}", source=provider)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_single_qgen_failed", provider=provider, error=str(exc))
        return None


def generate_questions(*, context: QuestionContext, count: int, seed: int) -> list[QuestionItem]:
    """Main question generation function with smart fallback."""
    settings = get_settings()
    provider = settings.qgen_provider.strip().lower()

    logger.info("generate_questions_start", provider=provider, count=count)

    # Template-only mode
    if provider in {"template", "rules", "local_template", LLMProvider.TEMPLATE.value}:
        return _local_template_questions(context=context, count=count, seed=seed)

    # Try primary provider
    if provider == LLMProvider.GEMINI.value:
        gemini_questions = _llm_generate_questions(context=context, count=count, seed=seed, provider=provider)
        if gemini_questions:
            logger.info("generate_questions_gemini_success", count=len(gemini_questions))
            return gemini_questions
        logger.info("generate_questions_gemini_failed_trying_local")
        
        # Try local as fallback
        local_questions = _llm_generate_questions(context=context, count=count, seed=seed, provider=LLMProvider.LOCAL.value)
        if local_questions:
            logger.info("generate_questions_local_success", count=len(local_questions))
            return local_questions
        
        logger.info("generate_questions_all_llm_failed_using_template")
        return _local_template_questions(context=context, count=count, seed=seed)

    if provider in {LLMProvider.GROQ.value, "grok"}:
        groq_questions = _llm_generate_questions(context=context, count=count, seed=seed, provider=LLMProvider.GROQ.value)
        if groq_questions:
            logger.info("generate_questions_groq_success", count=len(groq_questions))
            return groq_questions
        
        # Try local as fallback
        local_questions = _llm_generate_questions(context=context, count=count, seed=seed, provider=LLMProvider.LOCAL.value)
        if local_questions:
            logger.info("generate_questions_local_success", count=len(local_questions))
            return local_questions
        
        logger.info("generate_questions_all_llm_failed_using_template")
        return _local_template_questions(context=context, count=count, seed=seed)

    if provider in {LLMProvider.LOCAL.value, "local_llm"}:
        local_questions = _llm_generate_questions(context=context, count=count, seed=seed, provider=LLMProvider.LOCAL.value)
        if local_questions:
            logger.info("generate_questions_local_success", count=len(local_questions))
            return local_questions
        
        logger.info("generate_questions_local_failed_using_template")
        return _local_template_questions(context=context, count=count, seed=seed)

    # Default to template
    logger.info("generate_questions_unknown_provider_using_template", provider=provider)
    return _local_template_questions(context=context, count=count, seed=seed)


def _clone_with_id(question: QuestionItem, qid: str) -> QuestionItem:
    """Clone question with new ID."""
    return QuestionItem(
        id=qid,
        question=question.question,
        difficulty=question.difficulty,
        category=question.category,
        rubric_points=tuple(question.rubric_points),
    )


def generate_dynamic_question(
    *,
    context: QuestionContext,
    asked_questions: list[QuestionItem],
    transcript: str,
    seed: int,
    index: int,
    target_count: int,
) -> QuestionItem:
    """Generate next dynamic question with improved fallback logic."""
    settings = get_settings()
    provider = settings.qgen_provider.strip().lower()

    logger.info("generate_dynamic_question", provider=provider, index=index, target=target_count)

    # Try LLM generation first
    if provider in {LLMProvider.GEMINI.value, LLMProvider.GROQ.value, "grok", LLMProvider.LOCAL.value, "local_llm"}:
        actual_provider = provider if provider != "grok" else LLMProvider.GROQ.value
        question = _llm_generate_single_question(
            context=context,
            asked_questions=asked_questions,
            transcript=transcript,
            seed=seed,
            index=index,
            target_count=target_count,
            provider=actual_provider,
        )
        if question:
            logger.info("generate_dynamic_question_llm_success", provider=actual_provider)
            return question
        logger.info("generate_dynamic_question_llm_failed_using_template", provider=actual_provider)

    # Fallback to smart template selection
    candidates = _local_template_questions(context=context, count=max(target_count * 2, 12), seed=seed + index)
    asked_texts = {q.question.lower() for q in asked_questions}
    
    # Find a question not already asked
    for candidate in candidates:
        if candidate.question.lower() not in asked_texts:
            logger.info("generate_dynamic_question_template_selected", category=candidate.category)
            return _clone_with_id(candidate, f"q{index + 1}")

    # Last resort: modify a template
    if candidates:
        question = candidates[index % len(candidates)]
        logger.info("generate_dynamic_question_template_fallback", category=question.category)
        return _clone_with_id(question, f"q{index + 1}")

    # Ultimate fallback
    logger.warning("generate_dynamic_question_ultimate_fallback")
    return QuestionItem(
        id=f"q{index + 1}",
        question=f"Tell me about your experience with {context.role} responsibilities and a specific challenge you overcame.",
        difficulty="medium",
        category="project",
        rubric_points=("Situation and context", "Your specific actions", "Measurable results"),
    )


def _local_template_followup(question: QuestionItem, answer: str) -> str:
    """Generate template followup with better logic."""
    word_count = len(answer.split())
    
    if not answer.strip():
        return "Could you please elaborate on that? I'd like to hear more details."
    
    if word_count < 20:
        return "That's a good start. Can you expand on that with a specific example and the outcome?"
    
    if word_count < 40:
        return "Interesting. Can you add more technical detail about your approach and what trade-offs you considered?"
    
    # For longer answers, ask for depth
    if question.category in ("system_design", "architecture"):
        return "Good explanation. How would you handle scalability and what would be your monitoring strategy?"
    elif question.category == "debugging":
        return "That makes sense. How would you prevent this issue from happening again in the future?"
    elif question.category == "project":
        return "Thanks for sharing. Can you quantify the impact and tell me what you learned from this?"
    else:
        return "That's helpful. Can you give me a concrete example from your experience that demonstrates this?"


def _llm_generate_followup(*, context: QuestionContext, question: QuestionItem, answer: str, provider: str) -> str | None:
    """Generate followup using LLM."""
    client = _client_for_provider(provider)
    if not client:
        return None

    system_prompt = sanitize_llm_input(
        "You are an interviewer conducting a live interview. Generate ONE concise follow-up question "
        "based on the candidate's answer. The follow-up should: (1) probe for more depth, "
        "(2) ask for specific examples, or (3) explore trade-offs and alternatives. "
        "Keep it professional and specific to their answer. Return ONLY JSON: {\"followup\": \"...\"}."
    )

    user_payload = {
        "role": context.role,
        "question": question.question,
        "rubric_points": list(question.rubric_points),
        "answer": answer[:ContentLimits.MAX_ANSWER_LENGTH],
        "answer_length": len(answer.split()),
        "job_context": context.job_description[:500],
    }

    try:
        payload = validate_json_size(user_payload)
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=payload,
            temperature=LLMTemperature.FOLLOWUP,
        )
        if not data:
            return None
        followup = data.get("followup")
        if isinstance(followup, str) and followup.strip():
            return followup.strip()
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_followup_failed", provider=provider, error=str(exc))
        return None


def _llm_generate_reply(
    *,
    context: QuestionContext,
    question: QuestionItem,
    answer: str,
    transcript: str,
    asked_questions: list[QuestionItem],
    provider: str,
) -> dict[str, Any] | None:
    """Generate interview reply using LLM."""
    client = _client_for_provider(provider)
    if not client:
        return None

    system_prompt = sanitize_llm_input(
        "You are a professional interviewer in a live video interview. "
        "Based on the candidate's answer, provide: (1) a brief acknowledgment (reply), "
        "(2) optionally a follow-up question if the answer needs clarification or more depth, "
        "(3) a decision on whether to move to the next question. "
        "If the answer is strong and complete, set move_on=true and followup=null. "
        "If the answer is weak or vague, ask ONE specific follow-up. "
        "Return ONLY JSON: {\"reply\": \"...\", \"followup\": \"...\" or null, \"move_on\": true/false}."
    )

    user_payload = {
        "role": context.role,
        "question": question.question,
        "difficulty": question.difficulty,
        "rubric_points": list(question.rubric_points),
        "answer": answer[:ContentLimits.MAX_ANSWER_LENGTH],
        "answer_word_count": len(answer.split()),
        "transcript_tail": transcript[-ContentLimits.MAX_TRANSCRIPT_TAIL:],
        "questions_so_far": len(asked_questions),
    }

    try:
        payload = validate_json_size(user_payload)
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=payload,
            temperature=LLMTemperature.REPLY,
        )
        if not data:
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_reply_failed", provider=provider, error=str(exc))
        return None


def generate_interview_reply(
    *,
    context: QuestionContext,
    question: QuestionItem,
    answer: str,
    transcript: str,
    asked_questions: list[QuestionItem],
) -> dict[str, Any]:
    """Generate interview reply with smart fallback."""
    settings = get_settings()
    provider = settings.qgen_provider.strip().lower()

    # Try Gemini first for full reply functionality
    if provider == LLMProvider.GEMINI.value:
        reply_payload = _llm_generate_reply(
            context=context,
            question=question,
            answer=answer,
            transcript=transcript,
            asked_questions=asked_questions,
            provider=provider,
        )
        if isinstance(reply_payload, dict):
            reply = str(reply_payload.get("reply", "")).strip()
            followup = reply_payload.get("followup")
            followup_text = str(followup).strip() if isinstance(followup, str) else None
            move_on = bool(reply_payload.get("move_on", False))
            
            # Validate response
            if not reply and followup_text:
                return {"reply": followup_text, "followup": None, "move_on": False}
            if reply:
                logger.info("generate_reply_gemini_success", move_on=move_on)
                return {"reply": reply, "followup": followup_text, "move_on": move_on}

    # Fallback to simple followup generation
    if provider in {LLMProvider.GROQ.value, "grok", LLMProvider.LOCAL.value, "local_llm"}:
        actual_provider = LLMProvider.GROQ.value if provider == "grok" else provider
        followup = _llm_generate_followup(
            context=context,
            question=question,
            answer=answer,
            provider=actual_provider,
        )
        if followup:
            logger.info("generate_reply_llm_followup_success", provider=actual_provider)
            return {"reply": followup, "followup": None, "move_on": False}

    # Template fallback
    followup = _local_template_followup(question, answer)
    logger.info("generate_reply_template_fallback")
    return {"reply": followup, "followup": None, "move_on": False}


def generate_greeting_reply(*, context: QuestionContext, transcript: str) -> str | None:
    """Generate greeting reply with fallback."""
    settings = get_settings()
    if settings.qgen_provider.strip().lower() != LLMProvider.GEMINI.value:
        return None

    client = _client_for_provider(LLMProvider.GEMINI.value)
    if not client:
        return None

    system_prompt = sanitize_llm_input(
        "You are a friendly professional interviewer on a live video call. "
        "Respond warmly to the candidate's greeting and smoothly transition to starting the interview. "
        "Keep it to 1-2 sentences, professional but personable. "
        "Return ONLY JSON: {\"reply\": \"...\"}."
    )

    user_payload = {
        "role": context.role,
        "candidate_greeting": transcript[-ContentLimits.MAX_TRANSCRIPT_TAIL:],
    }

    try:
        payload = validate_json_size(user_payload)
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=payload,
            temperature=LLMTemperature.GREETING,
        )
        if not data:
            return None
        reply = data.get("reply")
        if isinstance(reply, str) and reply.strip():
            logger.info("generate_greeting_success")
            return reply.strip()
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_greeting_failed", error=str(exc))
        return None
