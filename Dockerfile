FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Collect static files for WhiteNoise
RUN python manage.py collectstatic --noinput

# Expose API port
EXPOSE 8000

# Run database migrations and start gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn dicoevent.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
