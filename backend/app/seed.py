from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.application_service import apply_to_job, update_application_status
from app.services.auth_service import get_user_by_email, register_candidate, register_hr
from app.services.chat_service import ensure_conversation_for_job, send_message
from app.services.interview_service import complete_interview, ensure_interview_questions
from app.services.job_service import create_job
from app.services.ml import parse_resume
from app.services.resume_service import get_primary_resume

DEFAULT_PASSWORD = "StrongPass!123"

HR_SEED = [
    {
        "full_name": "Aarav Mehta",
        "email": "hr@novafin.ai",
        "company_name": "NovaFin",
        "company_website": "https://novafin.ai",
        "jobs": [
            {
                "title": "Backend Engineer",
                "description": "Build FastAPI services powering fintech workflows and ledger integrity.",
                "responsibilities": "Design APIs, optimize performance, and improve reliability.",
                "required_skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "SQLAlchemy"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Risk Modeling Analyst",
                "description": "Develop risk models for credit and fraud detection across lending products.",
                "responsibilities": "Own model metrics, explainability, and monitoring.",
                "required_skills": ["Python", "Statistics", "Risk Modeling", "SQL", "Pandas"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Bengaluru",
                "employment_type": "Full-time",
            },
            {
                "title": "Data Analyst",
                "description": "Create dashboards for finance KPIs, cohort analysis, and operational insights.",
                "responsibilities": "Build BI reports and maintain data quality checks.",
                "required_skills": ["SQL", "Power BI", "Python", "Excel"],
                "minimum_experience_years": 1,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Frontend Engineer",
                "description": "Ship user-facing fintech dashboards with high performance and clarity.",
                "responsibilities": "Own UI components, accessibility, and API integration.",
                "required_skills": ["React", "TypeScript", "Tailwind", "REST"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Mumbai",
                "employment_type": "Full-time",
            },
            {
                "title": "DevOps Engineer",
                "description": "Maintain CI/CD, infrastructure, and monitoring for regulated systems.",
                "responsibilities": "Automate deployments and improve uptime.",
                "required_skills": ["AWS", "Docker", "Kubernetes", "Terraform"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Nisha Kapoor",
        "email": "hr@pulsebridge.health",
        "company_name": "PulseBridge Health",
        "company_website": "https://pulsebridge.health",
        "jobs": [
            {
                "title": "Health Data Engineer",
                "description": "Build HIPAA-compliant pipelines for clinical data and analytics.",
                "responsibilities": "Design ETL, enforce data governance, and monitor quality.",
                "required_skills": ["Python", "ETL", "Snowflake", "Airflow"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Hyderabad",
                "employment_type": "Full-time",
            },
            {
                "title": "Product Designer",
                "description": "Create patient-first experiences for telehealth workflows.",
                "responsibilities": "Design systems, prototyping, and usability tests.",
                "required_skills": ["Figma", "UX", "Design Systems"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Clinical Ops Analyst",
                "description": "Analyze care operations and recommend process improvements.",
                "responsibilities": "Track metrics and partner with care teams.",
                "required_skills": ["SQL", "Excel", "Healthcare Ops"],
                "minimum_experience_years": 1,
                "education_requirement": "bachelor",
                "location": "Delhi",
                "employment_type": "Full-time",
            },
            {
                "title": "Frontend Engineer",
                "description": "Build care team dashboards with React and data visualization.",
                "responsibilities": "Implement UI modules and integrate APIs.",
                "required_skills": ["React", "TypeScript", "D3"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "QA Automation Engineer",
                "description": "Automate testing for patient-facing and clinician workflows.",
                "responsibilities": "Create test suites and CI test gates.",
                "required_skills": ["Selenium", "Playwright", "CI/CD"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Rohit Sharma",
        "email": "hr@skillorbit.io",
        "company_name": "SkillOrbit",
        "company_website": "https://skillorbit.io",
        "jobs": [
            {
                "title": "Full-Stack Engineer",
                "description": "Build learning journeys, progress tracking, and content delivery systems.",
                "responsibilities": "Own frontend and backend feature delivery.",
                "required_skills": ["React", "Node.js", "PostgreSQL"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "AI Tutor Engineer",
                "description": "Integrate AI tutoring with adaptive content recommendations.",
                "responsibilities": "Work with ML and product teams to ship AI features.",
                "required_skills": ["Python", "LLM", "APIs", "Prompting"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Curriculum Data Specialist",
                "description": "Map skills to curriculum and assess learning outcomes.",
                "responsibilities": "Build competency frameworks and assessments.",
                "required_skills": ["Data Analysis", "Curriculum", "Excel"],
                "minimum_experience_years": 1,
                "education_requirement": "bachelor",
                "location": "Pune",
                "employment_type": "Full-time",
            },
            {
                "title": "Product Designer",
                "description": "Craft learner-first experiences with strong usability.",
                "responsibilities": "Wireframes, prototypes, and testing.",
                "required_skills": ["Figma", "UX", "Research"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Growth Marketer",
                "description": "Drive acquisition and activation for learning cohorts.",
                "responsibilities": "Run campaigns and track funnel metrics.",
                "required_skills": ["Performance Marketing", "Analytics", "Content"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Meera Iyer",
        "email": "hr@cartcraft.com",
        "company_name": "CartCraft",
        "company_website": "https://cartcraft.com",
        "jobs": [
            {
                "title": "Marketplace Manager",
                "description": "Own seller onboarding, merchandising, and marketplace growth.",
                "responsibilities": "Drive catalog health and seller success.",
                "required_skills": ["Marketplace", "Operations", "Analytics"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Bengaluru",
                "employment_type": "Full-time",
            },
            {
                "title": "Supply Chain Analyst",
                "description": "Optimize inventory and delivery timelines across regions.",
                "responsibilities": "Build forecasting models and track KPIs.",
                "required_skills": ["SQL", "Excel", "Supply Chain"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Chennai",
                "employment_type": "Full-time",
            },
            {
                "title": "Mobile Engineer",
                "description": "Build fast, reliable shopping experiences on mobile.",
                "responsibilities": "Ship app features and improve performance.",
                "required_skills": ["React Native", "TypeScript", "Mobile"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Customer Success Lead",
                "description": "Improve customer retention and satisfaction.",
                "responsibilities": "Run onboarding and lifecycle campaigns.",
                "required_skills": ["Customer Success", "CRM", "Communication"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Data Engineer",
                "description": "Build pipelines for sales and behavioral analytics.",
                "responsibilities": "ETL and data quality checks.",
                "required_skills": ["Python", "SQL", "Airflow"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Vikram Rao",
        "email": "hr@cloudmetric.com",
        "company_name": "CloudMetric",
        "company_website": "https://cloudmetric.com",
        "jobs": [
            {
                "title": "Solutions Engineer",
                "description": "Support enterprise customers with onboarding and technical enablement.",
                "responsibilities": "Deliver demos and integrations.",
                "required_skills": ["APIs", "SaaS", "Customer Enablement"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Platform Engineer",
                "description": "Own infrastructure, observability, and platform reliability.",
                "responsibilities": "Improve uptime and deployment velocity.",
                "required_skills": ["AWS", "Kubernetes", "Terraform"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Security Analyst",
                "description": "Monitor alerts, run investigations, and improve security posture.",
                "responsibilities": "Threat detection and response.",
                "required_skills": ["SIEM", "Security", "Incident Response"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "QA Automation Engineer",
                "description": "Automate regression suites and improve release confidence.",
                "responsibilities": "Testing, CI, and quality ownership.",
                "required_skills": ["Playwright", "Selenium", "CI/CD"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Account Executive",
                "description": "Drive SaaS revenue with mid-market and enterprise accounts.",
                "responsibilities": "Pipeline management and closing.",
                "required_skills": ["Sales", "SaaS", "Negotiation"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Anika Bose",
        "email": "hr@routepulse.io",
        "company_name": "RoutePulse",
        "company_website": "https://routepulse.io",
        "jobs": [
            {
                "title": "Operations Analyst",
                "description": "Analyze delivery performance and optimize routing strategies.",
                "responsibilities": "Track KPIs and optimize logistics operations.",
                "required_skills": ["SQL", "Excel", "Operations"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Delhi",
                "employment_type": "Full-time",
            },
            {
                "title": "Fleet Optimization Engineer",
                "description": "Build optimization algorithms for fleet utilization and routing.",
                "responsibilities": "Model optimization constraints and outcomes.",
                "required_skills": ["Python", "Optimization", "Algorithms"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "GIS Specialist",
                "description": "Own geospatial data layers and mapping accuracy.",
                "responsibilities": "Maintain GIS datasets and tooling.",
                "required_skills": ["GIS", "QGIS", "Spatial Data"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Pune",
                "employment_type": "Full-time",
            },
            {
                "title": "Backend Engineer",
                "description": "Build routing services and operational APIs.",
                "responsibilities": "Design APIs and improve performance.",
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Site Reliability Engineer",
                "description": "Ensure high availability for logistics systems.",
                "responsibilities": "Monitoring, incident response, and automation.",
                "required_skills": ["SRE", "AWS", "Kubernetes"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Karan Malhotra",
        "email": "hr@streamforge.tv",
        "company_name": "StreamForge",
        "company_website": "https://streamforge.tv",
        "jobs": [
            {
                "title": "Video Pipeline Engineer",
                "description": "Build transcoding and streaming workflows at scale.",
                "responsibilities": "Optimize encoding performance and quality.",
                "required_skills": ["FFmpeg", "Streaming", "AWS"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "ML Recommendation Engineer",
                "description": "Build personalization models for content discovery.",
                "responsibilities": "Train and deploy recommendation systems.",
                "required_skills": ["Python", "ML", "Recommendation Systems"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Content Ops Manager",
                "description": "Manage content ingest pipelines and metadata quality.",
                "responsibilities": "Coordinate releases and metadata workflows.",
                "required_skills": ["Content Ops", "Metadata", "Operations"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Mumbai",
                "employment_type": "Full-time",
            },
            {
                "title": "Brand Strategist",
                "description": "Build go-to-market storytelling for new content.",
                "responsibilities": "Campaign strategy and positioning.",
                "required_skills": ["Brand Strategy", "Marketing", "Content"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "UX Researcher",
                "description": "Research viewer behavior and usability across platforms.",
                "responsibilities": "Run studies and insights.",
                "required_skills": ["Research", "UX", "Qualitative"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Sneha Gupta",
        "email": "hr@shieldarc.io",
        "company_name": "ShieldArc",
        "company_website": "https://shieldarc.io",
        "jobs": [
            {
                "title": "Security Engineer",
                "description": "Build detection pipelines and secure cloud infrastructure.",
                "responsibilities": "Threat detection and secure architecture.",
                "required_skills": ["Cloud Security", "SIEM", "Python"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Threat Researcher",
                "description": "Analyze emerging threats and develop mitigation playbooks.",
                "responsibilities": "Threat intelligence and analysis.",
                "required_skills": ["Threat Intel", "Malware Analysis", "Security"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "SOC Analyst",
                "description": "Monitor alerts and handle incident response workflows.",
                "responsibilities": "24x7 monitoring and escalation.",
                "required_skills": ["SIEM", "SOC", "Incident Response"],
                "minimum_experience_years": 1,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Identity Engineer",
                "description": "Manage IAM and authentication systems.",
                "responsibilities": "SSO, MFA, and access control.",
                "required_skills": ["IAM", "Okta", "Security"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Cloud Security Architect",
                "description": "Define secure cloud architecture patterns.",
                "responsibilities": "Security architecture and governance.",
                "required_skills": ["AWS", "Security Architecture", "Compliance"],
                "minimum_experience_years": 5,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Aditya Jain",
        "email": "hr@solaraxis.energy",
        "company_name": "SolarAxis",
        "company_website": "https://solaraxis.energy",
        "jobs": [
            {
                "title": "Energy Analyst",
                "description": "Analyze energy usage and forecast solar output.",
                "responsibilities": "Forecasting and KPI tracking.",
                "required_skills": ["Energy Analytics", "SQL", "Excel"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Chennai",
                "employment_type": "Full-time",
            },
            {
                "title": "IoT Engineer",
                "description": "Build IoT telemetry pipelines for solar assets.",
                "responsibilities": "Device integration and data ingestion.",
                "required_skills": ["IoT", "MQTT", "Python"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Data Scientist",
                "description": "Model energy demand and anomaly detection.",
                "responsibilities": "Train ML models and report insights.",
                "required_skills": ["Python", "ML", "Time Series"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Project Manager",
                "description": "Deliver solar projects on time and budget.",
                "responsibilities": "Timeline, vendor, and stakeholder management.",
                "required_skills": ["Project Management", "Operations"],
                "minimum_experience_years": 4,
                "education_requirement": "bachelor",
                "location": "Ahmedabad",
                "employment_type": "Full-time",
            },
            {
                "title": "Full-Stack Engineer",
                "description": "Build monitoring dashboards for solar assets.",
                "responsibilities": "Frontend and backend delivery.",
                "required_skills": ["React", "Node.js", "PostgreSQL"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
    {
        "full_name": "Priya Nair",
        "email": "hr@talentwave.co",
        "company_name": "TalentWave",
        "company_website": "https://talentwave.co",
        "jobs": [
            {
                "title": "Recruiting Coordinator",
                "description": "Coordinate interviews and candidate communication.",
                "responsibilities": "Scheduling and pipeline coordination.",
                "required_skills": ["Recruiting", "Coordination", "Communication"],
                "minimum_experience_years": 1,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "People Ops Analyst",
                "description": "Support HR analytics and people programs.",
                "responsibilities": "HR reporting and process improvement.",
                "required_skills": ["HR Analytics", "Excel", "SQL"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Employer Branding Lead",
                "description": "Build brand campaigns to attract talent.",
                "responsibilities": "Content and campaign strategy.",
                "required_skills": ["Branding", "Content", "Social"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Customer Success Manager",
                "description": "Own post-sale success for hiring teams.",
                "responsibilities": "Onboarding and retention.",
                "required_skills": ["Customer Success", "SaaS", "Communication"],
                "minimum_experience_years": 3,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
            {
                "title": "Integration Engineer",
                "description": "Build integrations with ATS and HR systems.",
                "responsibilities": "APIs and integration delivery.",
                "required_skills": ["APIs", "Integrations", "Python"],
                "minimum_experience_years": 2,
                "education_requirement": "bachelor",
                "location": "Remote",
                "employment_type": "Full-time",
            },
        ],
    },
]


def _expand_description(title: str, base: str) -> str:
    base = base.strip()
    if not base.endswith("."):
        base = f"{base}."

    title_lower = title.lower()

    if "account executive" in title_lower or "sales" in title_lower:
        extra = (
            "You will manage the full sales cycle from prospecting to close, including discovery, demos, and "
            "negotiation. You will maintain a healthy pipeline, forecast accurately, and partner with product to "
            "communicate value. Success looks like consistent quota attainment and long-term customer relationships."
        )
    elif "designer" in title_lower:
        extra = (
            "You will own the end-to-end design process from discovery to polished UI, including research, "
            "wireframes, prototypes, and usability testing. You will collaborate closely with product and engineering, "
            "contribute to the design system, and ensure accessibility and consistency. Success looks like intuitive "
            "flows, higher engagement, and a cohesive brand experience."
        )
    elif "researcher" in title_lower:
        extra = (
            "You will design studies, conduct interviews and usability tests, and synthesize findings into clear "
            "recommendations. You will work with product and design to prioritize improvements and validate outcomes. "
            "Success looks like evidence-based decisions and measurable UX gains."
        )
    elif "marketer" in title_lower or "branding" in title_lower or "brand" in title_lower or "strategist" in title_lower:
        extra = (
            "You will plan and execute campaigns across key channels, run experiments, and optimize funnel "
            "performance. You will own messaging, creative briefs, and performance reporting with a focus on ROI. "
            "Success looks like qualified pipeline growth and stronger brand recall."
        )
    elif "coordinator" in title_lower:
        extra = (
            "You will manage scheduling, communications, and process tracking to keep pipelines moving. You will "
            "maintain accurate records, coordinate stakeholders, and improve operational efficiency. Success looks "
            "like smooth handoffs, clear documentation, and timely execution."
        )
    elif "manager" in title_lower or "lead" in title_lower:
        extra = (
            "You will drive planning, execution, and stakeholder alignment across cross-functional teams. You will "
            "define goals, track progress with metrics, and remove blockers while maintaining quality. Success looks "
            "like predictable delivery, improved processes, and delighted customers."
        )
    elif "analyst" in title_lower:
        extra = (
            "You will define KPIs, build dashboards, and analyze datasets to surface actionable insights. You will "
            "partner with operations and leadership to translate questions into metrics, validate data quality, and "
            "communicate findings with clear narratives. Success looks like better decisions, improved efficiency, "
            "and well-instrumented reporting."
        )
    elif "specialist" in title_lower:
        extra = (
            "You will own domain-specific datasets and workflows, maintain standards, and provide expert guidance to "
            "partner teams. You will document processes, ensure data quality, and improve tooling where needed. "
            "Success looks like accurate outputs, reliable systems, and well-informed stakeholders."
        )
    elif "engineer" in title_lower or "architect" in title_lower:
        extra = (
            "You will design, build, and operate production systems with strong testing, observability, and "
            "performance tuning. You will collaborate with product and design to ship reliable features, write clear "
            "documentation, and participate in code reviews and on-call rotations. Success looks like stable releases, "
            "measurable improvements, and clean, maintainable architecture."
        )
    else:
        extra = (
            "You will collaborate with cross-functional teams to deliver high-quality outcomes, maintain clear "
            "documentation, and continuously improve processes. You will take ownership of key deliverables and "
            "measure impact with clear metrics. Success looks like dependable execution and tangible business results."
        )

    return f"{base} {extra}"

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _testdata_path() -> Path:
    return _project_root() / "testdata" / "resumes" / "resume_backend.txt"


def _ensure_candidate(db) -> User:
    email = "candidate@hirenexus.local"
    user = get_user_by_email(db, email)
    if user:
        return user
    return register_candidate(
        db,
        email=email,
        password=DEFAULT_PASSWORD,
        full_name="Cameron Candidate",
    )


def _ensure_hr(db, *, email: str, full_name: str, company_name: str, company_website: str) -> User:
    user = get_user_by_email(db, email)
    if user:
        return user
    return register_hr(
        db,
        email=email,
        password=DEFAULT_PASSWORD,
        full_name=full_name,
        company_name=company_name,
        company_website=company_website,
    )


def _copy_resume_to_uploads(user: User, source: Path) -> Path:
    settings = get_settings()
    target_dir = settings.upload_dir / "resumes" / str(user.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"seed_{source.name}"
    shutil.copy(source, target_path)
    return target_path


def _ensure_resume(db, user: User) -> Resume:
    resume = get_primary_resume(db, user_id=user.id)
    if resume:
        return resume

    source = _testdata_path()
    if not source.exists():
        raise FileNotFoundError(f"Missing seed resume: {source}")

    target_path = _copy_resume_to_uploads(user, source)
    parsed = parse_resume(file_path=target_path, file_type=target_path.suffix.lower())
    parsed_payload = parsed.to_dict()

    db.execute(update(Resume).where(Resume.user_id == user.id).values(is_primary=False))

    resume = Resume(
        user_id=user.id,
        file_name=target_path.name,
        file_type=target_path.suffix.lower(),
        file_path=str(target_path),
        raw_text=parsed.raw_text,
        parsed_json=parsed_payload,
        extracted_skills=list(parsed_payload.get("skills", [])),
        keywords=list(parsed_payload.get("keywords", [])),
        estimated_experience_years=parsed.estimated_experience_years,
        education_level=parsed.education_level,
        is_primary=True,
    )
    db.add(resume)
    db.flush()
    return resume


def _ensure_job(db, *, hr_user: User, job_seed: dict) -> Job:
    stmt = select(Job).where(Job.hr_user_id == hr_user.id, Job.title == job_seed["title"])
    job = db.scalar(stmt)
    expanded_description = _expand_description(job_seed["title"], job_seed["description"])
    if job:
        if job.description != expanded_description:
            job.description = expanded_description
        return job

    return create_job(
        db,
        hr_user=hr_user,
        title=job_seed["title"],
        description=expanded_description,
        responsibilities=job_seed.get("responsibilities"),
        required_skills=job_seed.get("required_skills", []),
        minimum_experience_years=job_seed.get("minimum_experience_years", 0),
        education_requirement=job_seed.get("education_requirement"),
        location=job_seed.get("location"),
        employment_type=job_seed.get("employment_type"),
    )


def _ensure_application_flow(db, candidate: User, hr_user: User, resume: Resume, job: Job) -> None:
    stmt = select(Application).where(Application.candidate_user_id == candidate.id, Application.job_id == job.id)
    application = db.scalar(stmt)
    if application:
        return

    application, interview, _eligibility, _conversation, _notification = apply_to_job(
        db,
        candidate=candidate,
        job=job,
        resume_id=resume.id,
    )

    questions = ensure_interview_questions(db, interview=interview)
    answers = [
        "I would design the API contract, implement endpoints with FastAPI, add tests, and monitor metrics."
        for _ in questions
    ]
    complete_interview(
        db,
        interview=interview,
        answers=answers,
        transcript="Candidate discussed architecture, reliability, and performance considerations.",
        recording_url=None,
    )

    update_application_status(db, hr_user=hr_user, application=application, new_status=ApplicationStatus.shortlisted)

    conversation = ensure_conversation_for_job(db, candidate=candidate, job=job)
    send_message(db, conversation=conversation, sender=hr_user, content="Thanks for applying! We'd love to chat.")
    send_message(db, conversation=conversation, sender=candidate, content="Thank you! Looking forward to it.")


def main() -> None:
    with SessionLocal() as db:
        candidate = _ensure_candidate(db)
        resume = _ensure_resume(db, candidate)

        hr_users: list[User] = []
        seeded_jobs: list[Job] = []

        for hr_seed in HR_SEED:
            hr_user = _ensure_hr(
                db,
                email=hr_seed["email"],
                full_name=hr_seed["full_name"],
                company_name=hr_seed["company_name"],
                company_website=hr_seed["company_website"],
            )
            hr_users.append(hr_user)

            for job_seed in hr_seed["jobs"]:
                job = _ensure_job(db, hr_user=hr_user, job_seed=job_seed)
                seeded_jobs.append(job)

        if hr_users and seeded_jobs:
            _ensure_application_flow(db, candidate, hr_users[0], resume, seeded_jobs[0])

        db.commit()

    print(f"Seed complete: {len(hr_users)} HR users and {len(seeded_jobs)} jobs created.")


if __name__ == "__main__":
    main()
