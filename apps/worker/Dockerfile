FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app:/packages

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY apps/worker/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy packages
COPY packages/ /packages/

# Copy application code
COPY apps/worker/ .

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker && chown -R worker:worker /app
USER worker

# Run the worker
CMD ["celery", "-A", "worker", "worker", "--loglevel=info", "--concurrency=4"]

