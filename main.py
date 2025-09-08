# main.py
from flask import Flask, request, jsonify
from crawler import get_latest_post, get_new_posts_since_last_check
from telegram_utils import send_message as tg_send_message
import database
import os

# Flask 애플리케이션 객체를 생성합니다.
app = Flask(__name__)

# 간단한 헬스체크 및 루트 페이지
@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "ok", "service": "hoseo_notice_bot", "env": "render"}), 200

@app.route('/healthz', methods=['GET'])
def healthz():
    return "ok", 200

# 애플리케이션이 처음 실행될 때, 데이터베이스를 초기화하는 함수를 호출합니다.
# 이를 통해 서버가 시작될 때 항상 'posts.db' 파일과 'posts' 테이블이 준비됩니다.
database.init_db()

# '/crawl-and-notify' 경로로 POST 요청이 올 때 실행될 함수를 정의합니다.
# 이 경로는 스케줄러(예: Render Cron Job)가 주기적으로 호출할 주소(엔드포인트)입니다.
@app.route('/crawl-and-notify', methods=['POST'])
def crawl_and_notify():
    """
    웹사이트를 크롤링하여 새로운 게시글이 있으면 텔레그램 구독자에게 알림을 보냅니다.
    """
    print("크롤링 및 알림 작업을 시작합니다...")
    
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
        
        # 각 새로운 공지를 구독자들에게 발송합니다
        subscribers = database.list_subscribers()
        total_sent = 0
        
        for post in new_posts:
            title = post['title']
            link = post['link']
            text = f"[새 학사공지]\n{title}\n\n🔗 {link}"
            
            print(f"공지 발송 중: {title}")
            
            # 텔레그램 구독자들에게 발송
            success_count = 0
            for chat_id in subscribers:
                if tg_send_message(chat_id, text, disable_web_page_preview=False):
                    success_count += 1
            
            print(f"텔레그램 전송 완료: {success_count}/{len(subscribers)}")
            total_sent += success_count
            
            # DB에 발송 완료 기록
            database.add_sent_post(link, title)
        
        return jsonify({
            "status": "success",
            "message": f"새 공지 {len(new_posts)}개를 구독자들에게 알렸습니다.",
            "posts_count": len(new_posts),
            "total_sent": total_sent,
            "subscribers_count": len(subscribers)
        }), 200
    except Exception as e:
        print(f"크롤링 및 알림 작업 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"작업 오류: {str(e)}"}), 500

# 텔레그램 봇 웹훅 엔드포인트
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

        if text in ('/start', '/help'):
            help_text = (
                "명령어 안내:\n"
                "- /latest: 최근 5개 공지 확인\n"
                "- /subscribe: 공지 알림 구독\n"
                "- /unsubscribe: 공지 알림 해제"
            )
            tg_send_message(chat_id, help_text)
        elif text == '/latest':
            # 최근 5개 공지를 보여줍니다
            from crawler import get_recent_posts
            posts = get_recent_posts(limit=5)
            if not posts:
                tg_send_message(chat_id, '크롤링에 실패했습니다. 잠시 후 다시 시도해 주세요.')
            else:
                message = "📋 최근 공지사항:\n\n"
                for i, post in enumerate(posts, 1):
                    message += f"{i}. {post['title']}\n🔗 {post['link']}\n\n"
                tg_send_message(chat_id, message)
        elif text == '/subscribe':
            database.add_subscriber(str(chat_id))
            tg_send_message(chat_id, '알림 구독이 완료되었습니다. 새로운 공지 시 메시지를 받게 됩니다.')
        elif text == '/unsubscribe':
            database.remove_subscriber(str(chat_id))
            tg_send_message(chat_id, '알림 구독이 해제되었습니다.')
        else:
            tg_send_message(chat_id, "알 수 없는 명령입니다. /help 를 입력해 보세요.")

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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
