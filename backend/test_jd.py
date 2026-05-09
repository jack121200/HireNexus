import os
import sys

# Add backend directory to sys.path to allow imports
sys.path.insert(0, r"c:\Users\jatin sharma\OneDrive\Desktop\hirenexus\backend")

# Need to load .env variables
from dotenv import load_dotenv
load_dotenv(r"c:\Users\jatin sharma\OneDrive\Desktop\hirenexus\backend\.env")

from app.services.ml.jd_parser import parse_jd_with_groq
import json

jd_text = """
Our is Client is a largest Top 5 Software giant in India, with over 11.3 USD billion dollars revenue, Global work force 2,40,000 employees, It delivers end-to-end technology, consulting, and business process services to clients across the globe, Presence: 60+ countries and Publicly traded company NSE & BSE (India), NYSE (USA).

Job Title: oracle SQL + Data Warehousing
Exp : 8+ years
Location: Chennai & Bangalore
Salary: As per market
Notice Period: 0-15 days / serving
Mode of Hire: Contract

Job Title: Oracle SQL Developer / Data Warehouse Engineer
Job Summary
We are seeking a skilled Oracle SQL Developer with strong experience in Data Warehousing concepts, ETL processes, and performance tuning. The candidate will be responsible for designing, developing, and maintaining data warehouse solutions that support business intelligence and analytics.

Key Responsibilities
• Design, develop, and optimize complex SQL queries, stored procedures, and PL/SQL packages
• Develop and maintain data warehouse schemas (Star/Snowflake models)
• Build and manage ETL processes for data extraction, transformation, and loading
• Ensure data quality, integrity, and consistency across systems
• Perform query tuning and performance optimization in Oracle databases
• Work with large datasets and ensure efficient data processing
• Collaborate with BI teams for reporting and analytics requirements
• Troubleshoot data-related issues and provide timely resolutions
• Maintain documentation for data models, ETL flows, and processes

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

parsed = parse_jd_with_groq(jd_text)
print(json.dumps(parsed, indent=2))
