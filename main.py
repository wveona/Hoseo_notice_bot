# main.py
from flask import Flask, request, jsonify
from crawler import get_latest_post, get_new_posts_since_last_check
from line_utils import send_notice_message as line_send_message, verify_signature
import database
import os

# Flask 애플리케이션 객체를 생성합니다.
app = Flask(__name__)

# 간단한 헬스체크 및 루트 페이지
@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "ok", "service": "hoseo_notice_bot", "env": "render", "platform": "line"}), 200

@app.route('/healthz', methods=['GET'])
def healthz():
    return "ok", 200

# 애플리케이션이 처음 실행될 때, 데이터베이스를 초기화하는 함수를 호출합니다.
# 이를 통해 서버가 시작될 때 항상 테이블이 준비됩니다.
database.init_db()

# '/crawl-and-notify' 경로로 POST 요청이 올 때 실행될 함수를 정의합니다.
# 이 경로는 스케줄러(예: Render Cron Job)가 주기적으로 호출할 주소(엔드포인트)입니다.
@app.route('/crawl-and-notify', methods=['POST'])
def crawl_and_notify():
    """
    웹사이트를 크롤링하여 새로운 게시글이 있으면 라인으로 알림을 보냅니다.
    """
    print("크롤링 및 라인 알림 작업을 시작합니다...")
    
    # 스케줄러 보안: 환경변수 SCHEDULER_TOKEN이 설정된 경우 헤더 검증
    expected_token = os.environ.get('SCHEDULER_TOKEN')
    if expected_token:
        incoming = request.headers.get('X-CRON-TOKEN')
        if incoming != expected_token:
            return jsonify({"status": "error", "message": "unauthorized"}), 401
    
    try:
        # 새로운 게시글들을 확인합니다 (여러 개일 수 있음)
        new_posts = get_new_posts_since_last_check()
        
        if not new_posts:
            print("새로운 공지가 없습니다.")
            return jsonify({"status": "success", "message": "새 공지 없음"}), 200
        
        print(f"새로운 공지 {len(new_posts)}개 발견")
        
        # 수신자 결정: TARGET_CHAT_IDS(쉼표구분) 우선, 없으면 DB 구독자
        target_chat_ids_env = os.environ.get('TARGET_CHAT_IDS', '').strip()
        if target_chat_ids_env:
            recipients = [cid.strip() for cid in target_chat_ids_env.split(',') if cid.strip()]
        else:
            recipients = database.list_subscribers()
        
        total_sent = 0
        
        for post in new_posts:
            title = post['title']
            link = post['link']
            text = f"[새 학사공지]\n{title}\n\n🔗 {link}"
            
            print(f"공지 발송 중: {title}")
            
            success_count = 0
            for user_id in recipients:
                if line_send_message(user_id, title, link):
                    success_count += 1
            
            print(f"라인 전송 완료: {success_count}/{len(recipients)}")
            total_sent += success_count
            
            # DB에 발송 완료 기록(중복 방지)
            database.add_sent_post(link, title)
        
        return jsonify({
            "status": "success",
            "message": f"새 공지 {len(new_posts)}개 발송 완료",
            "posts_count": len(new_posts),
            "total_sent": total_sent,
            "recipients_count": len(recipients)
        }), 200
    except Exception as e:
        print(f"크롤링 및 알림 작업 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"작업 오류: {str(e)}"}), 500

# 라인 챗봇 웹훅 엔드포인트
@app.route('/line/webhook', methods=['POST'])
def line_webhook():
    try:
        # 서명 검증
        signature = request.headers.get('X-Line-Signature')
        if not signature:
            return jsonify({"error": "Missing signature"}), 400
        
        body = request.get_data(as_text=True)
        if not verify_signature(body, signature):
            return jsonify({"error": "Invalid signature"}), 400
        
        data = request.get_json(force=True, silent=True) or {}
        print(f"Line webhook: {data}")
        
        # 라인 이벤트 처리
        for event in data.get('events', []):
            if event.get('type') == 'message':
                user_id = event.get('source', {}).get('userId')
                message_text = event.get('message', {}).get('text', '').strip()
                
                print(f"라인 사용자: {user_id}, 메시지: {message_text}")
                
                if not user_id:
                    continue
                
                # 명령어 처리
                if message_text in ('도움말', 'help', '시작'):
                    from line_utils import send_help_message
                    send_help_message(user_id)
                    
                elif message_text in ('구독', '알림', '구독하기'):
                    database.add_subscriber(str(user_id))
                    from line_utils import send_subscription_message
                    send_subscription_message(user_id, True)
                    
                elif message_text in ('구독해제', '구독취소', '해제'):
                    database.remove_subscriber(str(user_id))
                    from line_utils import send_subscription_message
                    send_subscription_message(user_id, False)
                    
                elif message_text in ('최신공지', '최신', '공지'):
                    try:
                        latest_post = get_latest_post()
                        if latest_post:
                            from line_utils import send_notice_message
                            send_notice_message(user_id, latest_post['title'], latest_post['link'])
                        else:
                            from line_utils import send_message
                            send_message(user_id, "현재 공지사항을 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
                    except Exception as e:
                        from line_utils import send_message
                        send_message(user_id, "공지사항을 가져오는 중 오류가 발생했습니다.")
                
                else:
                    from line_utils import send_message
                    send_message(user_id, "안녕하세요! 호서대학교 학사공지 알림봇입니다.\n\n'도움말'을 입력하시면 사용법을 확인할 수 있습니다.")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"라인 웹훅 처리 오류: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/status', methods=['GET'])
def status():
    try:
        print("상태 확인 요청을 받았습니다...")
        latest_post = get_latest_post()
        if latest_post is None:
            return jsonify({"status": "error", "message": "크롤링에 실패했습니다.", "crawler_status": "failed"}), 500
        is_sent = database.is_post_sent(latest_post["link"])
        return jsonify({
            "status": "success",
            "crawler_status": "working",
            "latest_post": {
                "title": latest_post["title"],
                "link": latest_post["link"],
                "is_sent": is_sent
            },
            "message": "크롤러가 정상적으로 작동하고 있습니다."
        }), 200
    except Exception as e:
        print(f"상태 확인 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"상태 확인 중 오류가 발생했습니다: {str(e)}", "crawler_status": "error"}), 500

@app.route('/admin/db', methods=['GET', 'POST'])
def admin_db():
    """데이터베이스 관리 (GET: 조회, POST: 수정)"""
    # 관리자 토큰 검증
    admin_token = os.environ.get('ADMIN_TOKEN')
    if admin_token:
        incoming_token = request.headers.get('X-ADMIN-TOKEN')
        if incoming_token != admin_token:
            return jsonify({"status": "error", "message": "unauthorized"}), 401
    
    try:
        if request.method == 'GET':
            # 조회
            subscribers = database.list_subscribers()
            return jsonify({
                "status": "success",
                "subscribers": subscribers,
                "subscribers_count": len(subscribers)
            }), 200
            
        elif request.method == 'POST':
            # 수정
            data = request.get_json()
            action = data.get('action')
            
            if action == 'add_subscriber':
                chat_id = data.get('chat_id')
                if chat_id:
                    database.add_subscriber(str(chat_id))
                    return jsonify({"status": "success", "message": f"구독자 {chat_id} 추가됨"}), 200
                    
            elif action == 'remove_subscriber':
                chat_id = data.get('chat_id')
                if chat_id:
                    database.remove_subscriber(str(chat_id))
                    return jsonify({"status": "success", "message": f"구독자 {chat_id} 제거됨"}), 200
                    
            elif action == 'clear_subscribers':
                # 모든 구독자 제거
                import psycopg2
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM subscribers")
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({"status": "success", "message": "모든 구독자 제거됨"}), 200
                
            elif action == 'clear_sent_posts':
                # 발송된 게시글 기록 제거
                import psycopg2
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sent_posts")
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({"status": "success", "message": "발송된 게시글 기록 제거됨"}), 200
                
            else:
                return jsonify({"status": "error", "message": "알 수 없는 액션"}), 400
                
    except Exception as e:
        return jsonify({"status": "error", "message": f"DB 관리 중 오류: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
