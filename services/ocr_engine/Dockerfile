# ===== Stage 1: Build base image =====
FROM python:3.10-slim AS base

# Prevent Python from writing .pyc files and buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# Install system-level dependencies (for Pillow & PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    && rm -rf /var/lib/apt/lists/*

# ===== Stage 2: Install dependencies =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== Stage 3: Copy source code =====
COPY . .
# Create tmp folders (if not mounted)
RUN mkdir -p tmp/input tmp/output

# ===== Stage 4: Default command =====
# If you run via docker-compose, the command there will override this.
CMD ["python", "run_ocr_main.py"]