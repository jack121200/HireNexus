"""
Web Scraper — fetches career guidance articles from free public sources.
Rate-limited to be respectful (2s delay between requests).
Saves to data/raw_documents.json for the data processor.

Run: python -m app.services.career_rag.data_collector
"""
from __future__ import annotations

import json
import time
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "data" / "raw_documents.json"

# Curated free sources — career guidance articles
SOURCES = {
    "freecodecamp": [
        "https://www.freecodecamp.org/news/software-engineering-interviews/",
        "https://www.freecodecamp.org/news/writing-a-killer-software-engineering-resume/",
        "https://www.freecodecamp.org/news/how-to-negotiate-your-salary/",
    ],
    "dev.to": [
        "https://dev.to/tlakomy/6-mistakes-i-made-as-a-junior-developer-1i7j",
        "https://dev.to/svikashk/20-tips-for-your-next-technical-interview-20fc",
        "https://dev.to/nasichh/5-things-programmers-can-do-to-land-their-first-job-27o9",
    ],
    "hackernoon": [
        "https://hackernoon.com/how-to-get-your-first-developer-job",
        "https://hackernoon.com/top-tips-for-software-engineer-resume-writing",
    ],
}

# Curated static articles (scraped content as structured entries)
STATIC_ARTICLES = [
    {
        "title": "How to Crack FAANG Interviews",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "interview",
        "content": (
            "Cracking FAANG (Facebook/Meta, Amazon, Apple, Netflix, Google) interviews requires systematic preparation:\n\n"
            "1. DATA STRUCTURES & ALGORITHMS: Master arrays, strings, linked lists, trees, graphs, heaps, tries, and dynamic programming. "
            "Use LeetCode — target 200+ problems. Focus on Medium difficulty. Use Neetcode 150 as your main guide.\n\n"
            "2. SYSTEM DESIGN: Study scalable system architectures. Learn about load balancers, CDNs, databases (SQL vs NoSQL), "
            "caching (Redis, Memcached), message queues (Kafka), microservices, and API design. "
            "Practice designing Twitter, Uber, Netflix, WhatsApp, TinyURL.\n\n"
            "3. BEHAVIORAL INTERVIEWS: Use the STAR method (Situation, Task, Action, Result). Prepare 5-6 strong stories covering "
            "leadership, conflict resolution, failure/learning, cross-functional collaboration, and impact. Amazon focuses heavily on "
            "their 16 Leadership Principles.\n\n"
            "4. TIMELINE: 3-6 month preparation for freshers, 2-3 months for experienced with strong DSA base.\n\n"
            "5. SALARY: FAANG offers are 30-100% above market. Senior SDE at Google India: 80-200+ LPA total comp.\n\n"
            "6. REFERRALS: A referral increases your interview chance by 3-5x. Connect with employees on LinkedIn and ask directly."
        ),
    },
    {
        "title": "LinkedIn Profile Optimization Guide",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "resume",
        "content": (
            "LinkedIn is the #1 professional network. Here's how to optimize your profile for maximum visibility:\n\n"
            "1. HEADLINE: Don't just put your job title. Use keywords: 'Software Engineer | Python | FastAPI | Building @HireNexus'.\n\n"
            "2. ABOUT: Tell your story in 3 paragraphs — who you are, what you do, what you're looking for. Include keywords naturally.\n\n"
            "3. EXPERIENCE: Same as resume — action verbs, quantified achievements. Add media (screenshots, links).\n\n"
            "4. SKILLS: List 50 skills. Get endorsements from colleagues. These influence LinkedIn search ranking.\n\n"
            "5. OPEN TO WORK: Enable this privately so only recruiters see it. Choose your preferred roles and locations.\n\n"
            "6. CONNECTIONS: Connect with people from target companies. Send personalized connection requests (100 chars).\n\n"
            "7. CONTENT: Post 1-2 times per week. Share learnings, project updates, opinions. This builds visibility.\n\n"
            "8. RECOMMENDATIONS: Ask 2-3 colleagues or managers to write recommendations. These build strong social proof."
        ),
    },
    {
        "title": "Career Transition into Tech — Complete Guide",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "career_path",
        "content": (
            "Switching careers into tech is achievable in 6-12 months with the right approach:\n\n"
            "1. CHOOSE YOUR PATH: Based on your background — "
            "Non-technical → Web Dev or QA; Finance → Data Science; Design → UI/UX → Frontend; "
            "Management → Product Manager; Science → ML/Data Science.\n\n"
            "2. LEARN EFFICIENTLY: Pick one learning platform (Coursera, Udemy, freeCodeCamp). Don't hop between resources. "
            "Focus: 2-3 hours daily. Build projects immediately after each concept.\n\n"
            "3. BUILD YOUR PORTFOLIO: 3-5 real projects with GitHub links. Ideas: "
            "todo app (too generic), instead build a job tracker, expense splitter, recipe meal planner with AI.\n\n"
            "4. LEVERAGE YOUR OLD CAREER: Your domain knowledge is a superpower. Finance → FinTech, Healthcare → HealthTech, "
            "Retail → E-commerce. Use it to get roles where you combine industry + tech knowledge.\n\n"
            "5. NETWORKING: Join communities (Discord servers, Twitter tech community, local meetups). Most career-switcher jobs "
            "come through network referrals, not cold applications.\n\n"
            "6. REALISTIC TIMELINE: 6 months minimum for web dev. 12 months for data science. Be patient — the payoff is worth it.\n\n"
            "SALARY EXPECTATION: Expect a 10-20% pay cut initially. Within 2-3 years in tech you'll surpass your old salary."
        ),
    },
    {
        "title": "The Art of Salary Negotiation — Complete Playbook",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "salary",
        "content": (
            "Salary negotiation is a skill that can make a 10-30% difference in your offer. Never skip it.\n\n"
            "BEFORE THE OFFER:\n"
            "- Research salary ranges: Glassdoor, LinkedIn Salary, Levels.fyi, AmbitionBox (India).\n"
            "- Know your BATNA (Best Alternative to Negotiated Agreement) — another offer is your best leverage.\n"
            "- NEVER reveal your current salary. Say: 'I'd prefer to focus on what the role is worth and what fits your budget.'\n\n"
            "RECEIVING THE OFFER:\n"
            "- Always ask: 'Is there any flexibility in the compensation package?'\n"
            "- Get the offer in writing before negotiating.\n"
            "- Express enthusiasm first: 'I'm really excited about this opportunity.'\n\n"
            "NEGOTIATING:\n"
            "- Counter with a specific number, not a range. Say 15L, not 12-15L.\n"
            "- Justify with data: 'Based on my research and similar roles in this market, I was expecting X.'\n"
            "- Negotiate total comp: base + bonus + ESOPs + joining bonus + annual hike cycle.\n\n"
            "WHEN THEY SAY NO:\n"
            "- Ask for a sign-on bonus instead: 'Can we offset the difference with a joining bonus?'\n"
            "- Ask for earlier performance review: 'Can we schedule a review in 6 months instead of annually?'\n\n"
            "INDIA-SPECIFIC: For 3-6 LPA roles, 5-10% negotiation is typical. For 10+ LPA, 15-25% is possible with competing offers."
        ),
    },
    {
        "title": "Open Source Contribution Guide for Students",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "skills",
        "content": (
            "Contributing to open source is the fastest way to build credibility as a developer:\n\n"
            "1. WHERE TO START: GitHub — search for repos with labels 'good first issue', 'help wanted', 'beginner friendly'. "
            "Popular beginner-friendly projects: VS Code, React, FastAPI, freeCodeCamp, Hacktoberfest participants.\n\n"
            "2. HOW TO CONTRIBUTE:\n"
            "   a) Read CONTRIBUTING.md carefully\n"
            "   b) Fork the repository\n"
            "   c) Create a feature branch: git checkout -b fix/your-fix\n"
            "   d) Make small, focused changes\n"
            "   e) Write tests for your changes\n"
            "   f) Submit a Pull Request with a clear description\n\n"
            "3. PROGRAMS: Google Summer of Code (GSoC), Outreachy, MLH Fellowship, Hacktoberfest (October every year) — "
            "these programs pay stipends and look excellent on a resume.\n\n"
            "4. BENEFITS: GitHub activity graph, exposure to production codebases, strong portfolio, mentorship from maintainers, "
            "possible job offers from the companies behind the projects.\n\n"
            "5. GETTING MERGED: Be patient. Respond to review comments quickly. Be respectful. Start with small PRs."
        ),
    },
    {
        "title": "Remote Job Search Strategy — India to Global",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "job_search",
        "content": (
            "Landing a remote job, especially with US/European companies from India, can 5-10x your salary:\n\n"
            "1. BEST PLATFORMS FOR REMOTE JOBS:\n"
            "   - Remote.com, We Work Remotely, Remotive.io, Turing.com\n"
            "   - Arc.dev (vetted developers, get matched to companies)\n"
            "   - Toptal (top 3% developers, high rates)\n"
            "   - Upwork + Fiverr (freelance to start)\n"
            "   - LinkedIn (filter by Remote in location)\n\n"
            "2. PREPARATION: "
            "Remote companies value async communication skills, strong written English, self-management, and proof of work. "
            "Your GitHub and portfolio are MORE important than your degree.\n\n"
            "3. SALARY EXPECTATIONS:\n"
            "   - US startup remote: $40-100K/year (junior to senior)\n"
            "   - European remote: €30-80K/year\n"
            "   - These are 3-8x the equivalent Indian salary\n\n"
            "4. LEGAL: You'll work as a freelancer/contractor initially. Handle taxes yourself (consult a CA). "
            "LUT filing required for GST exemption on export services.\n\n"
            "5. TIMEZONE: Most US companies are fine with IST overlap of 4-6 hours (afternoon IST = morning US East Coast)."
        ),
    },
    {
        "title": "How to Build a Standout Portfolio",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "resume",
        "content": (
            "Your portfolio is your most powerful job application tool — more important than your resume.\n\n"
            "WHAT MAKES A GREAT PROJECT:\n"
            "- Solves a Real Problem: Not another todo app. Build something you or others would actually use.\n"
            "- Has Real Users: Even 10 users is impressive. Deploy it and share it.\n"
            "- Shows Technical Depth: Not just CRUD. Add authentication, real-time features, AI integration, or performance optimizations.\n"
            "- Has Good Documentation: README with setup instructions, screenshots, demo video.\n\n"
            "PROJECT IDEAS BY ROLE:\n"
            "- Frontend: AI image generator, real-time collaboration tool, job tracking dashboard\n"
            "- Backend: URL shortener with analytics, payment integration, REST API with rate limiting\n"
            "- Full Stack: SaaS boilerplate, job board with AI matching, e-learning platform\n"
            "- ML: Stock price predictor, sentiment analyzer, recommendation system, RAG chatbot\n\n"
            "HOW TO PRESENT:\n"
            "1. GitHub repo with clean code and good commit history\n"
            "2. Live demo (Vercel/Railway/Render is free)\n"
            "3. 90-second demo video (even a screen recording)\n"
            "4. Case study in your README: Problem → Solution → Tech stack → Challenges → Results\n\n"
            "QUANTITY VS QUALITY: 3 excellent projects beat 10 basic ones every time."
        ),
    },
    {
        "title": "The Complete Interview Day Guide",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "interview",
        "content": (
            "Day-of interview preparation matters as much as months of study:\n\n"
            "BEFORE THE INTERVIEW (night before):\n"
            "- Review your resume — know every project, every number, every tech choice\n"
            "- Research the company: product, tech stack, recent news, Glassdoor reviews\n"
            "- Prepare 5 questions to ask the interviewer\n"
            "- Lay out your clothes, test your internet (virtual), or plan your route (in-person)\n\n"
            "THE CODING ROUND:\n"
            "1. Repeat the problem in your own words to confirm understanding\n"
            "2. Clarify edge cases: null inputs, empty arrays, large numbers\n"
            "3. Think aloud — say what you're considering before writing code\n"
            "4. Start with brute force, then optimize\n"
            "5. Test with examples before saying you're done\n\n"
            "THE BEHAVIORAL ROUND:\n"
            "- Use STAR format for every answer\n"
            "- Be specific — real numbers, real situations\n"
            "- Common questions: 'Tell me about yourself', 'Why this company?', 'Biggest weakness?', "
            "'Conflict with a colleague?', 'Most proud of?'\n\n"
            "QUESTIONS TO ASK THE INTERVIEWER:\n"
            "- 'What does the tech stack look like?'\n"
            "- 'What does a typical sprint look like?'\n"
            "- 'What are the biggest technical challenges the team faces?'\n"
            "- 'What does success look like in the first 6 months?'\n\n"
            "AFTER THE INTERVIEW:\n"
            "- Send a thank-you email within 24 hours\n"
            "- Follow up after 5-7 days if no response"
        ),
    },
    {
        "title": "Certifications Worth Getting in Tech (2025)",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "skills",
        "content": (
            "The right certifications can make your resume stand out and prove skills to employers:\n\n"
            "CLOUD:\n"
            "- AWS Solutions Architect Associate: Most in-demand, 12,000+ jobs in India. Cost: ₹15,000\n"
            "- Google Cloud Professional: Growing fast, especially for ML workloads\n"
            "- Azure Fundamentals: Good for enterprise/Microsoft shops\n\n"
            "DATA & AI:\n"
            "- Google TensorFlow Developer Certificate: Validates ML implementation skills\n"
            "- IBM Data Science Professional (Coursera): Beginner-friendly, affordable\n"
            "- Databricks Certified Associate: High demand for data engineering roles\n\n"
            "SECURITY:\n"
            "- CompTIA Security+: Entry-level, widely recognized\n"
            "- CEH (Certified Ethical Hacker): Good for security testing roles\n"
            "- OSCP: Gold standard for penetration testers\n\n"
            "WEB/PROGRAMMING:\n"
            "- Meta Front-End Developer (Coursera): Structured curriculum, Meta-backed\n"
            "- MongoDB Certified Developer: Good for MEAN/MERN stack developers\n\n"
            "FREE CERTIFICATIONS:\n"
            "- Google's free certifications (Grow with Google)\n"
            "- HackerRank skill certifications\n"
            "- freeCodeCamp certifications\n\n"
            "IMPORTANT: Certifications supplement experience — they don't replace projects and real skills. "
            "Don't spend months on certifications instead of building."
        ),
    },
    {
        "title": "Work-Life Balance and Avoiding Burnout in Tech",
        "source": "HireNexus Knowledge",
        "url": "",
        "category": "general",
        "content": (
            "Tech careers can be intense. Here's how to succeed without burning out:\n\n"
            "SIGNS OF BURNOUT: Dreading work on Sunday nights, loss of creativity, constant fatigue, "
            "feeling cynical about your work, declining performance.\n\n"
            "PREVENTION STRATEGIES:\n"
            "1. SET BOUNDARIES: Define working hours and stick to them. Disable Slack/work notifications after hours.\n"
            "2. TAKE REAL BREAKS: Use your vacation days. Step away from screens during lunch.\n"
            "3. PHYSICAL HEALTH: Exercise 3x/week minimum. This is non-negotiable for mental clarity.\n"
            "4. LEARN OUTSIDE WORK: If your job isn't teaching you, study on your own but protect personal time too.\n"
            "5. TALK ABOUT IT: Find a mentor or peer group. Burnout is a systemic issue in tech — you're not alone.\n\n"
            "COMPANY RED FLAGS TO AVOID:\n"
            "- Constant 'crunch mode' treated as normal\n"
            "- No mental health benefits\n"
            "- On-call without compensation\n"
            "- Senior engineers leaving frequently (check Glassdoor)\n\n"
            "REMOTE WORK SPECIFIC: Create a dedicated workspace. End your 'commute' with a walk. "
            "Over-communicate your work to compensate for reduced visibility."
        ),
    },
]


def scrape_url(url: str) -> dict | None:
    """Scrape a single URL using trafilatura."""
    try:
        import trafilatura  # noqa

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_images=False,
        )
        if not content or len(content) < 200:
            return None

        metadata = trafilatura.extract_metadata(downloaded)
        return {
            "title": metadata.title if metadata else "",
            "source": metadata.sitename if metadata else "",
            "url": url,
            "content": content,
            "category": "",  # will be categorized by data processor
        }
    except Exception as e:
        print(f"  ⚠ Failed: {url} — {e}")
        return None


def collect_all(scrape_web: bool = False) -> list[dict]:
    """
    Collect career data.
    If scrape_web=True, also scrapes the SOURCES URLs.
    Always includes the curated STATIC_ARTICLES.
    """
    all_docs = list(STATIC_ARTICLES)  # Start with curated content

    if scrape_web:
        print("\nScraping web sources...")
        for source_name, urls in SOURCES.items():
            print(f"\n  {source_name}:")
            for url in urls:
                doc = scrape_url(url)
                if doc:
                    all_docs.append(doc)
                    title = (doc.get("title", "") or url)[:60]
                    print(f"    ✓ {title}")
                time.sleep(2)  # Be respectful

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Collected {len(all_docs)} documents → {OUTPUT_PATH}")
    return all_docs


if __name__ == "__main__":
    import sys
    scrape = "--scrape" in sys.argv
    collect_all(scrape_web=scrape)
