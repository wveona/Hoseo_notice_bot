# main.py
from flask import Flask, request, jsonify
from crawler import get_latest_post, get_new_posts_since_last_check
from telegram_utils import send_message as tg_send_message
import database
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "ok", "service": "hoseo_notice_bot", "env": "render"}), 200

@app.route('/healthz', methods=['GET'])
def healthz():
    return "ok", 200

database.init_db()

@app.route('/crawl-and-notify', methods=['POST'])
def crawl_and_notify():
    """
    웹사이트를 크롤링하여 새로운 게시글이 있으면 텔레그램으로 알림을 보냅니다.
    """
    print("크롤링 및 알림 작업을 시작합니다...")
    
    # 스케줄러 보안: 환경변수 SCHEDULER_TOKEN이 설정된 경우 헤더 검증
    expected_token = os.environ.get('SCHEDULER_TOKEN')
    if expected_token:
        incoming = request.headers.get('X-CRON-TOKEN')
        if incoming != expected_token:
            return jsonify({"status": "error", "message": "unauthorized"}), 401
    
    try:
        new_posts = get_new_posts_since_last_check()
        
        if not new_posts:
            print("새로운 공지가 없습니다.")
            return jsonify({"status": "success", "message": "새 공지 없음"}), 200
        
        print(f"새로운 공지 {len(new_posts)}개 발견")
        
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
            for chat_id in recipients:
                if tg_send_message(chat_id, text, disable_web_page_preview=False):
                    success_count += 1
            
            print(f"텔레그램 전송 완료: {success_count}/{len(recipients)}")
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

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json(force=True, silent=True) or {}
        message = update.get('message') or update.get('edited_message') or {}
        chat = message.get('chat') or {}
        chat_id = chat.get('id')
        text = (message.get('text') or '').strip()
        print(f"Telegram webhook: chat_id={chat_id}, text='{text}'")
        if not chat_id or not text:
            return jsonify({"ok": True})

        # 간단 응답만 유지(필요 없으면 웹훅 비활성화 가능)
        if text in ('/start', '/help'):
            help_text = (
                "이 봇은 매일 12시에 새로운 학사공지를 전송합니다.\n"
                "필요 시 /subscribe 로 구독, /unsubscribe 로 해제할 수 있습니다."
            )
            tg_send_message(chat_id, help_text)
        elif text == '/subscribe':
            database.add_subscriber(str(chat_id))
            tg_send_message(chat_id, '알림 구독이 완료되었습니다.')
        elif text == '/unsubscribe':
            database.remove_subscriber(str(chat_id))
            tg_send_message(chat_id, '알림 구독이 해제되었습니다.')
        else:
            tg_send_message(chat_id, "이 봇은 스케줄 알림용입니다. /help 를 참고하세요.")

        return jsonify({"ok": True})
    except Exception as e:
        print(f"텔레그램 웹훅 처리 오류: {e}")
        return jsonify({"ok": False}), 200

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
    admin_token = os.environ.get('ADMIN_TOKEN')
    if admin_token:
        incoming_token = request.headers.get('X-ADMIN-TOKEN')
        if incoming_token != admin_token:
            return jsonify({"status": "error", "message": "unauthorized"}), 401
    
    try:
        if request.method == 'GET':
            subscribers = database.list_subscribers()
            return jsonify({
                "status": "success",
                "subscribers": subscribers,
                "subscribers_count": len(subscribers)
            }), 200
            
        elif request.method == 'POST':
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
                import psycopg2
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM subscribers")
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({"status": "success", "message": "모든 구독자 제거됨"}), 200
                
            elif action == 'clear_sent_posts':
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
