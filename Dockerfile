FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak-ng \
    ffmpeg \
    libespeak-ng-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default command
ENTRYPOINT ["python", "cli.py"]
CMD ["status"] 

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak-ng \
    ffmpeg \
    libespeak-ng-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default command
ENTRYPOINT ["python", "cli.py"]
CMD ["status"]