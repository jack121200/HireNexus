# rag/evaluate_rag.py
# Implements Step 8: Accuracy Evaluation without crashing the local memory (LLM-as-a-judge)
import os
import json
import asyncio
from dotenv import load_dotenv

# Ensure we use backend/.env to pick up GROQ
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.services.career_rag.query_engine import query_career_guide
from app.services.career_rag.llm_client import generate

EVAL_QA_SET = [
    {"q": "What skills should a fresher backend engineer learn?", "role": "backend-developer", "level": "fresher"},
    {"q": "Frontend Developer roadmap for 2025 please.", "role": "frontend-developer", "level": "fresher"},
    {"q": "What is the typical salary for a data scientist in India?", "role": "data-scientist", "level": "experienced"},
    {"q": "How to prepare for Android Development interviews?", "role": "android-developer", "level": "all"},
]

JUDGE_PROMPT_TEMPLATE = """
As an impartial Evaluation Judge, rate the RAG response based on the provided Context and Question.

QUESTION: {question}
RAG CONTEXT USED: {context}
GENERATED ANSWER: {answer}

Provide exactly two numbers out of 10.
1. FAITHFULNESS (1-10): How grounded is the answer in the provided context?
2. RELEVANCE (1-10): How well does the answer directly address the user's question?

Format your response strictly as valid JSON:
{{"faithfulness": 8, "relevance": 9, "reasoning": "brief explanation"}}
"""

async def evaluate():
    print(f"🔥 Starting RAG Evaluation Model for {len(EVAL_QA_SET)} questions...\n")
    
    total_faithfulness = 0
    total_relevance = 0
    
    for i, test in enumerate(EVAL_QA_SET):
        print(f"[{i+1}/{len(EVAL_QA_SET)}] Testing: '{test['q']}'")
        print(f"    - Role Slug: {test['role']}")
        
        # 1. Fetch RAG output directly from local API logic
        user_profile = {"target_role": test["role"], "level": test["level"]}
        rag_data = await query_career_guide(test["q"], user_profile)
        
        # We need the verbatim context that was used for the LLM judge
        chunks_text = "\n".join([f"- {s['text']}" for s in rag_data.get('sources', [])])
        
        # 2. Ask Groq (LLaMA 3) to Judge the Output
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
            question=test["q"],
            context=chunks_text[:1500] + "...(truncated)", # prevent judge context overflow
            answer=rag_data.get('response', '')[:1500] + "...(truncated)"
        )
        
        try:
            eval_result_str = await generate(
                prompt=judge_prompt,
                system_instruction="You are a strict data evaluation machine. Output valid JSON only.",
                temperature=0.0,
                max_tokens=256
            )
            
            # Very basic cleanup incase LLM wraps JSON in markdown code blocks
            clean_str = eval_result_str.strip().replace("```json", "").replace("```", "")
            scores = json.loads(clean_str)
            
            f_score = scores.get("faithfulness", 0)
            r_score = scores.get("relevance", 0)
            total_faithfulness += f_score
            total_relevance += r_score
            
            print(f"    ➡️  Faithfulness: {f_score}/10 | Relevance: {r_score}/10")
            print(f"    💡 Reason: {scores.get('reasoning', '')[:100]}...\n")
            
        except Exception as e:
            print(f"    ❌ Evaluation failed to parse: {e}")
            
    print("\n==================================")
    print("🏆 FINAL AGGREGATE RAG SCORES")
    print("==================================")
    print(f"Faithfulness Metric: {(total_faithfulness / (len(EVAL_QA_SET)*10))*100:.1f}%")
    print(f"Answer Relevance:    {(total_relevance / (len(EVAL_QA_SET)*10))*100:.1f}%")
    print("Note: Scores > 85% indicate highly production-ready performance.")

if __name__ == "__main__":
    asyncio.run(evaluate())
