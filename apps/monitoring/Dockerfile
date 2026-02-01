FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    prometheus-client \
    requests \
    python-dateutil

# Copy the metrics exporter
COPY apps/monitoring/metrics_exporter.py /app/metrics_exporter.py

# Make it executable
RUN chmod +x /app/metrics_exporter.py

# Expose metrics port
EXPOSE 8002

# Run the metrics exporter
CMD ["python3", "metrics_exporter.py", "--port", "8002", "--interval", "30"]





