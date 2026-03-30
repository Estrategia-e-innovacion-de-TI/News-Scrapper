FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Optional: install Playwright for browser-based fetching
# RUN pip install playwright && playwright install chromium --with-deps

EXPOSE 8080

CMD ["python", "-m", "newsradar_server.application.app"]
