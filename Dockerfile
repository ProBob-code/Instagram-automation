# IG Growth Hub - Docker Configuration
# Uses Playwright official image with Chromium pre-installed

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PORT=5000

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already included in base image, but ensure latest)
RUN playwright install chromium

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/reports /app/data/profiles /app/data/sessions /app/data/tasks

# Expose port (Railway overrides this via PORT env var)
EXPOSE ${PORT}

# Health check using shell to expand PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run with Gunicorn - using shell form to expand $PORT variable
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 app:app

