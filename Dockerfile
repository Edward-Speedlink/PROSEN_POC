# Use Python 3.10 for maximum compatibility
FROM python:3.11-slim

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
    gcc \
    g++ \
    git \ 
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# # Alternative: Install SORT manually if requirements method fails
# RUN pip install --no-cache-dir git+https://github.com/abewley/sort.git


# # Install SORT tracker by copying files directly
# RUN git clone https://github.com/abewley/sort.git /tmp/sort && \
#     mkdir -p /app/sort && \
#     cp /tmp/sort/sort.py /app/sort/ && \
#     cp /tmp/sort/README.md /app/sort/ && \
#     rm -rf /tmp/sort

# # Create __init__.py to make it a proper Python package
# RUN echo "" > /app/sort/__init__.py

# Copy your full project
COPY . .

# Expose the Flask port
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
