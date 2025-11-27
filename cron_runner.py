"""
Cron Job용 실행 스크립트
"""
import os
import requests
import sys

def main():
    try:
        # 환경변수에서 설정 가져오기
        service_url = os.environ.get('SERVICE_URL', 'https://hoseo-notice-bot.onrender.com')
        scheduler_token = os.environ.get('SCHEDULER_TOKEN')
        
        if not scheduler_token:
            print("❌ SCHEDULER_TOKEN이 설정되지 않았습니다.")
            sys.exit(1)
        
        # 웹 서비스 호출
        url = f"{service_url}/crawl-and-notify"
        headers = {
            'X-CRON-TOKEN': scheduler_token,
            'Content-Type': 'application/json'
        }
        
        print(f"🔄 크롤링 작업 시작: {url}")
        
        response = requests.post(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공: {result.get('message', '작업 완료')}")
            sys.exit(0)
        else:
            print(f"❌ 실패: HTTP {response.status_code}")
            print(f"응답: {response.text}")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
