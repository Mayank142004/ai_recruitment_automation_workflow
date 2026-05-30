# 🚀 Local Virtual Environment Setup & Free Cloud Deployment Guide

This guide provides step-by-step instructions to run the **AI Recruitment Automation Workflow** locally inside a Python virtual environment and deploy the entire stack to the cloud **100% free** using modern free-tier cloud platforms.

---

## 🛠️ Part 1: Local Setup with a Virtual Environment (`venv`)

A virtual environment isolates the dependencies of this project from your global system, preventing version conflicts and permission errors.

### Step 1: Open PowerShell or Command Prompt
Open your terminal and navigate to the project directory:
```powershell
cd "f:\ai requirement automantion workflow\ai-recruitment"
```

### Step 2: Create the Virtual Environment
Create a new virtual environment named `.venv` inside the project root:
```powershell
python -m venv .venv
```
*(This may take 5–10 seconds to create the directory structures).*

### Step 3: Activate the Virtual Environment
Depending on your shell, run the appropriate activation command:

* **Windows PowerShell (Recommended)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
  > 💡 **PowerShell Permission Note**: If you get a policy error like `Execution_Policies`, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first, then run the activation script.
  
* **Windows Command Prompt (CMD)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```

* **macOS / Linux Terminal**:
  ```bash
  source .venv/bin/activate
  ```

Once activated, your command line prompt will show `(.venv)` at the beginning, confirming that you are inside the virtual environment.

### Step 4: Upgrade Pip
Ensure you are using the latest version of `pip`:
```powershell
python -m pip install --upgrade pip
```

### Step 5: Install Dependencies
Install all 26 libraries pinned inside `backend/requirements.txt`:
```powershell
pip install -r backend/requirements.txt
```
*(Make sure to use the plural **requirements.txt**; if you ran `pip install -r requirement.txt`, it would fail due to the missing 's').*

### Step 6: Download the spaCy NLP Model
Download the small English language pipeline model required for skill extraction and semantic match evaluations:
```powershell
python -m spacy download en_core_web_sm
```

### Step 7: Configure your local Environment Variables
1. Duplicate `.env.example` and rename it to `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` and fill in your keys (e.g., your **Groq API Key**, Gmail credentials, and database settings).

### Step 8: Run the Services
Now that the virtual environment is set up, you can run the applications:

* **Start the FastAPI Backend**:
  ```powershell
  uvicorn backend.main:app --reload --port 8000
  ```
* **Start the Candidate Portal**:
  ```powershell
  streamlit run frontend/app.py --server.port 8501
  ```
* **Start the Recruiter Dashboard**:
  ```powershell
  streamlit run frontend/dashboard.py --server.port 8502
  ```

---

## ☁️ Part 2: Completely Free Cloud Deployment Plan

You can deploy the entire workflow online using 100% free hosting services without entering a credit card for active usage.

```mermaid
graph TD
    subgraph Client
        Browser[User Browser]
    end
    
    subgraph Streamlit Community Cloud (Free)
        Portal[Streamlit Candidate Portal]
        Dashboard[Streamlit Recruiter Dashboard]
    end
    
    subgraph Render.com (Free Web Service)
        FastAPI[FastAPI Backend Server]
    end
    
    subgraph Neon.tech (Free Serverless)
        Postgres[(PostgreSQL Database)]
    end
    
    subgraph Upstash.com (Free Serverless)
        Redis[(Upstash Redis Broker)]
    end

    Browser -->|Upload Resume / View Stats| Portal
    Browser -->|Review Candidates / Export| Dashboard
    Portal -->|POST /api/submit| FastAPI
    Dashboard -->|GET /api/candidates| FastAPI
    FastAPI -->|Read/Write Data| Postgres
    FastAPI -->|Queue Async Tasks| Redis
```

---

### 1. The Database: Neon Serverless PostgreSQL (Free)
Since SQLite is file-based and Render's free tier files are ephemeral (reset every restart), we need a free hosted relational database. **Neon** offers an outstanding, zero-cost, serverless PostgreSQL database.

* **Setup Steps**:
  1. Sign up at [Neon.tech](https://neon.tech/) (Free tier).
  2. Create a new project and select your preferred region.
  3. Under the dashboard, copy your **Connection String** (e.g., `postgresql://user:password@ep-cool-water-12345.us-east-2.aws.neon.tech/neondb?sslmode=require`).
  4. Paste this into your `.env` as the `DATABASE_URL`.

---

### 2. Async Queue Broker: Upstash Serverless Redis (Free)
For our asynchronous processing and Celery tasks (Phase 14), we need a stable Redis broker. **Upstash** offers a completely free, serverless Redis service.

* **Setup Steps**:
  1. Sign up at [Upstash.com](https://upstash.com/) (Free tier, no card required).
  2. Create a new Redis database.
  3. Copy your Redis connection URL (e.g., `rediss://default:your-password@cool-broker-12345.upstash.io:6379`).
  4. Paste this into your `.env` as `REDIS_URL`.

---

### 3. Backend API: Render Web Services (Free)
**Render** allows you to host web servers for free directly from your GitHub repository.

* **Setup Steps**:
  1. Push your project code to a public or private repository on **GitHub**.
  2. Sign up at [Render.com](https://render.com/) and connect your GitHub account.
  3. Click **New +** > **Web Service**.
  4. Select your repository.
  5. Configure the service:
     * **Name**: `ai-recruitment-api`
     * **Environment**: `Python 3`
     * **Build Command**: `pip install -r backend/requirements.txt && python -m spacy download en_core_web_sm`
     * **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port 10000`
     * **Instance Type**: **Free** ($0/month)
  6. Click **Advanced** and add your environment variables (`DATABASE_URL`, `REDIS_URL`, `GROQ_API_KEY`, etc. from your local `.env`).
  7. Deploy! Render will give you a public URL (e.g., `https://ai-recruitment-api.onrender.com`).
  > ⚠️ **Render Free Tier Limitation**: Render's free services go to sleep after 15 minutes of inactivity. The first request after a sleep period takes about 50 seconds to boot back up.

---

### 4. Streamlit Frontends: Streamlit Community Cloud (Free)
Streamlit hosts Streamlit apps for free with unlimited running time (they do not spin down or go to sleep like Render).

* **Setup Steps**:
  1. Sign up at [Streamlit Share](https://share.streamlit.io/) using your GitHub account.
  2. Click **New app**.
  3. Configure the **Candidate Application Form**:
     * **Repository**: Select your GitHub repository.
     * **Branch**: `main`
     * **Main file path**: `frontend/app.py`
  4. Click **Advanced settings** and add your environment variables:
     * `API_BASE_URL` = `https://ai-recruitment-api.onrender.com` (your Render API URL).
  5. Click **Deploy**.
  6. Repeat the exact same steps to deploy your **Recruiter Dashboard** (`frontend/dashboard.py`).

---

### 5. Automated Workflows: n8n (Free Self-Hosted)
While n8n cloud is paid, you can host n8n for free in the cloud:
* **Option A**: Add n8n to your local Docker setup (free locally).
* **Option B**: Deploy n8n via a one-click Docker template on **Hugging Face Spaces** or **Render** as a free Docker Web Service.
* **Option C (Easiest & Free)**: Use n8n's community workflows locally or run a self-hosted desktop app.

---

## 📊 Free Tier Limits & Resource Summary

| Service | Platform | Free Tier Quota | Why We Use It |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Database** | [Neon.tech](https://neon.tech/) | 0.5 GiB storage, serverless autoscaling | Store candidate schemas, match scores, and status history |
| **Redis Queue Broker** | [Upstash](https://upstash.com/) | 10,000 commands/day, serverless | Celery asynchronous resume parsing & email queue broker |
| **FastAPI Backend** | [Render](https://render.com/) | 512 MB RAM, 0.1 CPU, shared | Core logic, REST API endpoints, parsing, and LLM orchestration |
| **Streamlit Frontends** | [Streamlit Cloud](https://share.streamlit.io/) | Unlimited run time, 1 GB RAM, fast edge | Candidate portals and analytics dashboards |
| **LLM Scoring API** | [Groq API](https://console.groq.com/) | Generous free usage limits (14,400 requests/day) | Llama 3 70B evaluation, multi-criteria score parsing |

---

## 🔒 Production Readiness Checklist
When deploying to public URLs:
1. Make sure to change your **dashboard password** in the `.env` (the variable `ADMIN_PASSWORD`).
2. Set your `ENVIRONMENT` variable to `production` to secure Swagger docs if needed.
3. Keep your repository private if it contains any hardcoded default keys.
