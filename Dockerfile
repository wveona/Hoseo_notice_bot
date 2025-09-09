FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 환경변수에 따라 다른 명령어 실행
CMD ["/bin/sh", "-c", "if [ \"$CRON_MODE\" = \"true\" ]; then python cron_runner.py; else exec gunicorn -w 2 -k gthread --threads 8 -t 60 --bind 0.0.0.0:$PORT main:app; fi"]
