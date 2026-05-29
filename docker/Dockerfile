FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pytesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model (cached in Docker layer)
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY .env.example ./.env

# Create uploads directory
RUN mkdir -p /app/uploads

# Set Python path
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8000 8501 8502

# Default command: start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
