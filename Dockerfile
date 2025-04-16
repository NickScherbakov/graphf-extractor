FROM python:3.10-slim

# Install system dependencies for manim and graphreader
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libgl1-mesa-glx \
    libcairo2 \
    pkg-config \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Optional: install texlive for LaTeX support (can be large)
# RUN apt-get update && apt-get install -y texlive-full

WORKDIR /app

# Copy files
COPY . /app

# Install python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -e .

# Entrypoint for CLI
ENTRYPOINT ["graph-pipeline"]
# Example:
# CMD ["--pdf", "example.pdf"]