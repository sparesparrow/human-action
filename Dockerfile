FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create data directories
RUN mkdir -p data/1-pdf \
    data/2-markdown-chapters \
    data/3-markdown-chunks \
    data/4-markdown-chunks-optimized \
    data/5-audio-chunks \
    data/5-audio-chunks-espeak \
    data/6-audio-chapters \
    data/6-audio-chapters-espeak \
    data/7-paragraphs

# Set environment variables for non-API testing
ENV USE_ESPEAK=1
ENV SKIP_TEXT_OPTIMIZATION=1

# Entry point
ENTRYPOINT ["python", "-m"]

# Default command
CMD ["pipeline", "--help"]