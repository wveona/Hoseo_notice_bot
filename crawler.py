# crawler.py
import requests
from bs4 import BeautifulSoup
import re # 자바스크립트 코드 분석을 위해 정규표현식 라이브러리를 추가합니다.

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# [수정됨] 호서대학교 학사공지 게시판 정보
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
NOTICE_URL = "https://www.hoseo.ac.kr/Home//BBSList.mbz?action=MAPP_1708240139&pageIndex=1"
# 게시글 보기(view) 페이지의 기본 URL
NOTICE_VIEW_URL_BASE = "https://www.hoseo.ac.kr/Home//BBSView.mbz"
# 게시판의 고유 ID (action 파라미터 값)
BOARD_ACTION_ID = "MAPP_1708240139"


def get_latest_post():
    """
    [수정됨] 호서대학교 공지사항 웹페이지에서 가장 위에 있는 게시글(공지 포함)의
    제목과 전체 링크 주소를 반환합니다.
    """
    try:
        # [수정] 요청을 보낼 때, 실제 브라우저처럼 보이게 하기 위해 User-Agent 헤더를 추가합니다.
        # 일부 웹사이트는 자동화된 스크립트의 접근을 막기 때문에 이 설정이 도움이 됩니다.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 지정된 URL로 HTTP GET 요청을 보냅니다. 헤더와 타임아웃을 설정합니다.
        response = requests.get(NOTICE_URL, headers=headers, timeout=10)
        # 요청이 성공하지 않았을 경우(상태 코드가 200번대가 아닐 경우) 예외를 발생시킵니다.
        response.raise_for_status()
        
        # 받아온 HTML 텍스트를 BeautifulSoup 객체로 변환하여 쉽게 다룰 수 있도록 합니다.
        soup = BeautifulSoup(response.text, "html.parser")
        
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        # [수정됨] 최신 글을 찾는 로직 (공지 포함)
        # 복잡한 반복문 대신, 테이블의 가장 첫 번째 행(tr)을 바로 선택합니다.
        # 이것이 공지글이든 일반글이든 상관없이 가장 위에 있는 최신 정보입니다.
        target_row = soup.select_one(".ui-list tbody tr.board_new")
        
        # 최신 게시글 행(target_row)을 찾았는지 확인합니다.
        if target_row:
            # 행 안에서 제목이 들어있는 .board-list-title 클래스의 <a> 태그를 찾습니다.
            subject_element = target_row.select_one(".board-list-title a")
            
            # 태그 안의 텍스트(제목)를 가져옵니다. 양쪽 공백은 제거합니다.
            title = subject_element.text.strip()
            # 태그의 'href' 속성(링크)을 가져옵니다.
            href_value = subject_element.get('href')
            
            # 정규표현식을 사용하여 javascript:fn_viewData('게시글ID') 형태에서
            # 게시글 ID(숫자)만 정확히 추출합니다.
            match = re.search(r"fn_viewData\('(\d+)'\)", href_value)
            if match:
                post_id = match.group(1)
                # 기본 URL, 게시판ID, 추출한 게시글ID를 조합하여 실제 링크를 완성합니다.
                full_link = f"{NOTICE_VIEW_URL_BASE}?action={BOARD_ACTION_ID}&schIdx={post_id}"
                
                # 최종적으로 제목과 완성된 링크를 딕셔너리 형태로 반환합니다.
                return {"title": title, "link": full_link}
            else:
                print("링크(href)에서 게시글 ID를 추출하는 데 실패했습니다.")
                return None
                
        else:
            # CSS 선택자에 해당하는 요소를 찾지 못한 경우
            print("최신 공지사항을 찾을 수 없습니다. CSS 선택자('.ui-list tbody tr.board_new')를 확인하세요.")
            return None
            
    except requests.exceptions.RequestException as e:
        # 네트워크 오류 등 HTTP 요청 중에 문제가 발생한 경우
        print(f"웹사이트 크롤링 중 오류 발생: {e}")
        return None


def get_recent_posts(limit=5):
    """
    최근 게시글들을 가져옵니다. 기본적으로 최근 5개를 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(NOTICE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 모든 게시글 행을 가져옵니다
        rows = soup.select(".ui-list tbody tr.board_new")
        
        posts = []
        for row in rows[:limit]:  # limit개만 처리
            subject_element = row.select_one(".board-list-title a")
            if subject_element:
                title = subject_element.text.strip()
                href_value = subject_element.get('href')
                
                match = re.search(r"fn_viewData\('(\d+)'\)", href_value)
                if match:
                    post_id = match.group(1)
                    full_link = f"{NOTICE_VIEW_URL_BASE}?action={BOARD_ACTION_ID}&schIdx={post_id}"
                    posts.append({"title": title, "link": full_link})
        
        return posts
        
    except requests.exceptions.RequestException as e:
        print(f"최근 게시글 크롤링 중 오류 발생: {e}")
        return []


def get_new_posts_since_last_check():
    """
    마지막 체크 이후의 새로운 게시글들을 반환합니다.
    DB에 저장된 최신 게시글과 비교하여 새로운 것들만 반환합니다.
    """
    try:
        # 최근 게시글들을 가져옵니다
        recent_posts = get_recent_posts(limit=10)
        
        if not recent_posts:
            return []
        
        # DB에서 이미 발송된 게시글들을 확인합니다
        import database
        
        new_posts = []
        for post in recent_posts:
            if not database.is_post_sent(post["link"]):
                new_posts.append(post)
            else:
                # 이미 발송된 게시글을 만나면 중단 (최신순이므로)
                break
        
        return new_posts
        
    except Exception as e:
        print(f"새 게시글 확인 중 오류 발생: {e}")
        return []

