
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy project
COPY . .

# Create static directories if they don't exist
RUN mkdir -p /app/static /app/staticfiles

# Run as non-root user
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Command will be overridden by docker-compose
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]