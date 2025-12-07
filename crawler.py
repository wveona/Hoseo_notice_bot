# crawler.py
import requests
from bs4 import BeautifulSoup
import re
import time
import random

NOTICE_URL = "https://www.hoseo.ac.kr/Home//BBSList.mbz?action=MAPP_1708240139&pageIndex=1"
NOTICE_VIEW_URL_BASE = "https://www.hoseo.ac.kr/Home//BBSView.mbz"
BOARD_ACTION_ID = "MAPP_1708240139"

def _make_request_with_retry(url, max_retries=3, initial_delay=2):
    """HTTP 요청을 재시도 로직과 함께 실행합니다."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.hoseo.ac.kr/'
    }
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = initial_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"재시도 {attempt}/{max_retries - 1} - {delay:.2f}초 대기 중...")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', initial_delay * (2 ** attempt)))
                print(f"HTTP 429 발생 - {retry_after}초 후 재시도...")
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    response.raise_for_status()
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429 and attempt < max_retries - 1:
                retry_after = int(e.response.headers.get('Retry-After', initial_delay * (2 ** attempt)))
                print(f"HTTP 429 예외 발생 - {retry_after}초 후 재시도...")
                time.sleep(retry_after)
                continue
            raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                continue
            raise
    
    raise requests.exceptions.RequestException("최대 재시도 횟수 초과")


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

