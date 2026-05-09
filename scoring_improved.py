# file name is scoring.py
from __future__ import annotations

from typing import Any, Sequence

from app.core.config import get_settings
from app.core.logging import get_logger

from .config import (
    FILLER_WORDS,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    RUBRIC_STOPWORDS,
    LLMProvider,
    LLMTemperature,
    ScoringWeights,
    Thresholds,
)
from .eligibility import _semantic_similarity
from .llm_client import create_llm_client
from .models import QuestionItem, ScoreResult
from .resume_parser import _tokenize


logger = get_logger(__name__)


def _keyword_coverage(answer: str, rubric_points: Sequence[str]) -> float:
    """Calculate keyword coverage with improved matching."""
    if not answer.strip() or not rubric_points:
        return 0.0
    
    answer_tokens = {token for token in _tokenize(answer) if token not in RUBRIC_STOPWORDS}
    rubric_tokens = {token for token in _tokenize(" ".join(rubric_points)) if token not in RUBRIC_STOPWORDS}
    
    if not answer_tokens or not rubric_tokens:
        return 0.0
    
    # Direct overlap
    overlap = len(answer_tokens.intersection(rubric_tokens))
    direct_coverage = (overlap / len(rubric_tokens)) * 100
    
    # Partial matching for technical terms
    partial_matches = 0
    for rubric_token in rubric_tokens:
        if rubric_token in answer_tokens:
            continue
        for answer_token in answer_tokens:
            if len(rubric_token) > 3 and len(answer_token) > 3:
                if rubric_token in answer_token or answer_token in rubric_token:
                    partial_matches += 0.5
                    break
    
    partial_coverage = (partial_matches / len(rubric_tokens)) * 100
    total_coverage = min(direct_coverage + partial_coverage, 100.0)
    
    return round(total_coverage, 2)


def _coherence(answer: str) -> float:
    """Improved coherence scoring with better heuristics."""
    words = answer.split()
    if not words:
        return 0.0
    
    word_count = len(words)
    
    # Length score - more forgiving curve
    if word_count < 10:
        length_score = (word_count / 10) * 30
    elif word_count < 50:
        length_score = 30 + ((word_count - 10) / 40) * 40
    elif word_count < 150:
        length_score = 70 + ((word_count - 50) / 100) * 30
    else:
        length_score = 100
    
    # Sentence structure score
    sentence_count = max(len([ch for ch in answer if ch in ".!?"]), 1)
    avg_words_per_sentence = word_count / sentence_count
    
    # Optimal range: 10-25 words per sentence
    if 10 <= avg_words_per_sentence <= 25:
        structure_score = 100
    elif avg_words_per_sentence < 10:
        structure_score = (avg_words_per_sentence / 10) * 100
    else:
        structure_score = max(0, 100 - ((avg_words_per_sentence - 25) * 2))
    
    # Combine scores
    coherence = (length_score * 0.7) + (structure_score * 0.3)
    return round(min(coherence, 100.0), 2)


def _sentiment(answer: str) -> float:
    """Improved sentiment analysis."""
    tokens = _tokenize(answer)
    if not tokens:
        return 0.0
    
    pos = sum(1 for token in tokens if token in POSITIVE_WORDS)
    neg = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    
    # Normalize to -1 to 1 range, then shift to 0-1
    sentiment_score = (pos - neg) / max(len(tokens), 1)
    normalized_sentiment = (sentiment_score + 1) / 2  # Now 0 to 1
    
    return normalized_sentiment


def _hesitation_penalty(transcript: str) -> float:
    """Calculate hesitation penalty with improved logic."""
    tokens = _tokenize(transcript)
    if not tokens:
        return 0.0
    
    filler_count = sum(1 for token in tokens if token in FILLER_WORDS)
    filler_ratio = filler_count / len(tokens)
    
    # More forgiving penalty curve
    if filler_ratio < 0.02:  # Less than 2% filler words
        penalty = 0
    elif filler_ratio < 0.05:  # 2-5%
        penalty = (filler_ratio - 0.02) * 10
    else:  # Above 5%
        penalty = 0.3 + (filler_ratio - 0.05) * 5
    
    return min(penalty, Thresholds.MAX_HESITATION_PENALTY)


def _answer_completeness(answer: str, rubric_points: Sequence[str]) -> float:
    """Check if answer addresses multiple aspects of the question."""
    if not answer.strip() or not rubric_points:
        return 0.0
    
    # Check how many rubric points are addressed
    answer_lower = answer.lower()
    addressed_count = 0
    
    for point in rubric_points:
        point_tokens = _tokenize(point)
        if not point_tokens:
            continue
        
        # Check if at least 30% of tokens from this rubric point appear in answer
        matches = sum(1 for token in point_tokens if token in answer_lower)
        if matches >= len(point_tokens) * 0.3:
            addressed_count += 1
    
    completeness = (addressed_count / len(rubric_points)) * 100
    return round(completeness, 2)


def _technical_depth(answer: str, question: QuestionItem) -> float:
    """Assess technical depth based on question difficulty."""
    words = answer.split()
    word_count = len(words)
    
    # Expected word count based on difficulty
    if question.difficulty == "easy":
        expected_min = 20
        expected_optimal = 60
    elif question.difficulty == "medium":
        expected_min = 40
        expected_optimal = 100
    elif question.difficulty == "hard":
        expected_min = 60
        expected_optimal = 150
    else:  # expert
        expected_min = 80
        expected_optimal = 200
    
    # Score based on word count relative to expected
    if word_count < expected_min:
        depth_score = (word_count / expected_min) * 50
    elif word_count < expected_optimal:
        depth_score = 50 + ((word_count - expected_min) / (expected_optimal - expected_min)) * 50
    else:
        depth_score = 100
    
    return round(min(depth_score, 100.0), 2)


def _score_answer(
    answer: str,
    rubric_points: Sequence[str],
    question: QuestionItem,
    *,
    model_name: str,
    logger_context,
) -> tuple[float, dict[str, float]]:
    """Improved answer scoring with multiple dimensions."""
    if not answer.strip():
        return 0.0, {"semantic": 0.0, "coverage": 0.0, "coherence": 0.0, "completeness": 0.0, "depth": 0.0}

    # Calculate all scoring components
    rubric_text = " ".join(rubric_points)
    semantic = _semantic_similarity(answer, rubric_text, model_name, logger_context)
    coverage = _keyword_coverage(answer, rubric_points)
    coherence = _coherence(answer)
    completeness = _answer_completeness(answer, rubric_points)
    depth = _technical_depth(answer, question)

    # Weighted combination with improved weights
    score = (
        (semantic * 0.25) +      # Semantic understanding
        (coverage * 0.20) +      # Keyword coverage
        (coherence * 0.15) +     # Answer structure
        (completeness * 0.25) +  # Addresses rubric points
        (depth * 0.15)           # Technical depth
    )
    
    score = round(max(0.0, min(score, 100.0)), 2)

    # Apply bonuses and penalties
    word_count = len(answer.split())
    
    # Bonus for good answers
    if word_count >= 50 and completeness >= 60 and coherence >= 70:
        score = min(score * 1.1, 100.0)
    
    # Gentle penalty for very short answers (not as harsh)
    if word_count < Thresholds.MIN_ANSWER_WORDS:
        penalty_factor = word_count / Thresholds.MIN_ANSWER_WORDS
        score = score * (0.5 + (penalty_factor * 0.5))  # 50-100% of score
    
    # Only cap score if both semantic and coverage are very low
    if coverage < 10 and semantic < 15:
        score = min(score, 25.0)
    elif coverage < 20 and semantic < 25:
        score = min(score, 50.0)

    score = round(score, 2)

    return score, {
        "semantic": semantic,
        "coverage": coverage,
        "coherence": coherence,
        "completeness": completeness,
        "depth": depth,
    }


def _confidence_score(transcript: str, answers: list[str]) -> float:
    """Improved confidence scoring."""
    if not answers:
        return 0.0
    
    combined_answers = " ".join(answers)
    non_empty = [answer for answer in answers if answer.strip()]
    
    # Answer completeness
    coverage = len(non_empty) / max(len(answers), 1)
    
    # Answer quality
    coherence = _coherence(combined_answers) / 100
    sentiment = _sentiment(combined_answers)
    
    # Calculate average answer length
    total_words = sum(len(answer.split()) for answer in non_empty)
    avg_words = total_words / max(len(non_empty), 1)
    length_factor = min(avg_words / 50, 1.0)  # Normalize to 50 words
    
    # Hesitation penalty (only from transcript)
    hesitation_penalty = _hesitation_penalty(transcript) if transcript else 0
    
    # Combine factors
    base = (
        ScoringWeights.CONFIDENCE_BASE +
        (coherence * ScoringWeights.CONFIDENCE_COHERENCE) +
        (sentiment * ScoringWeights.CONFIDENCE_SENTIMENT) +
        (length_factor * 0.1)
    )
    
    score = max(0.0, min((base * coverage) - hesitation_penalty, 1.0))
    return round(score * 100, 2)


def _gemini_score_interview(
    *,
    questions: list[QuestionItem],
    answers: list[str],
    transcript: str,
) -> ScoreResult | None:
    """Gemini-based interview scoring with better error handling."""
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.info("gemini_api_key_not_configured")
        return None

    try:
        client = create_llm_client(
            provider=LLMProvider.GEMINI.value,
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_api_base,
            model=settings.gemini_model,
            timeout=int(settings.qgen_timeout_seconds),
            logger=logger,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_client_init_failed", provider=LLMProvider.GEMINI.value, error=str(exc))
        return None

    system_prompt = (
        "You are a fair and experienced technical interviewer evaluating a candidate. "
        "Score each answer on a 0-100 scale based on: technical accuracy, completeness, "
        "clarity, and relevance to the question. Be realistic - good answers should get 60-85, "
        "excellent answers 85-100, weak answers 20-50, and very poor answers below 20. "
        "Return ONLY valid JSON with this exact structure: "
        "{"
        "\"overall_score\": number (0-100),"
        "\"confidence_score\": number (0-100),"
        "\"per_question\": ["
        "{\"id\": str, \"score\": number (0-100), \"feedback\": str, "
        "\"key_strengths\": [str], \"key_weaknesses\": [str]}"
        "],"
        "\"strengths\": [str, str, str],"
        "\"weaknesses\": [str, str, str],"
        "\"improvements\": [str, str, str],"
        "\"skill_gaps\": [str, str, str]"
        "}"
    )

    # Prepare input with better structure
    qa_pairs = []
    for i, (q, a) in enumerate(zip(questions, answers)):
        qa_pairs.append({
            "id": q.id,
            "question": q.question,
            "difficulty": q.difficulty,
            "category": q.category,
            "rubric_points": list(q.rubric_points),
            "answer": a if i < len(answers) else "",
        })

    input_payload = {
        "questions_and_answers": qa_pairs,
        "transcript_excerpt": transcript[-2000:] if len(transcript) > 2000 else transcript,
        "evaluation_instructions": "Score fairly based on content quality, not length alone.",
    }

    try:
        data = client.generate(
            system_prompt=system_prompt,
            user_prompt=input_payload,
            temperature=LLMTemperature.SCORING,
        )
        if not data:
            logger.warning("gemini_scoring_returned_none")
            return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("gemini_scoring_failed", error=str(exc))
        return None

    try:
        per_question_raw = data.get("per_question") or []
        per_question: list[dict[str, Any]] = []

        q_map = {q.id: q for q in questions}
        idx_map = {q.id: idx for idx, q in enumerate(questions)}
        
        for item in per_question_raw:
            qid = str(item.get("id", "")).strip()
            question = q_map.get(qid) or (questions[0] if questions else None)
            if not question:
                continue
                
            idx = idx_map.get(question.id, 0)
            answer_text = answers[idx] if idx < len(answers) else ""
            
            # Validate and clamp score
            raw_score = float(item.get("score", 0.0) or 0.0)
            score = max(0.0, min(raw_score, 100.0))
            
            # Extract feedback with defaults
            feedback = str(item.get("feedback", "")).strip()
            if not feedback:
                feedback = "Answer evaluated" if score >= 50 else "Needs improvement"
            
            per_question.append({
                "id": question.id,
                "question": question.question,
                "difficulty": question.difficulty,
                "category": question.category,
                "rubric_points": list(question.rubric_points),
                "answer": answer_text,
                "score": score,
                "components": {"semantic": 0.0, "coverage": 0.0, "coherence": 0.0},
                "feedback": feedback,
            })

        # Validate overall and confidence scores
        overall = float(data.get("overall_score", 0.0) or 0.0)
        overall = max(0.0, min(overall, 100.0))
        
        confidence = float(data.get("confidence_score", 0.0) or 0.0)
        confidence = max(0.0, min(confidence, 100.0))
        
        # If overall is 0 but we have valid question scores, recalculate
        if overall == 0.0 and per_question:
            question_scores = [pq["score"] for pq in per_question]
            if question_scores:
                overall = round(sum(question_scores) / len(question_scores), 2)

        # Extract lists with validation
        strengths = [str(item) for item in data.get("strengths", []) if str(item).strip()]
        weaknesses = [str(item) for item in data.get("weaknesses", []) if str(item).strip()]
        improvements = [str(item) for item in data.get("improvements", []) if str(item).strip()]
        skill_gaps = [str(item) for item in data.get("skill_gaps", []) if str(item).strip()]

        # Generate summary
        if overall >= 75:
            feedback_summary = "Strong performance with good technical understanding"
        elif overall >= 60:
            feedback_summary = "Solid performance with room for improvement"
        elif overall >= 40:
            feedback_summary = "Adequate performance but needs more depth"
        else:
            feedback_summary = "Needs significant improvement in technical knowledge"

        return ScoreResult(
            per_question=tuple(per_question),
            overall_score=overall,
            confidence_score=confidence,
            feedback_summary=feedback_summary,
            strengths=tuple(strengths[:5]) if strengths else ("Completed interview",),
            weaknesses=tuple(weaknesses[:5]) if weaknesses else ("Work on depth",),
            improvements=tuple(improvements[:6]) if improvements else ("Practice more",),
            skill_gaps=tuple(skill_gaps[:6]) if skill_gaps else (),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("gemini_scoring_parse_failed", error=str(exc))
        return None


def score_interview(*, questions: list[QuestionItem], answers: list[str], transcript: str) -> ScoreResult:
    """Main scoring function with improved fallback logic."""
    if not questions:
        logger.warning("score_interview_no_questions")
        return ScoreResult(
            per_question=tuple(),
            overall_score=0.0,
            confidence_score=0.0,
            feedback_summary="No questions provided",
            strengths=tuple(),
            weaknesses=tuple(),
            improvements=tuple(),
            skill_gaps=tuple(),
        )
    
    settings = get_settings()
    
    # Try Gemini first if configured
    if settings.qgen_provider.strip().lower() == LLMProvider.GEMINI.value:
        gemini_result = _gemini_score_interview(questions=questions, answers=answers, transcript=transcript)
        if gemini_result:
            logger.info("score_interview_gemini_success", overall=gemini_result.overall_score)
            return gemini_result
        logger.info("score_interview_gemini_failed_fallback_to_local")

    # Fallback to local scoring
    model_name = settings.embedding_model_name if settings.use_sentence_transformers else ""

    per_question: list[dict[str, Any]] = []
    scores: list[float] = []

    # Pad answers if needed
    padded_answers = answers + [""] * max(0, len(questions) - len(answers))

    for question, answer in zip(questions, padded_answers, strict=False):
        score, components = _score_answer(
            answer, 
            question.rubric_points, 
            question,
            model_name=model_name, 
            logger_context=logger
        )
        scores.append(score)
        
        # Generate contextual feedback
        if score >= 75:
            feedback = "Excellent answer with strong technical depth and clarity"
        elif score >= 60:
            feedback = "Good answer covering key points, could add more detail"
        elif score >= 40:
            feedback = "Adequate answer but lacks depth in some rubric areas"
        elif score >= 20:
            feedback = "Weak answer, needs more technical detail and examples"
        else:
            feedback = "Insufficient answer, please elaborate with specific examples"
        
        per_question.append({
            "id": question.id,
            "question": question.question,
            "difficulty": question.difficulty,
            "category": question.category,
            "rubric_points": list(question.rubric_points),
            "answer": answer,
            "score": score,
            "components": components,
            "feedback": feedback,
        })

    # Calculate overall score
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0
    confidence = _confidence_score(transcript, answers)

    # Identify strengths and weaknesses
    strengths = [
        item["question"][:100] + "..." if len(item["question"]) > 100 else item["question"]
        for item in per_question 
        if item["score"] >= 70
    ][:3]
    
    weaknesses = [
        item["question"][:100] + "..." if len(item["question"]) > 100 else item["question"]
        for item in per_question 
        if item["score"] < 50
    ][:3]

    # Identify skill gaps
    skill_gaps: list[str] = []
    for item in per_question:
        if item["score"] < 50:
            # Add rubric points as skill gaps
            for point in item["rubric_points"][:2]:
                if point not in skill_gaps:
                    skill_gaps.append(point)
                if len(skill_gaps) >= 6:
                    break
        if len(skill_gaps) >= 6:
            break

    # Generate improvements
    improvements = []
    avg_words = sum(len(a.split()) for a in answers if a.strip()) / max(len([a for a in answers if a.strip()]), 1)
    
    if avg_words < 40:
        improvements.append("Provide more detailed answers with specific examples (aim for 50-100 words)")
    
    low_completeness_count = sum(1 for item in per_question if item["components"].get("completeness", 0) < 50)
    if low_completeness_count >= len(questions) * 0.4:
        improvements.append("Address all aspects of each question - review rubric points carefully")
    
    low_depth_count = sum(1 for item in per_question if item["components"].get("depth", 0) < 50)
    if low_depth_count >= len(questions) * 0.4:
        improvements.append("Include technical depth: explain trade-offs, alternatives, and real-world context")
    
    if not improvements:
        improvements.append("Continue practicing technical communication and providing structured answers")
    
    improvements.append("Use the STAR method: Situation, Task, Action, Result")
    improvements.append("Quantify your impact with metrics and specific outcomes where possible")

    # Generate summary
    if overall >= 75:
        feedback_summary = "Excellent performance demonstrating strong technical knowledge"
    elif overall >= 60:
        feedback_summary = "Good performance with solid understanding of key concepts"
    elif overall >= 45:
        feedback_summary = "Satisfactory performance with some areas needing improvement"
    else:
        feedback_summary = "Needs improvement - focus on technical depth and clarity"

    logger.info("score_interview_local_complete", overall=overall, confidence=confidence)

    return ScoreResult(
        per_question=tuple(per_question),
        overall_score=overall,
        confidence_score=confidence,
        feedback_summary=feedback_summary,
        strengths=tuple(strengths) if strengths else ("Attended interview",),
        weaknesses=tuple(weaknesses) if weaknesses else ("Could improve depth",),
        improvements=tuple(improvements[:6]),
        skill_gaps=tuple(skill_gaps[:6]) if skill_gaps else (),
    )
