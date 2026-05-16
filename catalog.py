"""
SHL Catalog - Loader and TF-IDF Search
Scrapes the SHL product catalog at startup and caches to disk.
Falls back to bundled catalog if scraping fails.
"""

import json
import os
import re
import math
import time
import logging
import requests
from bs4 import BeautifulSoup
from collections import Counter

logger = logging.getLogger(__name__)

CATALOG_CACHE_PATH = "shl_catalog.json"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"

# ── Test type mappings ────────────────────────────────────────────────────────
TEST_TYPE_MAP = {
    "A": "Ability/Cognitive",
    "P": "Personality",
    "B": "Behavioral/Competency",
    "S": "Skills/Simulation",
    "K": "Knowledge",
    "M": "Motivational",
    "360": "360 Feedback",
}


def scrape_catalog() -> list:
    """
    Scrape SHL Individual Test Solutions catalog.
    Returns list of assessment dicts.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SHLBot/1.0)",
        "Accept": "text/html",
    }
    all_items = []
    start = 0
    page_size = 12

    while True:
        params = {
            "start": start,
            "type": 1,  # Individual Test Solutions
            "action_doFilteringForm": "Search",
        }
        try:
            resp = requests.get(
                CATALOG_URL, params=params, headers=headers, timeout=15
            )
            if resp.status_code != 200:
                logger.warning(f"Catalog page returned {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table tr[data-href], .product-catalogue__row, tr.js-redirect-row")

            if not rows:
                # Try alternate table structure
                rows = soup.select("table tbody tr")

            if not rows:
                logger.info(f"No rows at start={start}, stopping")
                break

            for row in rows:
                item = parse_row(row)
                if item:
                    all_items.append(item)

            # Check for next page
            next_link = soup.find("a", string=re.compile(r"Next|>"))
            if not next_link or len(rows) < page_size:
                break
            start += page_size
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Scrape error at start={start}: {e}")
            break

    logger.info(f"Scraped {len(all_items)} assessments")
    return all_items


def parse_row(row) -> dict | None:
    """Parse a catalog table row into an assessment dict."""
    try:
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        # Name and URL
        link = row.find("a") or cells[0].find("a")
        if not link:
            return None

        name = link.get_text(strip=True)
        href = link.get("href", "")
        if not href.startswith("http"):
            href = "https://www.shl.com" + href
        if not name or not href:
            return None

        # Remote testing and Adaptive columns (checkmarks)
        remote = False
        adaptive = False
        test_type = "A"

        if len(cells) >= 3:
            remote = bool(cells[1].find("span", class_=re.compile(r"check|yes|tick")) or
                         cells[1].get_text(strip=True) in ["\u2714", "Yes", "✓"])
        if len(cells) >= 4:
            adaptive = bool(cells[2].find("span", class_=re.compile(r"check|yes|tick")) or
                           cells[2].get_text(strip=True) in ["\u2714", "Yes", "✓"])
        if len(cells) >= 5:
            type_cell = cells[-1].get_text(strip=True)
            if type_cell:
                test_type = type_cell.split()[0] if type_cell.split() else "A"

        return {
            "name": name,
            "url": href,
            "remote_testing": remote,
            "adaptive": adaptive,
            "test_type": test_type,
            "description": "",
        }
    except Exception:
        return None


def load_catalog() -> list:
    """Load catalog: try cache first, then scrape, then fall back to bundled."""
    # 1. Try cache
    if os.path.exists(CATALOG_CACHE_PATH):
        try:
            with open(CATALOG_CACHE_PATH) as f:
                data = json.load(f)
            if data:
                logger.info(f"Loaded catalog from cache: {len(data)} items")
                return data
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")

    # 2. Try scraping
    scraped = scrape_catalog()
    if scraped:
        with open(CATALOG_CACHE_PATH, "w") as f:
            json.dump(scraped, f, indent=2)
        return scraped

    # 3. Fall back to bundled catalog
    logger.warning("Scraping failed, using bundled catalog")
    return get_bundled_catalog()


def get_bundled_catalog() -> list:
    """
    Comprehensive bundled catalog of SHL Individual Test Solutions.
    Sourced from https://www.shl.com/solutions/products/product-catalog/
    type=1 (Individual Test Solutions only)
    """
    return [
        # ── Cognitive / Ability ───────────────────────────────────────────────
        {
            "name": "Verify Numerical Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-numerical-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Measures numerical reasoning ability. Suitable for graduate and professional roles. Tests ability to interpret numerical data, tables, and charts.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager"],
            "keywords": ["numerical", "math", "quantitative", "data analysis", "numbers", "cognitive"],
        },
        {
            "name": "Verify Verbal Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-verbal-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Measures verbal reasoning ability. Tests ability to understand written information and evaluate arguments.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager"],
            "keywords": ["verbal", "reading", "comprehension", "language", "communication", "cognitive"],
        },
        {
            "name": "Verify Inductive Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-inductive-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Measures inductive/abstract reasoning ability. Tests ability to identify patterns and rules in abstract information.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["inductive", "abstract", "logical", "patterns", "reasoning", "cognitive", "problem solving"],
        },
        {
            "name": "Verify Deductive Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-deductive-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Measures deductive reasoning ability. Tests ability to draw logical conclusions from given information.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager"],
            "keywords": ["deductive", "logical", "reasoning", "conclusions", "cognitive"],
        },
        {
            "name": "Verify Mechanical Comprehension",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-mechanical-comprehension/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures mechanical reasoning ability. Suitable for roles requiring mechanical understanding.",
            "job_levels": ["Entry-Level", "Mid-Professional"],
            "keywords": ["mechanical", "engineering", "technical", "physical", "machines"],
        },
        {
            "name": "Verify Interactive - Numerical Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-interactive-numerical-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Mobile-first interactive numerical reasoning assessment. Modern, engaging format.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["numerical", "interactive", "mobile", "math", "quantitative"],
        },
        {
            "name": "Verify Interactive - Verbal Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-interactive-verbal-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Mobile-first interactive verbal reasoning assessment.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["verbal", "interactive", "mobile", "language", "reading"],
        },
        {
            "name": "Verify Interactive - Deductive Reasoning",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-interactive-deductive-reasoning/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "Mobile-first interactive deductive reasoning assessment.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["deductive", "logical", "interactive", "mobile", "reasoning"],
        },
        {
            "name": "Verify G+ (General Ability)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-g-general-ability/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": True,
            "description": "General cognitive ability assessment combining verbal, numerical, and inductive reasoning.",
            "job_levels": ["Graduate", "Mid-Professional", "Manager", "Director"],
            "keywords": ["general ability", "cognitive", "IQ", "intelligence", "reasoning", "all-round"],
        },

        # ── Personality ───────────────────────────────────────────────────────
        {
            "name": "OPQ32r",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/opq32r/",
            "test_type": "P",
            "remote_testing": True,
            "adaptive": False,
            "description": "Occupational Personality Questionnaire. 32-dimension personality measure for professional and managerial roles. Widely used for selection and development. Measures relationships with people, thinking style, feelings and emotions.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager", "Director", "Executive"],
            "keywords": ["personality", "OPQ", "behavior", "interpersonal", "leadership", "management", "culture fit", "soft skills", "traits"],
        },
        {
            "name": "OPQ32n",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/opq32n/",
            "test_type": "P",
            "remote_testing": True,
            "adaptive": False,
            "description": "Normative version of the OPQ32. Measures personality across 32 dimensions for selection.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager"],
            "keywords": ["personality", "OPQ", "normative", "traits", "behavior"],
        },
        {
            "name": "Hogan Personality Inventory (HPI)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/hogan-personality-inventory/",
            "test_type": "P",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures normal personality characteristics that predict occupational success.",
            "job_levels": ["Mid-Professional", "Manager", "Director", "Executive"],
            "keywords": ["personality", "hogan", "leadership", "executive", "success"],
        },
        {
            "name": "Personnel Reaction Blank (PRB)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/personnel-reaction-blank/",
            "test_type": "P",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures conscientiousness, reliability, and work ethic for entry-level roles.",
            "job_levels": ["Entry-Level", "Graduate", "Supervisor"],
            "keywords": ["personality", "reliability", "conscientiousness", "entry-level", "work ethic"],
        },

        # ── Motivational ──────────────────────────────────────────────────────
        {
            "name": "Motivation Questionnaire (MQ)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/motivation-questionnaire-mq/",
            "test_type": "M",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures factors that energize, direct, and sustain behavior at work. 18 motivation dimensions.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor", "Manager", "Director"],
            "keywords": ["motivation", "engagement", "drive", "career", "values", "what motivates", "MQ"],
        },

        # ── Behavioral / Competency ───────────────────────────────────────────
        {
            "name": "SHL Universal Competency Framework (UCF)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/universal-competency-framework/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Comprehensive competency framework mapping behavioral expectations across levels and job families.",
            "job_levels": ["All Levels"],
            "keywords": ["competency", "behavioral", "framework", "skills", "leadership"],
        },
        {
            "name": "Sales Achievement Predictor (SalesAP)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/sales-achievement-predictor/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Predicts sales performance. Measures attitudes, behavior, and work habits relevant to sales success.",
            "job_levels": ["Entry-Level", "Graduate", "Mid-Professional"],
            "keywords": ["sales", "selling", "business development", "revenue", "account manager", "SDR", "AE"],
        },
        {
            "name": "Customer Contact Styles Questionnaire (CCSQ)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/customer-contact-styles-questionnaire/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures behavioral styles relevant to customer-facing roles. Contact center and customer service focused.",
            "job_levels": ["Entry-Level", "Supervisor"],
            "keywords": ["customer service", "contact center", "call center", "customer facing", "support", "helpdesk"],
        },
        {
            "name": "Workplace Safety (SP)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/workplace-safety-sp/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Assesses safety-related behaviors and attitudes for industrial and operational roles.",
            "job_levels": ["Entry-Level", "Supervisor"],
            "keywords": ["safety", "workplace", "industrial", "manufacturing", "compliance", "health and safety"],
        },

        # ── Situational Judgment ──────────────────────────────────────────────
        {
            "name": "SMART (Situational Judgment - Graduate)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/smart-situational-judgment-graduate/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Graduate-level situational judgment test assessing decision-making in workplace scenarios.",
            "job_levels": ["Graduate", "Entry-Level"],
            "keywords": ["situational judgment", "SJT", "graduate", "decision making", "scenarios"],
        },
        {
            "name": "Scenarios - Management (SJT)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/scenarios-management-sjt/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Situational judgment test for managerial roles. Tests decision-making in management scenarios.",
            "job_levels": ["Manager", "Front Line Manager", "Supervisor"],
            "keywords": ["situational judgment", "SJT", "management", "leadership", "decision making"],
        },

        # ── Technical / IT Knowledge ──────────────────────────────────────────
        {
            "name": "Java (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/java-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Multi-choice test measuring Java programming knowledge including OOP, collections, exceptions, and concurrency.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["java", "programming", "developer", "software", "backend", "OOP", "coding"],
        },
        {
            "name": "Java 8 (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge of Java 8 features including streams, lambdas, functional interfaces.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["java 8", "java", "streams", "lambda", "functional", "developer", "backend"],
        },
        {
            "name": "Python (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/python-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests Python programming knowledge: syntax, data structures, OOP, and standard library.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["python", "programming", "developer", "data science", "ML", "backend", "scripting"],
        },
        {
            "name": "SQL (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/sql-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures knowledge of SQL queries, data manipulation, joins, and transaction processing.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["SQL", "database", "data", "queries", "MySQL", "PostgreSQL", "analyst"],
        },
        {
            "name": "JavaScript (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/javascript-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests JavaScript programming knowledge: ES6+, async patterns, DOM, and frameworks.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["javascript", "JS", "frontend", "web developer", "React", "Node", "TypeScript"],
        },
        {
            "name": "C# (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/c-sharp-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests C# programming knowledge including .NET framework, OOP, LINQ, and async programming.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["C#", ".NET", "dotnet", "Microsoft", "backend", "developer", "software engineer"],
        },
        {
            "name": "C++ (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/c-plus-plus-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests C++ programming knowledge including STL, memory management, and OOP.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["C++", "systems", "embedded", "developer", "low-level", "performance"],
        },
        {
            "name": "Spring (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/spring-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge of Spring framework: core, AOP, IOC container, and transactions.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["spring", "java", "framework", "backend", "microservices", "REST API"],
        },
        {
            "name": "Manual Testing (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/manual-testing-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures knowledge of software testing lifecycle, testing tools, test case design.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["testing", "QA", "quality assurance", "manual testing", "test cases", "SDLC"],
        },
        {
            "name": "Automata - Selenium",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/automata-selenium/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "Coding simulation for Selenium automation testing. Candidate writes real test scripts.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["selenium", "automation", "testing", "QA", "coding simulation", "web testing"],
        },
        {
            "name": "Automata Pro",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/automata-pro/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "Advanced coding simulation. Candidates solve real-world programming problems in their chosen language.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["coding", "simulation", "programming", "software engineer", "developer", "algorithms"],
        },
        {
            "name": "Coding Pro - Full Stack",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/coding-pro-full-stack/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "Full-stack coding simulation covering frontend and backend development tasks.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["full stack", "coding", "frontend", "backend", "developer", "simulation"],
        },
        {
            "name": "MS Excel (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/ms-excel-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures ability to use MS Excel for data maintenance, analysis, and presentation.",
            "job_levels": ["Entry-Level", "Graduate", "Mid-Professional", "Supervisor"],
            "keywords": ["excel", "spreadsheet", "data", "financial analysis", "reporting", "MS Office"],
        },
        {
            "name": "MS Word (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/ms-word-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures proficiency in MS Word including formatting, tables, and document management.",
            "job_levels": ["Entry-Level", "Graduate", "Mid-Professional"],
            "keywords": ["word", "MS office", "document", "administrative", "clerical"],
        },
        {
            "name": "MS PowerPoint (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/ms-powerpoint-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests MS PowerPoint proficiency for creating and editing presentations.",
            "job_levels": ["Entry-Level", "Graduate", "Mid-Professional"],
            "keywords": ["powerpoint", "presentation", "slides", "MS office", "communication"],
        },
        {
            "name": "General Ability (Intermediate)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/general-ability-intermediate/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures general cognitive ability for clerical and administrative roles.",
            "job_levels": ["Entry-Level", "Graduate", "Supervisor"],
            "keywords": ["general ability", "cognitive", "clerical", "administrative", "IQ"],
        },
        {
            "name": "Basic Computer Literacy (BCL)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/basic-computer-literacy/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Assesses basic computer skills for data entry and clerical roles.",
            "job_levels": ["Entry-Level"],
            "keywords": ["computer literacy", "basic", "data entry", "clerical", "typing", "IT basics"],
        },
        {
            "name": "Data Entry Speed and Accuracy",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/data-entry-speed-accuracy/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures typing speed and accuracy for data entry and administrative roles.",
            "job_levels": ["Entry-Level"],
            "keywords": ["data entry", "typing", "speed", "accuracy", "clerical", "administrative"],
        },

        # ── Numerical / Financial ─────────────────────────────────────────────
        {
            "name": "Financial Analysis (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/financial-analysis-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge of financial analysis, accounting principles, and financial statement interpretation.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["finance", "financial analysis", "accounting", "CFA", "banking", "investment", "P&L"],
        },
        {
            "name": "Numerical Reasoning (Graduate)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/numerical-reasoning-graduate/",
            "test_type": "A",
            "remote_testing": True,
            "adaptive": False,
            "description": "Graduate-level numerical reasoning test for finance, consulting, and analytical roles.",
            "job_levels": ["Graduate"],
            "keywords": ["numerical", "graduate", "math", "finance", "consulting", "analytical"],
        },

        # ── Call Center / Customer Service ────────────────────────────────────
        {
            "name": "Contact Center Simulation",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/contact-center-simulation/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "Realistic simulation of contact center work: handling calls, emails, and chats.",
            "job_levels": ["Entry-Level", "Supervisor"],
            "keywords": ["contact center", "call center", "customer service", "simulation", "helpdesk", "BPO"],
        },
        {
            "name": "Customer Service Skills",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/customer-service-skills/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Measures knowledge and skills for customer service roles.",
            "job_levels": ["Entry-Level", "Graduate", "Supervisor"],
            "keywords": ["customer service", "client facing", "service", "support", "retail"],
        },

        # ── Sales ─────────────────────────────────────────────────────────────
        {
            "name": "Sales Aptitude",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/sales-aptitude/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Assesses natural aptitude for sales roles including persuasion, resilience, and drive.",
            "job_levels": ["Entry-Level", "Graduate", "Mid-Professional"],
            "keywords": ["sales", "aptitude", "persuasion", "selling", "revenue", "business development"],
        },

        # ── Leadership / Management ───────────────────────────────────────────
        {
            "name": "Management Competency Inventory (MCI)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/management-competency-inventory/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Assesses key management competencies including planning, delegation, and team leadership.",
            "job_levels": ["Manager", "Front Line Manager", "Director"],
            "keywords": ["management", "leadership", "competency", "team leader", "supervisor", "people manager"],
        },
        {
            "name": "Leadership Report (OPQ32)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/leadership-report-opq32/",
            "test_type": "P",
            "remote_testing": True,
            "adaptive": False,
            "description": "OPQ32-based leadership potential report identifying strengths and development areas.",
            "job_levels": ["Manager", "Director", "Executive"],
            "keywords": ["leadership", "executive", "senior", "director", "C-suite", "potential"],
        },
        {
            "name": "Situational Judgment for Leaders",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/situational-judgment-leaders/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Leadership-focused situational judgment test for senior and managerial roles.",
            "job_levels": ["Manager", "Director", "Executive"],
            "keywords": ["leadership", "SJT", "situational judgment", "senior", "executive", "decision making"],
        },

        # ── Occupational English / Language ───────────────────────────────────
        {
            "name": "SVAR (Spoken English Test)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/svar-spoken-english-test/",
            "test_type": "S",
            "remote_testing": True,
            "adaptive": False,
            "description": "AI-scored spoken English test for contact center and customer-facing roles.",
            "job_levels": ["Entry-Level", "Supervisor"],
            "keywords": ["English", "spoken", "language", "communication", "accent", "BPO", "call center"],
        },
        {
            "name": "Occupational English Test",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/occupational-english-test/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests English language proficiency for professional roles.",
            "job_levels": ["Graduate", "Mid-Professional"],
            "keywords": ["English", "language", "proficiency", "communication", "writing"],
        },

        # ── 360 Feedback ──────────────────────────────────────────────────────
        {
            "name": "360 Feedback Tool",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/360-feedback/",
            "test_type": "360",
            "remote_testing": True,
            "adaptive": False,
            "description": "Multi-rater 360 feedback assessment for development. Collects feedback from peers, managers, and direct reports.",
            "job_levels": ["Manager", "Director", "Executive", "Professional Individual Contributor"],
            "keywords": ["360", "feedback", "multi-rater", "development", "peers", "managers", "leadership development"],
        },

        # ── Retail / Operational ──────────────────────────────────────────────
        {
            "name": "Retail Skills (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/retail-skills-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge and skills specific to retail environments.",
            "job_levels": ["Entry-Level", "Supervisor"],
            "keywords": ["retail", "store", "customer", "sales", "merchandising", "frontline"],
        },

        # ── Project Management ─────────────────────────────────────────────────
        {
            "name": "Project Management (New)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/project-management-new/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge of project management principles, methodologies (Agile, Waterfall), and tools.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor", "Manager"],
            "keywords": ["project management", "PMP", "agile", "scrum", "waterfall", "PM", "delivery"],
        },

        # ── Cybersecurity / IT ────────────────────────────────────────────────
        {
            "name": "Cybersecurity Knowledge",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/cybersecurity-knowledge/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests knowledge of cybersecurity principles, threats, and countermeasures.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["cybersecurity", "security", "IT security", "infosec", "hacking", "network security"],
        },

        # ── HR / Administrative ───────────────────────────────────────────────
        {
            "name": "Administrative Professional (AP)",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/administrative-professional/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Comprehensive assessment for administrative and executive assistant roles.",
            "job_levels": ["Entry-Level", "Mid-Professional"],
            "keywords": ["administrative", "assistant", "EA", "PA", "office management", "clerical", "secretary"],
        },

        # ── Healthcare ────────────────────────────────────────────────────────
        {
            "name": "Healthcare Professional Assessment",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/healthcare-professional/",
            "test_type": "B",
            "remote_testing": True,
            "adaptive": False,
            "description": "Behavioral assessment for healthcare professionals measuring patient care competencies.",
            "job_levels": ["Entry-Level", "Mid-Professional", "Professional Individual Contributor"],
            "keywords": ["healthcare", "medical", "nurse", "doctor", "clinical", "patient care", "hospital"],
        },

        # ── Accounting / Finance ──────────────────────────────────────────────
        {
            "name": "Accountancy / Finance Knowledge",
            "url": "https://www.shl.com/solutions/products/product-catalog/view/accountancy-finance-knowledge/",
            "test_type": "K",
            "remote_testing": True,
            "adaptive": False,
            "description": "Tests accounting and finance knowledge including GAAP, financial statements, and bookkeeping.",
            "job_levels": ["Graduate", "Mid-Professional"],
            "keywords": ["accounting", "finance", "GAAP", "bookkeeping", "CPA", "financial statements", "auditing"],
        },
    ]


# ── TF-IDF Search Engine ──────────────────────────────────────────────────────

def tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+#]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def build_tfidf_index(catalog: list) -> tuple:
    """Build TF-IDF index over catalog."""
    docs = []
    for item in catalog:
        text = " ".join([
            item.get("name", "") * 3,  # name weighted 3x
            item.get("description", ""),
            " ".join(item.get("keywords", [])) * 2,  # keywords weighted 2x
            " ".join(item.get("job_levels", [])),
            item.get("test_type", ""),
        ])
        docs.append(tokenize(text))

    # IDF
    N = len(docs)
    df = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    idf = {term: math.log((N + 1) / (count + 1)) + 1 for term, count in df.items()}

    # TF-IDF vectors
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) or 1
        vec = {term: (count / total) * idf.get(term, 1) for term, count in tf.items()}
        vectors.append(vec)

    return vectors, idf


_INDEX = None
_IDF = None


def get_index(catalog: list):
    global _INDEX, _IDF
    if _INDEX is None:
        _INDEX, _IDF = build_tfidf_index(catalog)
    return _INDEX, _IDF


def cosine_sim(a: dict, b: dict) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values())) or 1
    norm_b = math.sqrt(sum(v * v for v in b.values())) or 1
    return dot / (norm_a * norm_b)


def search_catalog(catalog: list, query: str, top_k: int = 20) -> list:
    """Search catalog with TF-IDF + keyword boosting."""
    if not catalog or not query.strip():
        return catalog[:top_k]

    vectors, idf = get_index(catalog)
    q_tokens = tokenize(query)
    q_vec = {}
    tf = Counter(q_tokens)
    total = len(q_tokens) or 1
    for term, count in tf.items():
        q_vec[term] = (count / total) * idf.get(term, 1.0)

    scores = []
    for i, vec in enumerate(vectors):
        sim = cosine_sim(q_vec, vec)
        # Keyword exact match boost
        item_name = catalog[i]["name"].lower()
        for qt in q_tokens:
            if qt in item_name:
                sim += 0.3
        scores.append((sim, i))

    scores.sort(reverse=True)
    return [catalog[i] for _, i in scores[:top_k] if scores[0][0] > 0]
