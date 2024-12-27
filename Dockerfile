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

# Add these lines after the apt-get install
RUN addgroup --system chrome && \
    adduser --system --group chrome && \
    chown -R chrome:chrome /app

# Set the user to run Chrome
USER chrome

# Copy application code
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Update the CMD to run with proper permissions
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080"]
