:8000/api/candidate/resumes:1 
 Failed to load resource: the server responded with a status of 400 (Bad Request)

api.ts:35 
 POST http://localhost:8000/api/candidate/resumes 400 (Bad Request)
apiFetch	@	api.ts:35
apiUpload	@	api.ts:79
handleUpload	@	Resumes.tsx:49
import os
import sys

# Add backend directory to sys.path to allow imports
sys.path.insert(0, r"c:\Users\jatin sharma\OneDrive\Desktop\hirenexus\backend")

# Need to load .env variables
from dotenv import load_dotenv
load_dotenv(r"c:\Users\jatin sharma\OneDrive\Desktop\hirenexus\backend\.env")

from app.services.ml.jd_parser import parse_jd_with_groq
from app.services.ml.resume_parser import _parse_with_groq
from app.services.ml.eligibility import compute_eligibility
from app.services.ml.gap_analyzer import enrich_gaps_with_suggestions, gaps_to_dict
import json
import logging

logging.basicConfig(level=logging.ERROR)

jd_text = """
Our is Client is a largest Top 5 Software giant in India, with over 11.3 USD billion dollars revenue...
Job Title: oracle SQL + Data Warehousing
Exp : 8+ years
Location: Chennai & Bangalore
Salary: As per market
Notice Period: 0-15 days / serving
Mode of Hire: Contract

Job Title: Oracle SQL Developer / Data Warehouse Engineer
Job Summary
We are seeking a skilled Oracle SQL Developer with strong experience in Data Warehousing concepts, ETL processes, and performance tuning...

Required Skills
• Strong proficiency in Oracle SQL and PL/SQL
• Good understanding of Data Warehousing concepts (fact tables, dimension tables, SCDs, etc.)
• Experience with ETL tools (e.g., Informatica, ODI, Talend, or similar)
• Knowledge of performance tuning and query optimization
• Understanding of indexing, partitioning, and database design
• Experience working with large-scale databases

Preferred Skills
• Experience with Oracle Data Integrator (ODI) or Informatica PowerCenter
• Knowledge of BI tools (Tableau, Power BI, OBIEE)
• Familiarity with cloud platforms (AWS, Azure, Oracle Cloud)
• Basic understanding of Python or scripting for data processing
"""

resume_text = """
Jatin Jagdish Sharma
+91 97693 96743 | jatin97693@gmail.com | GitHub: (link)| LinkedIn: link
PROFESSIONAL SUMMARY
Aspiring Machine Learning Engineer (2027) with strong foundations in AI/ML, deep learning, and distributed systems.
...
CORE SKILLS
Programming: Python, C, C++, Java, JavaScript, SQL
AI/ML & Deep Learning: Natural Language Processing (NLP), TF-IDF, Scikit-learn, LLM Applications,
RAG Pipelines, Prompt Engineering, Model Fine-tuning (basics), GenAI Systems
Systems & Engineering: REST APIs, WebSockets, Distributed Systems (basics), Scalable Architectures, ETLPipelines
Cloud & MLOps: AWS (Lambda, API Gateway, S3, DynamoDB, Cognito), Docker, Git, CI/CD
Databases: MySQL, MongoDB, DynamoDB

EXPERIENCE
Hydrus.ai — Python Developer Intern
Jan 2025 – Dec 2025 | Remote
* Built scalable data pipelines and automated workflows
* Developed ETL pipelines for data cleaning, transformation

PROJECTS
Nyaya Mitra — AI Legal Assistant (AWS AI for Bharat Hackathon)
GenAI, LLM, Distributed Systems, AWS

HireNexus — AI Recruitment Automation Platform
* Built AI system for resume parsing, job matching, and automated candidate evaluation
"""

print("1. Parsing JD with Groq...")
parsed_jd = parse_jd_with_groq(jd_text)

print("\n2. Parsing Resume with Groq...")
parsed_resume = _parse_with_groq(resume_text, logging.getLogger("test"))

job_req_skills = parsed_jd.get("required_skills", [])
print(f"\n[Groq Extracted JD Skills]: {job_req_skills}")

resume_skills = parsed_resume.get("skills", [])
print(f"[Groq Extracted Resume Skills]: {resume_skills}")

print("\n3. Computing Eligibility...")
job_like = {
    "description": jd_text,
    "required_skills": job_req_skills,
    "minimum_experience_years": parsed_jd.get("experience_years", 0.0),
    "education_requirement": None,
}

resume_like = {
    "raw_text": resume_text,
    "skills": resume_skills,
    "estimated_experience_years": parsed_resume.get("experience_months", 0) / 12,
    "education_level": None,
    "parsed_json": {"groq_structured": parsed_resume},
}

result = compute_eligibility(resume_like=resume_like, job_like=job_like)

print(f"\n--- SCORE BREAKDOWN ---")
print(f"Eligibility Score: {result.eligibility_percentage}%")
print(f"Skill Match: {result.skill_match_percentage}%")
print(f"Experience Match: {result.experience_match_percentage}%")

print(f"\n--- MISSING SKILLS ---")
print(result.missing_skills)

print("\n--- ENRICHED GAP ANALYSIS ---")
enriched_gaps = enrich_gaps_with_suggestions(list(result.missing_skills), resume_skills)
print(json.dumps(gaps_to_dict(enriched_gaps), indent=2))
