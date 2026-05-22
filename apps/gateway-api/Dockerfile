FROM python:3.11-slim

WORKDIR /app

# Install curl for Docker healthchecks (python-slim does not include it)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Use exec form for CMD (more reliable in Docker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
