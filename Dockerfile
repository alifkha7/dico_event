FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and install dependencies
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --skip-lock --dev --clear

# Copy project files
COPY . /app/

# Expose port
EXPOSE ${PORT:-8000}

# Run migrations and start Gunicorn server
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn event_project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]

