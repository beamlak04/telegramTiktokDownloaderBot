FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including ffmpeg for media merging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scrape.py .

# Create downloads directory
RUN mkdir -p downloads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Koyeb and Render will look for traffic here)
EXPOSE 8080

# Run the bot
CMD ["python", "scrape.py"]