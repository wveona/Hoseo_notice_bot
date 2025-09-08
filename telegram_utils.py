import os
import requests
from typing import Optional

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None


def is_configured() -> bool:
    """환경변수 TELEGRAM_BOT_TOKEN 존재 여부를 확인합니다."""
    return bool(TELEGRAM_BOT_TOKEN and API_BASE)


def send_message(chat_id: str | int, text: str, disable_web_page_preview: bool = False) -> bool:
    """특정 chat_id(사용자/그룹)에 텍스트 메시지를 전송합니다."""
    if not is_configured():
        print("❌ TELEGRAM_BOT_TOKEN 미설정")
        return False
    url = f"{API_BASE}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ 텔레그램 전송 성공")
            return True
        print(f"❌ 텔레그램 전송 실패: {resp.status_code} {resp.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 텔레그램 요청 오류: {e}")
        return False


def set_webhook(webhook_url: str) -> bool:
    """텔레그램 웹훅 URL을 설정합니다."""
    if not is_configured():
        print("❌ TELEGRAM_BOT_TOKEN 미설정")
        return False
    url = f"{API_BASE}/setWebhook"
    try:
        resp = requests.post(url, data={"url": webhook_url}, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ 텔레그램 웹훅 설정 성공")
            return True
        print(f"❌ 텔레그램 웹훅 설정 실패: {resp.status_code} {resp.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 텔레그램 웹훅 요청 오류: {e}")
        return False


def delete_webhook() -> bool:
    """웹훅을 해제합니다."""
    if not is_configured():
        print("❌ TELEGRAM_BOT_TOKEN 미설정")
        return False
    url = f"{API_BASE}/deleteWebhook"
    try:
        resp = requests.post(url, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ 텔레그램 웹훅 해제 성공")
            return True
        print(f"❌ 텔레그램 웹훅 해제 실패: {resp.status_code} {resp.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 텔레그램 웹훅 해제 요청 오류: {e}")
        return False 