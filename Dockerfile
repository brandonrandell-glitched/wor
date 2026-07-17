FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output

EXPOSE 8080

# Single worker: in-memory workflow sessions are not shared across workers.
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 web.app:app
