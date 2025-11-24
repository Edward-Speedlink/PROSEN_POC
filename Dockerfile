# Use Python 3.10 for maximum compatibility
FROM python:3.10-slim

# Prevent Python from buffering and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy your full project
COPY . .

# Expose the Flask port
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
