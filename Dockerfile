FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cron Job용 명령어
CMD ["python", "-c", "import requests; requests.post('https://hoseo-notice-bot.onrender.com/crawl-and-notify', headers={'X-CRON-TOKEN': 'your_scheduler_token'})"]
