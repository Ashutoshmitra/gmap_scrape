# Use Python base image
FROM python:3.12.5-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies for Chrome and Chromedriver
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libasound2 \
    libatk1.0-0 \
    libxrandr2 \
    libpangocairo-1.0-0 \
    libcups2 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY requirements.txt ./

# Install Python packages BEFORE switching to chrome user
RUN pip install --no-cache-dir -r requirements.txt

# Create chrome user and set permissions AFTER pip install
RUN addgroup --system chrome && \
    adduser --system --group chrome && \
    chown -R chrome:chrome /app

# Copy the rest of the application code
COPY . .

# Switch to chrome user
USER chrome

# Expose the Flask app on port 8080
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080"]