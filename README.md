# 🚀 AI Recruitment Automation Workflow

A complete, production-ready AI-powered recruitment automation system built with **100% free-tier APIs and open-source tools**. Automates the entire hiring pipeline — from resume collection to candidate communication — using AI scoring, NLP, and workflow automation.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📄 Resume Parsing** | Extracts skills, experience, education, and contact info from PDF resumes (pdfplumber + OCR fallback) |
| **🤖 AI Scoring** | Groq LLM (Llama 3 70B) scores candidates 0-100 against job descriptions |
| **🎯 Smart Filtering** | YAML-driven rules route candidates to shortlisted / rejected / manual_review |
| **🛡️ Spam Detection** | Detects blank, inflated, or gibberish resumes |
| **🔍 Duplicate Detection** | Fuzzy matching prevents duplicate applications |
| **📊 GitHub Scoring** | Scores candidates' GitHub profiles based on repos, stars, and activity |
| **📧 Gmail Integration** | Sends shortlist invitations and rejection emails via Gmail API |
| **💬 WhatsApp Notifications** | Sends WhatsApp messages via Meta Cloud API |
| **📋 Google Sheets Sync** | Auto-syncs candidate data to Google Sheets |
| **📈 Recruiter Dashboard** | Live dashboard with charts, filters, and manual override |
| **⚡ Async Processing** | Celery + Redis for background task processing |
| **🔄 n8n Workflow** | End-to-end automation via n8n webhook workflow |

## 🏗️ Tech Stack

| Layer | Tool | Why Free |
|-------|------|----------|
| Frontend | Streamlit | Open-source |
| Backend API | FastAPI + Uvicorn | Open-source |
| Resume Parsing | pdfplumber + pytesseract | Free |
| NLP | spaCy (en_core_web_sm) | Free local model |
| AI Scoring | Groq API (Llama 3 70B) | 14,400 req/day free |
| Semantic Matching | sentence-transformers | Free HuggingFace |
| Email | Gmail API (OAuth2) | 500 emails/day free |
| WhatsApp | Meta Cloud API | 1,000 msg/month free |
| Database | SQLite / Supabase | Free |
| Sheets Sync | gspread | Free Google Sheets API |
| Task Queue | Celery + Redis | Self-hosted free |
| Workflow | n8n (self-hosted) | Free forever |
| Containerization | Docker + Docker Compose | Free |

## 📁 Project Structure

```
ai-recruitment/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.yaml              # Per-role filtering rules
│   ├── requirements.txt         # All dependencies
│   ├── routers/
│   │   ├── candidates.py        # POST /submit, GET /candidates
│   │   ├── scoring.py           # POST /score, GET /analytics
│   │   └── communications.py    # POST /notify
│   ├── services/
│   │   ├── parser.py            # Resume parser (pdfplumber + OCR)
│   │   ├── scorer.py            # Groq LLM scoring
│   │   ├── nlp.py               # spaCy entity extraction
│   │   ├── filter.py            # YAML-based filtering
│   │   ├── embeddings.py        # Sentence-transformers matching
│   │   ├── gmail_service.py     # Gmail API integration
│   │   ├── whatsapp_service.py  # Meta Cloud API
│   │   ├── sheets_service.py    # Google Sheets sync
│   │   ├── github_scorer.py     # GitHub profile scoring
│   │   ├── duplicate_checker.py # Fuzzy duplicate detection
│   │   └── spam_detector.py     # Spam resume detection
│   ├── models/
│   │   ├── database.py          # SQLAlchemy models + DB init
│   │   └── schemas.py           # Pydantic schemas
│   ├── tasks/
│   │   └── celery_tasks.py      # Async Celery task definitions
│   └── utils/
│       └── helpers.py           # Shared utilities
├── frontend/
│   ├── app.py                   # Streamlit candidate portal
│   └── dashboard.py             # Streamlit recruiter dashboard
├── n8n/
│   └── workflow.json            # n8n workflow export
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/
│   ├── test_parser.py
│   ├── test_scorer.py
│   └── test_filter.py
├── .env.example
└── README.md
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd ai-recruitment

# Copy environment template
cp .env.example .env
# Edit .env with your API keys (see section below)

# Install dependencies
cd backend
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Configure Environment Variables

Edit `.env` with your free API keys:

```env
# Groq API (free at console.groq.com)
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama3-70b-8192

# Gmail API (free at console.cloud.google.com)
GMAIL_CREDENTIALS_JSON=path/to/credentials.json
GMAIL_SENDER_EMAIL=your_email@gmail.com

# WhatsApp (free at developers.facebook.com)
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_ID=your_phone_id

# Google Sheets
GOOGLE_SHEET_ID=your_sheet_id

# Database (SQLite for dev)
DATABASE_URL=sqlite:///./recruitment.db

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Dashboard
DASHBOARD_PASSWORD=admin123
COMPANY_NAME=YourCompany
HR_EMAIL=hr@yourcompany.com
```

### 3. Start the Backend API

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Start the Candidate Portal

```bash
streamlit run frontend/app.py --server.port 8501
```

Portal at: http://localhost:8501

### 5. Start the Recruiter Dashboard

```bash
streamlit run frontend/dashboard.py --server.port 8502
```

Dashboard at: http://localhost:8502 (password: `admin123`)

### 6. (Optional) Start Celery Worker

```bash
# Start Redis first
redis-server

# Start Celery worker
celery -A backend.tasks.celery_tasks worker --loglevel=info
```

### 7. (Optional) Start n8n

```bash
npx n8n
# Access at http://localhost:5678
# Import n8n/workflow.json
```

## 🐳 Docker Deployment

```bash
cd docker
docker-compose up --build
```

Services will be available at:
- **API**: http://localhost:8000
- **Candidate Portal**: http://localhost:8501
- **Dashboard**: http://localhost:8502
- **n8n**: http://localhost:5678
- **Redis**: localhost:6379

## 📡 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/submit` | Submit candidate application (PDF + form data) |
| `GET` | `/api/candidates` | List candidates (filters: status, role, min_score) |
| `GET` | `/api/candidates/{id}` | Get candidate detail |
| `PATCH` | `/api/candidates/{id}/status` | Manual status override |
| `POST` | `/api/score/{id}` | Re-score candidate |
| `POST` | `/api/notify/{id}` | Trigger notifications |
| `GET` | `/api/analytics` | Dashboard statistics |
| `GET` | `/api/roles` | Available roles from config.yaml |
| `GET` | `/api/task/{id}` | Async task status |
| `GET` | `/health` | Health check |

## 🧪 Running Tests

```bash
pytest tests/ -v --tb=short
```

Tests cover:
- **test_parser.py** — Resume parsing, skills extraction, experience parsing
- **test_scorer.py** — Mocked Groq API, JSON parsing, retry logic
- **test_filter.py** — Shortlist/reject/manual_review cases, config.yaml validation

## 🔑 Free API Setup

### Groq API (AI Scoring) — 100% Free
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (no credit card required)
3. Create API Key → copy to `GROQ_API_KEY`
4. Free: 14,400 requests/day, 30 req/minute

### Gmail API — Free 500 emails/day
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` → set path in `.env`

### Meta WhatsApp — Free 1,000 msg/month
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create App → Add WhatsApp product
3. Copy Test Token and Phone Number ID

### Google Sheets — Free
1. Use same Google Cloud project as Gmail
2. Enable Sheets API
3. Create spreadsheet → copy Sheet ID to `.env`

## 📋 End-to-End Flow

```
Candidate submits form → PDF saved → Spam check → Duplicate check
  → pdfplumber extracts text → spaCy extracts entities
  → Groq LLM scores 0-100 → YAML filter rules
  → shortlisted/rejected/manual_review
  → Gmail email sent → WhatsApp notification
  → Google Sheets synced → Dashboard updated
```

Total processing: **<25 seconds** (sync) or **<3 seconds** (async with Celery)

## ⚠️ Constraints

| Constraint | Limit | Mitigation |
|-----------|-------|------------|
| Groq API | 30 req/min | Rate limiter + Celery queue |
| Gmail | 500/day | Queue emails, log all sends |
| WhatsApp | 1,000/month | Only shortlisted candidates |
| SQLite | Single-file | Upgrade to Supabase for prod |

## 📄 License

Open-source. All tools and APIs used are free tier.

---

**Built with ❤️ using 100% free-tier APIs and open-source tools**
