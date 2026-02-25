# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Create and switch to a non-root user for security
RUN groupadd -r emektup && useradd -r -g emektup emektup
WORKDIR /app

# Install system dependencies if required (None currently, but good practice)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (caching layer)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

# Copy application source code
COPY ./app ./app

# Change ownership to non-root
RUN chown -R emektup:emektup /app
USER emektup

# Expose Cloud Run default port
EXPOSE 8080

# Run using gunicorn + uvicorn worker class for production Grade performance
CMD exec gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 8 --timeout 0
