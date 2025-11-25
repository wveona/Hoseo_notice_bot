# 호서대학교 학사공지 알림 봇

호서대학교 학사공지사항을 자동으로 크롤링하여 새로운 공지가 올라오면 텔레그램으로 알림을 보내는 봇입니다.

본 프로젝트는 AI를 활용하여 변화하는 웹 구조에 보다 유연하게 대응하고, 게시글 텍스트 정규화와 잡음(불필요 공백/특수문자 등) 제거, 링크 추출 실패 시 백업 로직 선택 등 크롤링 정확도를 향상하도록 설계되었습니다.

## 🚀 주요 기능

- **자동 크롤링**: 호서대학교 학사공지사항 웹사이트를 주기적으로 모니터링
- **새 공지 감지**: 새로운 공지사항이 올라오면 자동으로 감지
- **텔레그램 알림**: 구독자에게 텔레그램으로 즉시 전송
- **중복 방지**: 이미 발송된 공지는 다시 발송하지 않음
- **상태 모니터링**: `/status`로 크롤링 상태와 최신 공지 확인

## 🤖 AI 활용 요소

- **유연한 파싱 전략**: 정규표현식 + 선택자 조합으로 동적 구조 변화에 견고하게 대응
- **텍스트 정규화**: 공지 제목/본문의 공백·특수문자 제거로 일관된 비교 및 알림 품질 확보
- **백업 경로 추론**: 기본 링크 추출 실패 시 대체 패턴 시도(함수형 분리로 확장 용이)
- **에러 신뢰도 로그**: 실패 유형별 로그로 후속 개선(프롬프트/규칙) 빠른 피드백

## 📋 요구사항

- Python 3.11+
- 텔레그램 봇 토큰(TELEGRAM_BOT_TOKEN)
- 인터넷 연결

## 🛠️ 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token_here
# Render PostgreSQL 연결(필수)
# 예: postgres://USER:PASSWORD@HOST:PORT/DBNAME
export DATABASE_URL=postgres://... 
# 크론 보안 토큰(선택)
export SCHEDULER_TOKEN=your_secret_token
```

### 3. 텔레그램 봇 만들기
1) 텔레그램에서 BotFather와 대화 후 /newbot 으로 봇 생성
2) 발급받은 토큰을 `TELEGRAM_BOT_TOKEN`으로 설정

### 4. 서버 실행
```bash
python main.py
```

### 5. 텔레그램 웹훅 설정
프로덕션(공개 HTTPS 도메인 보유) 환경에서는 웹훅을 권장합니다. 아래 엔드포인트를 텔레그램에 등록합니다.
- 웹훅 URL: `https://your-domain.com/telegram/webhook`

설정 방법(예시):
```bash
# 서버의 /telegram/webhook 주소로 웹훅 설정 요청 (토큰 필요)
# 실제 운영에서는 별도 스크립트/관리 라우트를 만들어 자동화하는 것을 권장
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d url="https://your-domain.com/telegram/webhook"
```

로컬 개발 시에는 웹훅 대신 폴링을 사용할 수 있으나, 본 프로젝트는 웹훅 엔드포인트만 제공합니다. 로컬 테스트는 `ngrok` 같은 터널러로 공개 URL을 만들어 진행하세요.

## 📡 API 엔드포인트

### POST /crawl-and-notify
새로운 공지를 크롤링하고 텔레그램 구독자에게 알립니다.

### POST /telegram/webhook
텔레그램이 전송하는 업데이트를 수신합니다. 지원 명령어:
- `/help` 또는 `/start`: 명령어 안내
- `/subscribe`: 알림 구독(현재 채팅 id를 구독자로 등록)
- `/unsubscribe`: 알림 구독 해제

### GET /status
현재 크롤링 상태와 최신 공지 정보를 확인합니다.

## 🔧 설정

### 크롤링 설정
`crawler.py`의 상수로 관리합니다:
```python
NOTICE_URL = "https://www.hoseo.ac.kr/Home//BBSList.mbz?action=MAPP_1708240139&pageIndex=1"
NOTICE_VIEW_URL_BASE = "https://www.hoseo.ac.kr/Home//BBSView.mbz"
BOARD_ACTION_ID = "MAPP_1708240139"
```

### 데이터베이스
- Render PostgreSQL을 사용합니다. `DATABASE_URL` 환경변수로 연결 문자열을 주입하세요.
- 테이블: `posts(link UNIQUE)`, `subscribers(user_id UNIQUE)`는 서버 시작 시 자동 생성됩니다.

## 🐛 문제 해결
- 403 또는 전송 실패: 텔레그램 토큰/웹훅 URL 확인, 서버 HTTPS 인증서 점검
- DB 연결 실패: `DATABASE_URL` 형식/권한/방화벽 확인(Render 대시보드 Credentials 사용)
- 응답 지연: 크롤링을 즉시 수행하면 느릴 수 있으므로 캐시 고려
- 로컬 테스트: `ngrok http 8080` 으로 공개 URL 생성 후 웹훅 설정

## 📝 로그 예시
```
크롤링 및 알림 작업을 시작합니다...
새로운 공지 발견: OO 공지 제목
공지 링크: https://www.hoseo.ac.kr/...&schIdx=XXXXX
텔레그램 전송 완료: 3/3
✅ DB에 공지 기록 완료: OO 공지 제목...
``` 