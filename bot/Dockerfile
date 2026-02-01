FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Tailwind CSS
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Build Tailwind CSS for dashboard
RUN cd dashboard && npm install && npm run build-css-prod

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app:/packages
ENV BOT_TEST_MODE=true
ENV BOT_AUTO_START=false

# Expose port for dashboard
EXPOSE 8000

# Default command - run API server
CMD ["python", "api_server.py"]







