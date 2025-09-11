# line_utils.py
import requests
import os
import json
import hashlib
import hmac
import base64

def get_line_tokens():
    """라인 챗봇 토큰들을 환경변수에서 가져옵니다."""
    access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
    
    if access_token:
        access_token = access_token.strip().strip('"')
    if channel_secret:
        channel_secret = channel_secret.strip().strip('"')
    
    return access_token, channel_secret

def is_configured():
    """라인 챗봇이 올바르게 설정되었는지 확인합니다."""
    access_token, channel_secret = get_line_tokens()
    
    if not access_token:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN이 설정되지 않았습니다.")
        return False
    
    if not channel_secret:
        print("❌ LINE_CHANNEL_SECRET이 설정되지 않았습니다.")
        return False
    
    print(f"✅ 라인 챗봇 토큰 확인됨: {access_token[:10]}...")
    return True

def verify_signature(body, signature):
    """라인 웹훅 서명을 검증합니다."""
    access_token, channel_secret = get_line_tokens()
    
    if not channel_secret:
        return False
    
    hash_value = hmac.new(
        channel_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    expected_signature = base64.b64encode(hash_value).decode('utf-8')
    return hmac.compare_digest(signature, expected_signature)

def send_message(user_id, text, quick_replies=None):
    """
    라인 챗봇을 통해 메시지를 전송합니다.
    
    Args:
        user_id (str): 사용자 ID
        text (str): 전송할 메시지
        quick_replies (list): 빠른 응답 버튼 리스트 (선택사항)
    
    Returns:
        bool: 전송 성공 여부
    """
    if not is_configured():
        return False
    
    access_token, _ = get_line_tokens()
    
    # 라인 Messaging API 엔드포인트
    url = "https://api.line.me/v2/bot/message/push"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 메시지 구성
    message = {
        "type": "text",
        "text": text
    }
    
    # 빠른 응답 버튼 추가
    if quick_replies:
        message["quickReply"] = {
            "items": []
        }
        for reply in quick_replies:
            message["quickReply"]["items"].append({
                "type": "action",
                "action": {
                    "type": "message",
                    "label": reply["label"],
                    "text": reply["text"]
                }
            })
    
    data = {
        "to": user_id,
        "messages": [message]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 라인 메시지 전송 성공: {user_id}")
            return True
        else:
            print(f"❌ 라인 메시지 전송 실패: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 라인 메시지 전송 중 오류: {e}")
        return False

def send_notice_message(user_id, title, link):
    """
    공지사항 알림 메시지를 전송합니다.
    
    Args:
        user_id (str): 사용자 ID
        title (str): 공지사항 제목
        link (str): 공지사항 링크
    
    Returns:
        bool: 전송 성공 여부
    """
    text = f"📢 [새 학사공지]\n\n{title}\n\n🔗 자세히 보기: {link}"
    
    quick_replies = [
        {"label": "구독 해제", "text": "구독해제"},
        {"label": "최신공지", "text": "최신공지"}
    ]
    
    return send_message(user_id, text, quick_replies)

def send_subscription_message(user_id, is_subscribed=True):
    """
    구독/해제 완료 메시지를 전송합니다.
    
    Args:
        user_id (str): 사용자 ID
        is_subscribed (bool): 구독 여부
    
    Returns:
        bool: 전송 성공 여부
    """
    if is_subscribed:
        text = "✅ 알림 구독이 완료되었습니다!\n\n매일 12시에 새로운 학사공지를 받아보실 수 있습니다."
        quick_replies = [
            {"label": "구독 해제", "text": "구독해제"},
            {"label": "최신공지", "text": "최신공지"}
        ]
    else:
        text = "❌ 알림 구독이 해제되었습니다.\n\n다시 구독하시려면 아래 버튼을 눌러주세요."
        quick_replies = [
            {"label": "다시 구독", "text": "구독"},
            {"label": "도움말", "text": "도움말"}
        ]
    
    return send_message(user_id, text, quick_replies)

def send_help_message(user_id):
    """
    도움말 메시지를 전송합니다.
    
    Args:
        user_id (str): 사용자 ID
    
    Returns:
        bool: 전송 성공 여부
    """
    text = (
        "📢 호서대학교 학사공지 알림봇입니다!\n\n"
        "매일 12시에 새로운 학사공지를 알려드립니다.\n\n"
        "💡 사용법:\n"
        "• '구독' - 알림 구독\n"
        "• '구독해제' - 알림 해제\n"
        "• '최신공지' - 최신 공지사항 확인\n"
        "• '도움말' - 이 메시지 다시 보기"
    )
    
    quick_replies = [
        {"label": "구독하기", "text": "구독"},
        {"label": "최신공지", "text": "최신공지"},
        {"label": "도움말", "text": "도움말"}
    ]
    
    return send_message(user_id, text, quick_replies)
