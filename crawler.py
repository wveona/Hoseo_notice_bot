# crawler.py
import requests
from bs4 import BeautifulSoup
import re
import time
import random

NOTICE_URL = "https://www.hoseo.ac.kr/Home//BBSList.mbz?action=MAPP_1708240139&pageIndex=1"
NOTICE_VIEW_URL_BASE = "https://www.hoseo.ac.kr/Home//BBSView.mbz"
BOARD_ACTION_ID = "MAPP_1708240139"

_session = None

def _get_session():
    """세션을 생성하고 반환합니다."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session

def _make_request_with_retry(url, max_retries=5, initial_delay=5):
    """HTTP 요청을 재시도 로직과 함께 실행합니다."""
    session = _get_session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.hoseo.ac.kr/',
        'Cache-Control': 'max-age=0'
    }
    
    for attempt in range(max_retries):
        try:
            if attempt == 0:
                initial_wait = random.uniform(2, 5)
                print(f"첫 요청 전 {initial_wait:.2f}초 대기 중...")
                time.sleep(initial_wait)
            else:
                delay = initial_delay * (2 ** (attempt - 1)) + random.uniform(1, 3)
                print(f"재시도 {attempt}/{max_retries - 1} - {delay:.2f}초 대기 중...")
                time.sleep(delay)
            
            response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
            
            if response.status_code == 429:
                retry_after_header = response.headers.get('Retry-After')
                if retry_after_header:
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        retry_after = initial_delay * (2 ** attempt)
                else:
                    retry_after = initial_delay * (2 ** attempt) + random.uniform(5, 10)
                
                print(f"HTTP 429 발생 (시도 {attempt + 1}/{max_retries}) - {retry_after:.2f}초 후 재시도...")
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    raise requests.exceptions.HTTPError(f"HTTP 429: 최대 재시도 횟수 초과", response=response)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after_header = e.response.headers.get('Retry-After')
                    if retry_after_header:
                        try:
                            retry_after = int(retry_after_header)
                        except ValueError:
                            retry_after = initial_delay * (2 ** attempt)
                    else:
                        retry_after = initial_delay * (2 ** attempt) + random.uniform(5, 10)
                    
                    print(f"HTTP 429 예외 발생 (시도 {attempt + 1}/{max_retries}) - {retry_after:.2f}초 후 재시도...")
                    time.sleep(retry_after)
                    continue
                else:
                    print(f"HTTP 429: 최대 재시도 횟수({max_retries}) 초과")
                    raise
            raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"요청 오류 발생: {e} - 재시도 예정...")
                continue
            raise
    
    raise requests.exceptions.RequestException(f"최대 재시도 횟수({max_retries}) 초과")


def get_latest_post():
    """학사공지 게시판의 최신 게시글 정보를 반환합니다."""
    try:
        response = _make_request_with_retry(NOTICE_URL)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        target_row = soup.select_one(".ui-list tbody tr.board_new")
        
        if target_row:
            subject_element = target_row.select_one(".board-list-title a")
            
            title = subject_element.text.strip()
            href_value = subject_element.get('href')
            
            match = re.search(r"fn_viewData\('(\d+)'\)", href_value)
            if match:
                post_id = match.group(1)
                full_link = f"{NOTICE_VIEW_URL_BASE}?action={BOARD_ACTION_ID}&schIdx={post_id}"
                
                return {"title": title, "link": full_link}
            else:
                print("링크(href)에서 게시글 ID를 추출하는 데 실패했습니다.")
                return None
                
        else:
            print("최신 공지사항을 찾을 수 없습니다. CSS 선택자('.ui-list tbody tr.board_new')를 확인하세요.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"웹사이트 크롤링 중 오류 발생: {e}")
        return None


def get_recent_posts(limit=5):
    """최근 게시글들을 반환합니다."""
    try:
        response = _make_request_with_retry(NOTICE_URL)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        rows = soup.select(".ui-list tbody tr.board_new")
        
        posts = []
        for row in rows[:limit]:
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
    """DB에 없는 새로운 게시글 목록을 반환합니다."""
    try:
        recent_posts = get_recent_posts(limit=10)
        
        if not recent_posts:
            return []
        
        import database
        
        new_posts = []
        for post in recent_posts:
            if not database.is_post_sent(post["link"]):
                new_posts.append(post)
            else:
                break
        
        return new_posts
        
    except Exception as e:
        print(f"새 게시글 확인 중 오류 발생: {e}")
        return []

