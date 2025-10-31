# Use Python base image
FROM python:3.12-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y sqlite3

# Copy application code into the container
WORKDIR /app
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade uv
RUN uv pip install --upgrade pip
RUN uv pip install --no-cache-dir -r requirements.txt

# Make entrypoint.sh executable
RUN chmod +x entrypoint.sh
