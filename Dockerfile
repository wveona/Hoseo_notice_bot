FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render가 제공하는 $PORT에 바인딩
CMD ["/bin/sh", "-c", "exec gunicorn -w 2 -k gthread --threads 8 -t 60 --bind 0.0.0.0:$PORT main:app"]
