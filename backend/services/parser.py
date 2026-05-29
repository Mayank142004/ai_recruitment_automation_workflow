"""
AI Recruitment Automation — Resume Parsing Engine

Extracts text, skills, experience, education, and contact info from PDF resumes.
Primary: pdfplumber for text PDFs.
Fallback: pytesseract OCR for scanned/image-based PDFs.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing pdfplumber and pytesseract (graceful fallback if not installed)
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed — PDF text extraction will not work")

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    logger.warning("pytesseract not installed — OCR fallback will not work")


# ── Skills Database ──────────────────────────────────────────────────────────
# 150+ common tech skills for matching. Stored as lowercase for case-insensitive lookup.
SKILLS_DATABASE = {
    # Programming Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "c", "go", "golang",
    "rust", "php", "ruby", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "objective-c", "dart", "lua", "haskell", "elixir", "clojure", "groovy",
    "shell", "bash", "powershell", "sql", "plsql", "t-sql",

    # Web Frontend
    "react", "react.js", "reactjs", "angular", "angularjs", "vue", "vue.js", "vuejs",
    "next.js", "nextjs", "nuxt.js", "nuxtjs", "svelte", "gatsby", "ember.js",
    "html", "html5", "css", "css3", "sass", "scss", "less", "tailwind", "tailwindcss",
    "bootstrap", "material-ui", "mui", "chakra-ui", "styled-components",
    "webpack", "vite", "rollup", "babel", "jquery",

    # Web Backend
    "node.js", "nodejs", "express", "express.js", "expressjs", "fastapi", "django",
    "flask", "spring", "spring boot", "springboot", "asp.net", ".net", "dotnet",
    "rails", "ruby on rails", "laravel", "symfony", "gin", "fiber", "actix",
    "nest.js", "nestjs", "koa", "hapi", "fastify",

    # Databases
    "postgresql", "postgres", "mysql", "mariadb", "sqlite", "oracle", "sql server",
    "mongodb", "dynamodb", "cassandra", "couchdb", "firebase", "firestore",
    "redis", "memcached", "elasticsearch", "neo4j", "influxdb", "clickhouse",
    "supabase", "planetscale", "cockroachdb",

    # Cloud & DevOps
    "aws", "amazon web services", "gcp", "google cloud", "azure", "microsoft azure",
    "docker", "kubernetes", "k8s", "openshift", "rancher",
    "terraform", "ansible", "puppet", "chef", "vagrant",
    "ci/cd", "jenkins", "github actions", "gitlab ci", "circleci", "travis ci",
    "argocd", "helm", "istio", "envoy",

    # Data & ML/AI
    "machine learning", "deep learning", "artificial intelligence", "ai", "ml",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "opencv", "computer vision", "nlp", "natural language processing",
    "spacy", "nltk", "hugging face", "huggingface", "transformers",
    "bert", "gpt", "llm", "large language models",
    "spark", "pyspark", "hadoop", "hive", "presto", "dbt",
    "airflow", "luigi", "dagster", "prefect", "mlflow", "kubeflow",
    "data engineering", "data science", "data analysis", "data visualization",
    "feature engineering", "model deployment", "mlops",

    # Big Data & Streaming
    "kafka", "rabbitmq", "celery", "apache flink", "apache beam",
    "apache storm", "apache nifi", "aws kinesis", "pub/sub",

    # APIs & Protocols
    "rest api", "restful", "graphql", "grpc", "websocket", "websockets",
    "oauth", "oauth2", "jwt", "api gateway", "swagger", "openapi",
    "soap", "xml-rpc", "json-rpc",

    # Testing
    "unit testing", "integration testing", "pytest", "jest", "mocha",
    "cypress", "selenium", "playwright", "puppeteer",
    "tdd", "bdd", "cucumber",

    # Mobile
    "ios", "android", "react native", "flutter", "xamarin",
    "swift ui", "swiftui", "jetpack compose", "ionic", "cordova",

    # Version Control
    "git", "github", "gitlab", "bitbucket", "svn",

    # Project & Architecture
    "agile", "scrum", "kanban", "jira", "confluence",
    "microservices", "monolithic", "serverless", "event-driven",
    "design patterns", "solid", "clean architecture",
    "system design", "distributed systems",

    # Security
    "cybersecurity", "penetration testing", "owasp", "encryption",
    "ssl", "tls", "iam", "sso", "ldap", "active directory",

    # Other Tools
    "linux", "unix", "windows server", "nginx", "apache",
    "prometheus", "grafana", "elk", "logstash", "kibana",
    "tableau", "power bi", "looker", "metabase",
    "figma", "adobe xd", "sketch",
    "unity", "unreal engine",
    "blockchain", "ethereum", "solidity", "web3",
}


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.

    Uses pdfplumber as the primary extractor. If pdfplumber returns fewer
    than 100 characters (likely a scanned PDF), falls back to pytesseract OCR.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text with normalized whitespace.
    """
    text = ""

    # Primary: pdfplumber
    if pdfplumber is not None:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"pdfplumber extracted {len(text)} chars from {file_path}")
        except Exception as e:
            logger.error(f"pdfplumber failed on {file_path}: {e}")

    # Fallback: OCR if text is too short (scanned PDF)
    if len(text.strip()) < 100 and pytesseract is not None:
        logger.info(f"pdfplumber returned <100 chars, falling back to OCR for {file_path}")
        try:
            # Convert PDF pages to images and OCR each page
            from pdf2image import convert_from_path
            images = convert_from_path(file_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
                logger.info(f"OCR extracted {len(text)} chars from {file_path}")
        except ImportError:
            logger.warning("pdf2image not installed — OCR fallback requires it")
        except Exception as e:
            logger.error(f"OCR fallback failed on {file_path}: {e}")

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_skills(text: str) -> list[str]:
    """
    Extract tech skills from resume text.

    Uses a database of 150+ skills with case-insensitive word boundary matching.
    Returns a deduplicated list of found skills.

    Args:
        text: Raw text extracted from resume.

    Returns:
        List of unique skills found in the text.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = set()

    for skill in SKILLS_DATABASE:
        # Build a regex pattern with word boundaries for accurate matching.
        # Escape special regex characters in skill names (e.g., C++, .NET).
        escaped = re.escape(skill)
        pattern = r'(?<![a-zA-Z])' + escaped + r'(?![a-zA-Z])'
        if re.search(pattern, text_lower):
            # Store with proper capitalization
            found_skills.add(skill.title() if len(skill) > 3 else skill.upper())

    # Normalize some common skill names for consistency
    normalized = set()
    for s in found_skills:
        if s.lower() in ("react.js", "reactjs"):
            normalized.add("React")
        elif s.lower() in ("node.js", "nodejs"):
            normalized.add("Node.js")
        elif s.lower() in ("vue.js", "vuejs"):
            normalized.add("Vue.js")
        elif s.lower() in ("next.js", "nextjs"):
            normalized.add("Next.js")
        elif s.lower() in ("express.js", "expressjs"):
            normalized.add("Express.js")
        elif s.lower() in ("nest.js", "nestjs"):
            normalized.add("Nest.js")
        elif s.lower() in ("spring boot", "springboot"):
            normalized.add("Spring Boot")
        elif s.lower() in ("ruby on rails",):
            normalized.add("Ruby on Rails")
        elif s.lower() in ("scikit-learn", "sklearn"):
            normalized.add("scikit-learn")
        elif s.lower() in ("golang",):
            normalized.add("Go")
        elif s.lower() in ("postgresql", "postgres"):
            normalized.add("PostgreSQL")
        else:
            normalized.add(s)

    return sorted(normalized)


def extract_experience_years(text: str) -> float:
    """
    Extract total years of experience from resume text.

    Recognizes patterns like:
    - '3 years', '3+ years', '3.5 years experience'
    - '3-5 years of experience'
    - 'since 2019', 'from 2018 to 2022'

    Args:
        text: Raw resume text.

    Returns:
        Maximum years found as float. 0.0 if not found.
    """
    if not text:
        return 0.0

    years_found = []
    text_lower = text.lower()

    # Pattern 1: "X years" / "X+ years" / "X.Y years"
    pattern1 = r'(\d+\.?\d*)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)?'
    for match in re.finditer(pattern1, text_lower):
        years_found.append(float(match.group(1)))

    # Pattern 2: "X-Y years" (take the higher end)
    pattern2 = r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)'
    for match in re.finditer(pattern2, text_lower):
        years_found.append(float(match.group(2)))

    # Pattern 3: "since YYYY" (calculate from current year)
    from datetime import datetime
    current_year = datetime.now().year
    pattern3 = r'since\s+(20\d{2}|19\d{2})'
    for match in re.finditer(pattern3, text_lower):
        start_year = int(match.group(1))
        years_found.append(float(current_year - start_year))

    # Pattern 4: "from YYYY to YYYY" / "YYYY - YYYY"
    pattern4 = r'(?:from\s+)?(20\d{2}|19\d{2})\s*(?:to|[-–])\s*(20\d{2}|19\d{2}|present|current)'
    for match in re.finditer(pattern4, text_lower):
        start_year = int(match.group(1))
        end_str = match.group(2)
        end_year = current_year if end_str in ("present", "current") else int(end_str)
        years_found.append(float(end_year - start_year))

    return max(years_found) if years_found else 0.0


def extract_education(text: str) -> dict:
    """
    Extract education details from resume text.

    Args:
        text: Raw resume text.

    Returns:
        Dict with keys: degree, institution, year.
    """
    result = {"degree": "", "institution": "", "year": ""}

    if not text:
        return result

    # Match common degree abbreviations
    degree_patterns = [
        r'(?:Ph\.?D|Doctor(?:ate)?)\s*(?:in\s+\w+)?',
        r'(?:M\.?Tech|M\.?\s*Tech)',
        r'(?:M\.?Sc|M\.?\s*Sc\.?)\s*(?:in\s+\w+)?',
        r'(?:MBA|M\.?B\.?A\.?)',
        r'(?:MCA|M\.?C\.?A\.?)',
        r'(?:M\.?E\.?|Master(?:s?)?\s+(?:of|in)\s+\w+)',
        r'(?:B\.?Tech|B\.?\s*Tech)',
        r'(?:B\.?E\.?|Bachelor(?:s?)?\s+(?:of|in)\s+Engineering)',
        r'(?:B\.?Sc|B\.?\s*Sc\.?)\s*(?:in\s+\w+)?',
        r'(?:BCA|B\.?C\.?A\.?)',
        r'(?:B\.?Com|B\.?\s*Com\.?)',
        r'(?:BBA|B\.?B\.?A\.?)',
    ]

    for pattern in degree_patterns:
        # Wrap pattern with lookarounds to prevent matching abbreviations inside larger words (e.g., "MBA" in "Mumbai")
        full_pattern = r'(?<![a-zA-Z])(?:' + pattern + r')(?![a-zA-Z])'
        match = re.search(full_pattern, text, re.IGNORECASE)
        if match:
            result["degree"] = match.group(0).strip()
            break

    # Extract graduation year (4-digit year near education section)
    year_match = re.search(
        r'(?:graduated?|batch|class\s+of|year\s+of|passing)\s*:?\s*(20\d{2}|19\d{2})',
        text,
        re.IGNORECASE,
    )
    if year_match:
        result["year"] = year_match.group(1)
    else:
        # Look for any year near the degree
        if result["degree"]:
            degree_pos = text.lower().find(result["degree"].lower())
            if degree_pos >= 0:
                nearby = text[max(0, degree_pos - 100):degree_pos + 200]
                year_near = re.findall(r'20\d{2}|19\d{2}', nearby)
                if year_near:
                    result["year"] = year_near[-1]  # Take the most recent

    # Try to extract institution name using common patterns
    inst_patterns = [
        r'(?:university|institute|college|school|academy)\s+(?:of\s+)?[\w\s]+',
        r'(?:IIT|NIT|IIIT|BITS|VIT|SRM|MIT|DTU|NSIT|IISER|ISI)\s*[\w\s]*',
    ]
    for pattern in inst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inst = match.group(0).strip()
            # Clean up — max 100 chars
            result["institution"] = inst[:100]
            break

    return result


def extract_contact_info(text: str) -> dict:
    """
    Extract contact information from resume text.

    Args:
        text: Raw resume text.

    Returns:
        Dict with keys: email, phone, github_url, linkedin_url.
    """
    result = {
        "email": "",
        "phone": "",
        "github_url": "",
        "linkedin_url": "",
    }

    if not text:
        return result

    # Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        result["email"] = email_match.group(0).lower()

    # Indian phone number (+91 optional, 10 digits)
    phone_match = re.search(r'(?:\+?91[\s-]?)?([6-9]\d{9})', text)
    if phone_match:
        result["phone"] = phone_match.group(1)

    # GitHub URL
    github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)', text)
    if github_match:
        result["github_url"] = f"https://github.com/{github_match.group(1)}"

    # LinkedIn URL
    linkedin_match = re.search(
        r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)',
        text,
    )
    if linkedin_match:
        result["linkedin_url"] = f"https://linkedin.com/in/{linkedin_match.group(1)}"

    return result


def parse_resume(file_path: str) -> dict:
    """
    Complete resume parsing pipeline.

    Extracts text from PDF, then parses skills, experience, education,
    and contact info.

    Args:
        file_path: Path to the PDF resume.

    Returns:
        Dict with all parsed data.
    """
    text = extract_text_from_pdf(file_path)
    skills = extract_skills(text)
    experience = extract_experience_years(text)
    education = extract_education(text)
    contact = extract_contact_info(text)

    return {
        "raw_text": text,
        "skills": skills,
        "experience_years": experience,
        "education": education,
        "contact": contact,
        "text_length": len(text),
        "ocr_used": len(text) < 100,  # Approximation
    }
