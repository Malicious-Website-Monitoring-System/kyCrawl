import requests
from bs4 import BeautifulSoup
from collections import deque
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import logging
from urllib.parse import urlparse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# 수집된 링크를 저장할 리스트와 방문한 URL을 저장할 집합
crawled_links = []
visited = set()

# 탐색을 진행하지 않는 루트 도메인들을 설정하는 화이트리스트
whitelist = set([
    'donga.com',  # 예시 도메인, 실제 화이트리스트 도메인으로 변경
    'daum.net',
    'naver.com',
    'nonghyup.com',
    'gmarket.co.kr',
    'toastoven.net',
    'kbs.co.kr',
    'kebhana.com',
    'jtbc.co.kr',
    'kfcc.co.kr',
    'roku.com',
    'netflix.com'
    'kyobobook.co.kr',
    'epostbank.go.kr',
    'hbo.com',
    'kakao.com',
    'nexon.com',
    'megabox.co.kr',
    'mt.co.kr',
    'asiae.co.kr',
    'khan.co.kr',
    'kbstar.com',
    'go.kr',
    '11st.co.kr',
    'music-flo.com',
    'imbc.com',
    'ebs.co.kr',
    'kakaobank.com',
    'lottecinema.co.kr',
    'genie.co.kr',
    'yonhapnewstv.co.kr',
    'kakaocorp.com',
    'busan.com',
    'plaync.com',
    'sbs.co.kr',
    'ytn.co.kr',
    'coupang.com',
    'kobis.or.kr',
    'mk.or.kr',
    'millie.co.kr',
    'auction.co.kr',
    'gayeon.com',
    'yes24.com',
    'lotteon.com',
    'co.kr'
])

# 주어진 URL이 화이트리스트에 포함되는지 확인하는 함수
def is_whitelisted(url):
    domain = urlparse(url).netloc
    return any(domain.endswith(whitelisted_domain) for whitelisted_domain in whitelist)

# 주어진 URL에서 링크를 추출하는 함수
def get_urls(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return set()
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        urls = set()
        
        for link in soup.find_all('a', href=True):
            full_url = requests.compat.urljoin(url, link['href'])
            if not is_whitelisted(full_url):
                urls.add(full_url)
            
        for button in soup.find_all('button', onclick=True):
            onclick = button['onclick']
            if "window.location.href" in onclick:
                part = onclick.split('window.location.href=')[1].strip(" '\"")
                full_url = requests.compat.urljoin(url, part)
                if not is_whitelisted(full_url):
                    urls.add(full_url)
        
        for form in soup.find_all('form', action=True):
            full_url = requests.compat.urljoin(url, form['action'])
            if not is_whitelisted(full_url):
                urls.add(full_url)
        
        return urls
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return set()

# BFS 방식으로 링크를 탐색하는 함수
def bfs_crawl(start_url):
    global crawled_links, visited
    queue = deque([(start_url, 0)])
    
    while queue:
        url, depth = queue.popleft()
        
        if url in visited:
            continue
        
        visited.add(url)
        urls = get_urls(url)
        unique_urls = [next_url for next_url in urls if next_url not in visited]
        crawled_links.append((url, unique_urls))
        
        for next_url in unique_urls:
            if next_url not in visited:
                queue.append((next_url, depth + 1))
        
        # 탐색 결과를 실시간으로 반영
        socketio.emit('update', {'url': url, 'urls': unique_urls}, namespace='/')
        socketio.sleep(0)  # 비동기 처리를 위해 sleep 추가
    
    # 큐가 비었을 때 로그 메시지 출력
    print("Crawling completed.")

# BFS 크롤링 실행 함수
def start_crawl():
    start_url = 'https://zzang4.com/'
    bfs_crawl(start_url)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-crawl')
def start_crawl_route():
    global crawled_links, visited
    crawled_links = []
    visited = set()
    threading.Thread(target=start_crawl).start()
    return "Crawling started!"

@app.route('/crawled-links')
def crawled_links_route():
    return jsonify(crawled_links)

if __name__ == '__main__':
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    socketio.run(app, debug=True)
