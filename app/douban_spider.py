import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
import time
import random
from fake_useragent import UserAgent
from app.models import Movie, MovieType, db
import json
import logging
import re
import mimetypes
from pathlib import Path
import urllib3
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO
import argparse
from sqlalchemy.exc import SQLAlchemyError
from selenium.common.exceptions import TimeoutException, WebDriverException

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 确保日志目录存在
if not os.path.exists('logs'):
    os.makedirs('logs')

# 确保图片保存目录存在
POSTER_DIR = Path('app/static/posters')
if not POSTER_DIR.exists():
    POSTER_DIR.mkdir(parents=True)

# 配置爬虫日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 如果logger没有处理器，添加新的处理器
if not logger.handlers:
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    try:
        # 文件处理器
        log_file = 'logs/spider.log'
        # 如果文件被占用，尝试使用新的文件名
        if os.path.exists(log_file):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f'logs/spider_{timestamp}.log'
            
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {str(e)}")
        # 继续运行，只使用控制台日志

# 在类定义前添加电影类型映射
MOVIE_TYPES = {
    '总榜': {'name': '总榜', 'url': 'https://movie.douban.com/chart'},
    '剧情': {'name': '剧情', 'url': 'https://movie.douban.com/typerank?type_name=剧情&type=11&interval_id=100:90&action='},
    '喜剧': {'name': '喜剧', 'url': 'https://movie.douban.com/typerank?type_name=喜剧&type=24&interval_id=100:90&action='},
    '动作': {'name': '动作', 'url': 'https://movie.douban.com/typerank?type_name=动作&type=5&interval_id=100:90&action='},
    '爱情': {'name': '爱情', 'url': 'https://movie.douban.com/typerank?type_name=爱情&type=13&interval_id=100:90&action='},
    '科幻': {'name': '科幻', 'url': 'https://movie.douban.com/typerank?type_name=科幻&type=17&interval_id=100:90&action='},
    '动画': {'name': '动画', 'url': 'https://movie.douban.com/typerank?type_name=动画&type=25&interval_id=100:90&action='},
    '悬疑': {'name': '悬疑', 'url': 'https://movie.douban.com/typerank?type_name=悬疑&type=10&interval_id=100:90&action='},
    '惊悚': {'name': '惊悚', 'url': 'https://movie.douban.com/typerank?type_name=惊悚&type=19&interval_id=100:90&action='},
    '恐怖': {'name': '恐怖', 'url': 'https://movie.douban.com/typerank?type_name=恐怖&type=20&interval_id=100:90&action='},
    '纪录片': {'name': '纪录片', 'url': 'https://movie.douban.com/typerank?type_name=纪录片&type=1&interval_id=100:90&action='},
    '短片': {'name': '短片', 'url': 'https://movie.douban.com/typerank?type_name=短片&type=23&interval_id=100:90&action='},
    '情色': {'name': '情色', 'url': 'https://movie.douban.com/typerank?type_name=情色&type=6&interval_id=100:90&action='},
    '音乐': {'name': '音乐', 'url': 'https://movie.douban.com/typerank?type_name=音乐&type=14&interval_id=100:90&action='},
    '歌舞': {'name': '歌舞', 'url': 'https://movie.douban.com/typerank?type_name=歌舞&type=7&interval_id=100:90&action='},
    '家庭': {'name': '家庭', 'url': 'https://movie.douban.com/typerank?type_name=家庭&type=28&interval_id=100:90&action='},
    '儿童': {'name': '儿童', 'url': 'https://movie.douban.com/typerank?type_name=儿童&type=8&interval_id=100:90&action='},
    '传记': {'name': '传记', 'url': 'https://movie.douban.com/typerank?type_name=传记&type=2&interval_id=100:90&action='},
    '历史': {'name': '历史', 'url': 'https://movie.douban.com/typerank?type_name=历史&type=4&interval_id=100:90&action='},
    '战争': {'name': '战争', 'url': 'https://movie.douban.com/typerank?type_name=战争&type=22&interval_id=100:90&action='},
    '犯罪': {'name': '犯罪', 'url': 'https://movie.douban.com/typerank?type_name=犯罪&type=3&interval_id=100:90&action='},
    '西部': {'name': '西部', 'url': 'https://movie.douban.com/typerank?type_name=西部&type=27&interval_id=100:90&action='},
    '奇幻': {'name': '奇幻', 'url': 'https://movie.douban.com/typerank?type_name=奇幻&type=16&interval_id=100:90&action='},
    '冒险': {'name': '冒险', 'url': 'https://movie.douban.com/typerank?type_name=冒险&type=15&interval_id=100:90&action='},
    '灾难': {'name': '灾难', 'url': 'https://movie.douban.com/typerank?type_name=灾难&type=12&interval_id=100:90&action='},
    '武侠': {'name': '武侠', 'url': 'https://movie.douban.com/typerank?type_name=武侠&type=29&interval_id=100:90&action='},
    '古装': {'name': '古装', 'url': 'https://movie.douban.com/typerank?type_name=古装&type=30&interval_id=100:90&action='},
    '运动': {'name': '运动', 'url': 'https://movie.douban.com/typerank?type_name=运动&type=18&interval_id=100:90&action='},
    '黑色电影': {'name': '黑色电影', 'url': 'https://movie.douban.com/typerank?type_name=黑色电影&type=31&interval_id=100:90&action='}
}

class DoubanSpider:
    def __init__(self):
        self.ua = UserAgent()
        self.base_url = "https://movie.douban.com"
        self.movie_url = "https://movie.douban.com/subject/"
        self.search_url = "https://movie.douban.com/j/search_subjects"
        self.session = requests.Session()
        self.driver = None
        self.setup_selenium()
        
        # 初始化计数器
        self.total_movies = 0
        
        # 代理池配置
        self.proxy_pool = []
        self.current_proxy = None
        self.proxy_fail_count = 0
        self.max_proxy_fails = 3
        
        # 生成随机的设备 ID
        self.device_id = ''.join(random.choice('0123456789abcdef') for _ in range(11))
        
        # 设置基础 cookies
        self._init_cookies()
        
        # 设置默认请求头
        self._update_headers()

        # 电影类型列表
        self.movie_types = [
            ("剧情", "11"), ("喜剧", "24"), ("动作", "5"), ("爱情", "13"),
            ("科幻", "17"), ("动画", "25"), ("悬疑", "10"), ("惊悚", "19"),
            ("恐怖", "20"), ("纪录片", "1"), ("短片", "23"), ("情色", "6"),
            ("音乐", "14"), ("歌舞", "7"), ("家庭", "28"), ("儿童", "8"),
            ("传记", "2"), ("历史", "4"), ("战争", "22"), ("犯罪", "3"),
            ("西部", "27"), ("奇幻", "16"), ("冒险", "15"), ("灾难", "12"),
            ("武侠", "29"), ("古装", "30"), ("运动", "18"), ("黑色电影", "31")
        ]

    def setup_selenium(self):
        """设置Selenium"""
        try:
            chrome_options = Options()
            # 基本设置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 禁用GPU相关功能
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-gpu-sandbox')
            chrome_options.add_argument('--disable-accelerated-2d-canvas')
            chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
            chrome_options.add_argument('--disable-accelerated-mjpeg-decode')
            chrome_options.add_argument('--disable-accelerated-video-decode')
            chrome_options.add_argument('--disable-d3d11')
            
            # 内存和性能优化
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            
            # 禁用不必要的功能
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-media-source')
            chrome_options.add_argument('--disable-video-capture')
            chrome_options.add_argument('--disable-audio-capture')
            
            # 设置桌面版 User-Agent
            desktop_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'user-agent={desktop_ua}')
            
            # 设置窗口大小
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 禁用自动化控制特征
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 添加代理设置（如果系统使用了代理）
            system_proxy = requests.utils.get_environ_proxies('https://movie.douban.com', no_proxy=None)
            if system_proxy and 'https' in system_proxy:
                chrome_options.add_argument(f'--proxy-server={system_proxy["https"]}')
                logger.info(f"Using system proxy: {system_proxy['https']}")
            
            # 创建 Chrome 驱动
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # 使用 CDP 命令来修改 navigator.webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false
                    });
                    window.navigator.chrome = {
                        runtime: {},
                    };
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                '''
            })
            
            logger.info("Successfully initialized Selenium WebDriver")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {str(e)}")
            raise

    def _init_cookies(self):
        """初始化cookies"""
        timestamp = int(time.time())
        self.cookies = {
            'bid': self.device_id,
            'll': "118282",
            'ap_v': "0,6.0",
            '_pk_ses.100001.4cf6': '*',
            '_pk_id.100001.4cf6': f'{self.device_id}.{timestamp}.1',
            '__yadk_uid': str(random.randint(10000000, 99999999)),
            'dbcl2': "",
            'ck': self.device_id[:4],
            'push_noty_num': "0",
            'push_doumail_num': "0"
        }
        
        # 更新统计相关的 cookies
        for domain in ['30149280', '223695111']:
            self.cookies.update({
                f'__utma': f'{domain}.{random.randint(1000000000, 9999999999)}.{timestamp}.{timestamp}.{timestamp}.1',
                f'__utmb': f'{domain}.{random.randint(1, 999)}.10.{timestamp}',
                f'__utmc': domain,
                f'__utmz': f'{domain}.{timestamp}.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
                f'__utmt': '1',
                f'__utmv': f'{domain}.8.6/6'
            })
        
        self.session.cookies.update(self.cookies)

    def _update_headers(self):
        """更新请求头，模拟不同的浏览器特征"""
        chrome_versions = ['121.0.0.0', '120.0.0.0', '119.0.0.0']
        platforms = [
            ('Windows NT 10.0; Win64; x64', 'Windows'),
            ('Macintosh; Intel Mac OS X 10_15_7', 'macOS'),
            ('X11; Linux x86_64', 'Linux')
        ]
        
        platform, os_name = random.choice(platforms)
        chrome_version = random.choice(chrome_versions)
        major_version = chrome_version.split('.')[0]
        
        headers = {
            'Host': 'movie.douban.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': f'"Not A(Brand";v="99", "Google Chrome";v="{major_version}", "Chromium";v="{major_version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{os_name}"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ja;q=0.6',
            'DNT': '1',  # Do Not Track
            'Pragma': 'no-cache'
        }
        
        # 随机添加一些额外的头部
        if random.random() < 0.5:
            headers['X-Client-Data'] = 'CIa2yQEIpLbJAQipncoBCKijygEIkqHLAQj6yMwBCPrYzAEIhd3MAQiF+MwB'
        
        self.session.headers.update(headers)

    def _update_proxy_pool(self):
        """更新代理池"""
        try:
            # 使用系统代理
            PROXY_SOURCE = 'system'  # 可选: 'system', 'manual', 'api'
            
            if PROXY_SOURCE == 'system':
                # 获取系统代理设置
                system_proxies = requests.utils.get_environ_proxies('https://movie.douban.com', no_proxy=None)
                if system_proxies:
                    logger.info("Using system proxy configuration")
                    self.proxy_pool = [system_proxies.get('https') or system_proxies.get('http')]
                else:
                    logger.warning("No system proxy found")
                    self.proxy_pool = []
                    
            elif PROXY_SOURCE == 'api':
                # 使用代理服务商API获取代理
                # 示例：快代理API
                api_url = "http://dev.kdlapi.com/api/getproxy/"
                params = {
                    'orderid': 'YOUR_ORDER_ID',  # 替换为您的订单号
                    'num': 100,  # 获取数量
                    'protocol': 2,  # 1:http 2:https
                    'quality': 2,  # 代理质量
                    'format': 'json'
                }
                try:
                    response = requests.get(api_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and 'proxy_list' in data['data']:
                            self.proxy_pool = [f"http://{proxy}" for proxy in data['data']['proxy_list']]
                except Exception as e:
                    logger.error(f"Error fetching proxies from API: {str(e)}")
            
            else:
                # 手动配置代理列表
                self.proxy_pool = [
                    # 格式：'protocol://ip:port' 或 'protocol://username:password@ip:port'
                    # 请替换为您的代理服务器地址
                    'http://proxy1.example.com:8080',
                    'http://proxy2.example.com:8080',
                    # 如果使用带认证的代理，格式如下：
                    # 'http://username:password@proxy.example.com:8080',
                ]
            
            if not self.proxy_pool:
                logger.warning("No proxies available in the pool")
            else:
                logger.info(f"Successfully updated proxy pool with {len(self.proxy_pool)} proxies")
                
        except Exception as e:
            logger.error(f"Failed to update proxy pool: {str(e)}")
            self.proxy_pool = []

    def _get_random_proxy(self):
        """获取随机代理"""
        try:
            if not self.proxy_pool:
                self._update_proxy_pool()
            
            if self.proxy_pool:
                if self.current_proxy and self.proxy_fail_count < self.max_proxy_fails:
                    return self.current_proxy
                
                self.current_proxy = random.choice(self.proxy_pool)
                self.proxy_fail_count = 0
                return self.current_proxy
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting proxy: {str(e)}")
            return None

    def _handle_request_error(self, error, url):
        """处理请求错误"""
        if isinstance(error, requests.exceptions.ProxyError):
            logger.warning(f"Proxy error: {str(error)}")
            self.proxy_fail_count += 1
            if self.proxy_fail_count >= self.max_proxy_fails:
                self.current_proxy = None
                self.proxy_fail_count = 0
            return False
            
        if isinstance(error, requests.exceptions.RequestException):
            logger.warning(f"Request error for {url}: {str(error)}")
            return False
            
        logger.error(f"Unexpected error for {url}: {str(error)}")
        return False

    def _make_request(self, url, method='GET', **kwargs):
        """发送请求的统一接口"""
        try:
            # 使用Selenium访问页面
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))  # 随机延迟
            
            # 获取页面内容
            page_source = self.driver.page_source
            
            # 模拟Response对象
            class MockResponse:
                def __init__(self, content, status_code):
                    self.content = content
                    self.status_code = status_code
                    self.text = content
                    self.url = url
            
            return MockResponse(page_source, 200)
            
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None

    def _simulate_user_behavior(self):
        """模拟用户行为"""
        try:
            # 访问豆瓣首页
            response = self._make_request('https://www.douban.com')
            if not response:
                return False
            time.sleep(random.uniform(2, 4))
            
            # 访问电影首页
            response = self._make_request(self.base_url)
            if not response:
                return False
            time.sleep(random.uniform(2, 4))
            
            # 随机访问一些分类页面
            categories = ['classic', 'newest', 'playable', 'top250']
            for _ in range(random.randint(1, 2)):
                category = random.choice(categories)
                response = self._make_request(f'{self.base_url}/{category}')
                if not response:
                    continue
                time.sleep(random.uniform(3, 5))
            
            return True
            
        except Exception as e:
            logger.warning(f"Error in simulating user behavior: {str(e)}")
            return False

    def _download_poster(self, url):
        """下载电影海报"""
        if not url:
            return None, None
            
        try:
            # 获取高清海报链接
            url = url.replace('s_ratio_poster', 'l')
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://movie.douban.com/'
            }
            
            # 最多重试3次
            for attempt in range(3):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        # 获取MIME类型
                        content_type = response.headers.get('content-type', '')
                        if 'image' in content_type.lower():
                            return response.content, content_type
                        else:
                            logger.warning(f"下载的内容不是图片: {content_type}")
                            return None, None
                    else:
                        logger.warning(f"下载海报失败，状态码: {response.status_code}")
                        time.sleep(random.uniform(1, 2))  # 随机等待1-2秒后重试
                except requests.RequestException as e:
                    logger.warning(f"下载海报出错 (尝试 {attempt + 1}/3): {str(e)}")
                    if attempt < 2:  # 如果不是最后一次尝试，等待后重试
                        time.sleep(random.uniform(1, 2))
                    continue
                    
            return None, None
            
        except Exception as e:
            logger.error(f"下载海报时发生错误: {str(e)}")
            return None, None

    def search_movies(self, tag):
        """搜索指定标签的电影"""
        try:
            # 获取类型信息
            type_info = MOVIE_TYPES.get(tag)
            if not type_info:
                logger.warning(f"未知的电影类型: {tag}")
                return []
            
            url = type_info['url']
            logger.info(f"访问电影页面: {url}")
            
            # 访问页面
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载
            
            # 使用BeautifulSoup解析页面
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            movies = []
            
            if tag == '热门':
                # 处理排行榜页面
                movie_items = soup.select('tr.item')
            else:
                # 处理其他类型页面
                movie_items = soup.select('.movie-list-item') or \
                             soup.select('.item') or \
                             soup.select('.movie-item-title')
            
            if not movie_items:
                logger.warning(f"No movie items found for tag: {tag}")
                return []
            
            logger.info(f"Found {len(movie_items)} movies for tag: {tag}")
            
            for item in movie_items[:100]:  # 修改这里
                try:
                    # 查找标题和链接
                    if tag == '热门':
                        title_elem = item.select_one('.title a') or item.select_one('a.title')
                    else:
                        title_elem = item.select_one('a') or item.select_one('.title')
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    movie_url = title_elem.get('href', '')
                    douban_id = re.search(r'/subject/(\d+)/', movie_url)
                    if not douban_id:
                        continue
                    douban_id = douban_id.group(1)
                    
                    # 获取评分
                    rate_elem = item.select_one('.rating_nums') or item.select_one('.rating_num') or item.select_one('.rating')
                    rate = float(rate_elem.get_text(strip=True)) if rate_elem else 0.0
                    
                    # 获取年份
                    year_elem = item.select_one('.year') or item.select_one('.pub')
                    year = ''
                    if year_elem:
                        year_match = re.search(r'\((\d{4})\)', year_elem.get_text())
                        year = year_match.group(1) if year_match else ''
                    
                    # 获取导演
                    info_elem = item.select_one('.info') or item.select_one('.abstract')
                    director = ''
                    if info_elem:
                        info_text = info_elem.get_text()
                        director_match = re.search(r'导演:([^/]+)', info_text)
                        director = director_match.group(1).strip() if director_match else ''
                    
                    # 获取海报URL
                    poster_elem = item.select_one('img')
                    poster_url = poster_elem.get('src', '') if poster_elem else ''
                    
                    movies.append({
                        'id': douban_id,
                        'title': title,
                        'rate': rate,
                        'year': year,
                        'director': director,
                        'poster_url': poster_url
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing movie item: {str(e)}")
                    continue
            
            return movies
            
        except Exception as e:
            logger.error(f"Error in search_movies for tag {tag}: {str(e)}")
            return []

    def crawl_without_login(self):
        """爬取电影数据"""
        try:
            logger.info("开始爬取电影数据...")
            total_movies = 0
            
            for tag, type_info in MOVIE_TYPES.items():
                try:
                    logger.info(f"正在爬取 {tag} 类型的电影")
                    movies = self.search_movies(tag)
                    
                    if not movies:
                        logger.warning(f"未找到 {tag} 类型的电影")
                        continue
                        
                    # 确保MovieType存在
                    movie_type = MovieType.query.filter_by(name=type_info['name']).first()
                    if not movie_type:
                        movie_type = MovieType(name=type_info['name'])
                        db.session.add(movie_type)
                        db.session.commit()
                        logger.info(f"创建新的电影类型: {type_info['name']}")

                    for movie_data in movies:
                        try:
                            # 检查电影是否已存在
                            existing_movie = Movie.query.filter_by(douban_id=movie_data['id']).first()
                            if existing_movie:
                                logger.info(f"电影 {movie_data['title']} 已存在，跳过...")
                                continue

                            # 获取电影详细信息
                            movie_detail = self.get_movie_detail(movie_data['id'])
                            if not movie_detail:
                                logger.warning(f"无法获取电影 {movie_data['id']} 的详细信息，跳过...")
                                continue

                            # 创建新电影记录
                            new_movie = Movie(
                                douban_id=movie_detail['douban_id'],
                                title=movie_detail['title'],
                                original_title=movie_detail.get('original_title'),
                                year=movie_detail.get('year'),
                                directors=movie_detail.get('directors', ''),
                                writers=movie_detail.get('writers', ''),
                                actors=movie_detail.get('actors', ''),
                                countries=movie_detail.get('countries', ''),
                                languages=movie_detail.get('languages', ''),
                                release_date=movie_detail.get('release_date'),
                                runtime=movie_detail.get('runtime'),
                                rating=movie_detail.get('rating'),
                                rating_count=movie_detail.get('rating_count'),
                                summary=movie_detail.get('summary', ''),
                                poster_url=movie_detail.get('poster_url'),
                                poster_data=movie_detail.get('poster_data'),
                                poster_mimetype=movie_detail.get('poster_mimetype'),
                                tags=movie_detail.get('tags', '')
                            )
                            
                            # 关联电影类型
                            new_movie.types.append(movie_type)
                            
                            # 保存到数据库
                            db.session.add(new_movie)
                            db.session.commit()
                            total_movies += 1
                            logger.info(f"成功添加电影: {new_movie.title}")
                            
                        except Exception as e:
                            logger.error(f"保存电影 {movie_data.get('title', 'Unknown')} 时出错: {str(e)}")
                            db.session.rollback()
                            continue

                    # 每个分类爬取完成后等待一段随机时间
                    time.sleep(random.uniform(3, 5))
                    
                except Exception as e:
                    logger.error(f"爬取 {tag} 类型时出错: {str(e)}")
                    time.sleep(30)  # 连接错误后等待30秒
                    continue
                
            logger.info(f"爬取完成。共添加 {total_movies} 部电影")
            return total_movies
            
        except Exception as e:
            logger.error(f"爬取过程中出错: {str(e)}")
            return 0

    def get_movie_detail(self, movie_id):
        """获取电影详细信息"""
        url = f'https://movie.douban.com/subject/{movie_id}/'
        logger.info(f"获取电影详情: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "content"))
            )
            
            # 使用BeautifulSoup解析页面
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 提取基本信息
            title = soup.select_one('h1 span[property="v:itemreviewed"]').text.strip()
            year = soup.select_one('.year').text.strip('()')
            
            # 提取评分信息
            try:
                rating = float(soup.select_one('.rating_num').text.strip())
                rating_people = soup.select_one('.rating_people span').text
                rating_count = int(rating_people) if rating_people else 0
            except:
                rating = 0.0
                rating_count = 0
            
            # 提取信息字典
            info_text = soup.select_one('#info').text
            info_dict = {}
            for line in info_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            # 提取其他信息
            directors = info_dict.get('导演', '')
            writers = info_dict.get('编剧', '')
            actors = info_dict.get('主演', '')
            countries = info_dict.get('制片国家/地区', '')
            languages = info_dict.get('语言', '')
            release_date = info_dict.get('上映日期', '')
            
            # 处理片长
            runtime_str = info_dict.get('片长', '')
            runtime = None
            if runtime_str:
                runtime_match = re.search(r'(\d+)', runtime_str)
                if runtime_match:
                    runtime = int(runtime_match.group(1))
            
            # 提取剧情简介
            summary = ''
            # 尝试多个可能的选择器
            summary_selectors = [
                'span[property="v:summary"]',  # 新版页面
                'span.all.hidden',  # 完整简介（隐藏的）
                'div#link-report span.short',  # 短简介
                'div.related-info div.indent span',  # 另一种结构
                'div#link-report',  # 通用选择器
            ]
            
            for selector in summary_selectors:
                summary_elem = soup.select_one(selector)
                if summary_elem:
                    summary = summary_elem.text.strip()
                    # 如果找到非空简介，就跳出循环
                    if summary:
                        break
            
            # 清理简介文本
            if summary:
                # 移除多余的空白字符
                summary = re.sub(r'\s+', ' ', summary)
                # 移除"©豆瓣"等版权信息
                summary = re.sub(r'©豆瓣.*$', '', summary)
                # 移除展开全部等按钮文本
                summary = re.sub(r'展开全部|收起', '', summary)
            
            # 提取海报
            poster_url = ''
            poster_data = None
            poster_mimetype = None
            poster_elem = soup.select_one('#mainpic img')
            if poster_elem:
                poster_url = poster_elem.get('src', '')
                if poster_url:
                    poster_data, poster_mimetype = self._download_poster(poster_url)
            
            # 构建电影数据
            movie_data = {
                'douban_id': movie_id,
                'title': title,
                'original_title': info_dict.get('原名', ''),
                'year': year,
                'directors': directors,
                'writers': writers,
                'actors': actors,
                'countries': countries,
                'languages': languages,
                'release_date': release_date,
                'runtime': runtime,
                'rating': rating,
                'rating_count': rating_count,
                'summary': summary,
                'poster_url': poster_url,
                'poster_data': poster_data,
                'poster_mimetype': poster_mimetype
            }
            
            return movie_data
            
        except Exception as e:
            logger.error(f"获取电影详情时出错: {str(e)}")
            return None

    def crawl_and_save(self, tag='热门', limit=20):
        """爬取并保存电影数据"""
        try:
            # 搜索电影
            movies = self.search_movies(tag)
            if not movies:
                logger.warning(f"No movies found for tag: {tag}")
                return 0

            saved_count = 0
            for movie in movies:
                try:
                    movie_id = movie.get('id')
                    if not movie_id:
                        continue

                    # 检查电影是否已存在
                    existing_movie = Movie.query.filter_by(douban_id=movie_id).first()
                    if existing_movie:
                        # 检查电影是否已经关联了当前类型
                        if movie_type not in existing_movie.types:
                            existing_movie.types.append(movie_type)
                            db.session.commit()
                            logger.info(f"电影 {existing_movie.title} 已存在，添加新类型: {type_name}")
                        else:
                            logger.info(f"电影 {existing_movie.title} 已存在且已关联类型 {type_name}，跳过...")
                        continue
                    
                    # 获取详细信息
                    movie_detail = self.get_movie_detail(movie_id)
                    if not movie_detail:
                        continue

                    # 创建新电影记录
                    new_movie = Movie(
                        douban_id=movie_detail['douban_id'],
                        title=movie_detail['title'],
                        year=movie_detail['year'],
                        directors=movie_detail.get('directors', ''),
                        writers=movie_detail.get('writers', ''),
                        actors=movie_detail.get('actors', ''),
                        countries=movie_detail.get('countries', ''),
                        languages=movie_detail.get('languages', ''),
                        release_date=movie_detail.get('release_date'),
                        runtime=movie_detail.get('runtime'),
                        rating=movie_detail.get('rating'),
                        rating_count=movie_detail.get('rating_count'),
                        summary=movie_detail.get('summary', ''),
                        poster_url=movie_detail.get('poster_url'),
                        poster_data=movie_detail.get('poster_data'),
                        poster_mimetype=movie_detail.get('poster_mimetype'),
                        tags=movie_detail.get('tags', '')
                    )

                    db.session.add(new_movie)
                    db.session.commit()
                    saved_count += 1
                    logger.info(f"Successfully saved movie: {movie_detail['title']}")

                except Exception as e:
                    logger.error(f"Error saving movie: {str(e)}")
                    db.session.rollback()
                    continue

                # 添加延迟避免请求过快
                time.sleep(random.uniform(2, 4))

            return saved_count

        except Exception as e:
            logger.error(f"Error in crawl_and_save: {str(e)}")
            return 0

    def init_db(self):
        """初始化数据库，爬取电影数据"""
        logger.info("Starting to initialize database...")
        
        # 电影标签列表
        tags = [
            '热门', '最新', '经典', '华语', '欧美', '韩国', '日本', 
            '动作', '喜剧', '爱情', '科幻', '悬疑', '恐怖', '动画',
            '剧情', '犯罪', '奇幻', '冒险'
        ]
        
        total_movies = 0
        
        try:
            for tag in tags:
                logger.info(f"Fetching movies for tag: {tag}")
                movies = self.search_movies(tag)
                
                if not movies:
                    logger.warning(f"No movies found for tag: {tag}")
                    continue
                
                # 限制每个标签最多处理5部电影，避免请求过多被封
                for movie in movies[:5]:
                    movie_id = movie.get('id')
                    
                    # 检查电影是否已存在
                    existing_movie = Movie.query.filter_by(douban_id=movie_id).first()
                    if existing_movie:
                        logger.info(f"Movie {movie_id} already exists, skipping...")
                        continue
                    
                    # 获取电影详细信息
                    movie_detail = self.get_movie_detail(movie_id)
                    
                    if movie_detail:
                        try:
                            # 创建新的电影记录
                            new_movie = Movie(
                                douban_id=movie_detail['douban_id'],
                                title=movie_detail['title'],
                                year=movie_detail['year'],
                                directors=movie_detail.get('directors', ''),
                                writers=movie_detail.get('writers', ''),
                                actors=movie_detail.get('actors', ''),
                                countries=movie_detail.get('countries', ''),
                                languages=movie_detail.get('languages', ''),
                                release_date=movie_detail.get('release_date'),
                                runtime=movie_detail.get('runtime'),
                                rating=movie_detail.get('rating'),
                                rating_count=movie_detail.get('rating_count'),
                                summary=movie_detail.get('summary', ''),
                                poster_url=movie_detail.get('poster_url'),
                                poster_data=movie_detail.get('poster_data'),
                                poster_mimetype=movie_detail.get('poster_mimetype'),
                                tags=movie_detail.get('tags', '')
                            )
                            
                            db.session.add(new_movie)
                            db.session.commit()
                            total_movies += 1
                            logger.info(f"Successfully added movie: {movie_detail['title']}")
                            
                        except Exception as e:
                            logger.error(f"Error saving movie {movie_id} to database: {str(e)}")
                            db.session.rollback()
                    
                    # 随机延迟，避免请求过快
                    time.sleep(random.uniform(2, 4))
                
                # 每个标签处理完后多等待一会
                time.sleep(random.uniform(3, 5))
        
        except Exception as e:
            logger.error(f"Error during database initialization: {str(e)}")
            db.session.rollback()
        
        logger.info(f"Database initialization completed. Total movies added: {total_movies}")
        return total_movies

    def login_with_sms(self):
        """使用短信验证码登录豆瓣"""
        try:
            print("\n=== 豆瓣登录程序 ===")
            print("请保持浏览器窗口打开，按照提示操作...\n")
            
            # 访问豆瓣首页
            try:
                print("正在打开豆瓣首页...")
                self.driver.get('https://www.douban.com/')
                time.sleep(5)  # 增加等待时间
                
                # 只清除特定的cookie而不是全部清除
                for cookie in self.driver.get_cookies():
                    if 'douban.com' in cookie['domain']:
                        self.driver.delete_cookie(cookie['name'])
                
                print("等待页面加载完成...")
                # 等待页面完全加载
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 确保登录按钮可见
                print("查找登录按钮...")
                try:
                    login_btn = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "登录"))
                    )
                    print("找到登录按钮，点击中...")
                    login_btn.click()
                    time.sleep(3)  # 增加点击后的等待时间
                except Exception as e:
                    print("未找到常规登录按钮，尝试备用方式...")
                    # 尝试直接访问登录页面
                    self.driver.get('https://accounts.douban.com/passport/login')
                    time.sleep(5)
                
                # 等待登录框加载
                print("等待登录框加载...")
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "account-body"))
                )
                time.sleep(2)
                
                # 切换到密码登录
                print("切换到密码登录方式...")
                try:
                    password_login = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "account-tab-account"))
                    )
                    password_login.click()
                    time.sleep(2)
                except Exception as e:
                    print("已经在密码登录页面或切换失败，继续下一步...")
                
                # 输入手机号
                print("\n第1步：输入手机号")
                print("----------------------------------------")
                phone_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                phone_number = input("请输入手机号（必须是已注册豆瓣的手机号）: ")
                phone_input.clear()  # 清除可能的默认值
                phone_input.send_keys(phone_number)
                time.sleep(2)
                
                # 输入密码
                print("\n第2步：输入密码")
                print("----------------------------------------")
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                password = input("请输入密码: ")
                password_input.clear()  # 清除可能的默认值
                password_input.send_keys(password)
                time.sleep(2)
                
                # 点击登录按钮
                print("\n正在登录...")
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "account-form-field-submit"))
                )
                login_button.click()
                
                # 等待登录成功
                try:
                    print("\n正在验证登录状态，请稍候...")
                    WebDriverWait(self.driver, 30).until(
                        lambda driver: 'accounts.douban.com' not in driver.current_url
                    )
                    print("\n登录成功！")
                    
                    # 保存登录后的cookies
                    cookies = self.driver.get_cookies()
                    for cookie in cookies:
                        self.session.cookies.set(cookie['name'], cookie['value'])
                    
                    # 额外等待一下，确保页面完全加载
                    time.sleep(5)
                    return True
                    
                except Exception as e:
                    print("\n登录失败，请检查账号密码是否正确")
                    logger.error(f"Login verification failed: {str(e)}")
                    return False
                
            except Exception as e:
                logger.error(f"Error during login process: {str(e)}")
                print("\n登录过程中出现错误，请重试")
                return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            print("\n登录失败，请重试")
            return False

    def print_stats(self):
        """打印数据库统计信息"""
        try:
            movie_count = Movie.query.count()
            type_count = MovieType.query.count()
            
            print("\n数据库统计:")
            print(f"- 电影总数: {movie_count}")
            print(f"- 类型总数: {type_count}")
            
            # 按类型统计电影数量
            print("\n各类型电影数量:")
            for movie_type in MovieType.query.all():
                count = len(movie_type.movies)
                print(f"- {movie_type.name}: {count}部")
                
        except Exception as e:
            logger.error(f"获取统计信息时出错: {str(e)}")

    def __del__(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def save_movie(self, movie_data):
        """保存电影数据到数据库"""
        try:
            # 检查电影是否已存在
            existing_movie = Movie.query.filter_by(douban_id=movie_data['douban_id']).first()
            if existing_movie:
                logger.info(f"电影已存在: {movie_data['title']}")
                return existing_movie

            # 创建新的电影对象
            movie = Movie(
                douban_id=movie_data['douban_id'],
                title=movie_data['title'],
                original_title=movie_data.get('original_title'),
                directors=movie_data.get('directors', ''),
                writers=movie_data.get('writers', ''),
                actors=movie_data.get('actors', ''),
                year=movie_data.get('year'),
                summary=movie_data.get('summary', ''),
                rating=movie_data.get('rating'),
                rating_count=movie_data.get('rating_count'),
                runtime=movie_data.get('runtime'),
                release_date=movie_data.get('release_date'),
                languages=movie_data.get('languages', ''),
                countries=movie_data.get('countries', ''),
                poster_url=movie_data.get('poster_url')
            )

            # 处理海报数据
            if movie_data.get('poster_data'):
                movie.poster_data = movie_data['poster_data']

            # 处理电影类型
            if movie_data.get('types'):
                for type_name in movie_data['types']:
                    movie_type = MovieType.query.filter_by(name=type_name).first()
                    if not movie_type:
                        logger.info(f"创建新的电影类型: {type_name}")
                        movie_type = MovieType(name=type_name)
                        db.session.add(movie_type)
                        try:
                            db.session.flush()
                        except SQLAlchemyError as e:
                            logger.error(f"创建电影类型时出错: {str(e)}")
                            db.session.rollback()
                            continue
                    movie.types.append(movie_type)

            # 保存电影
            db.session.add(movie)
            db.session.commit()
            logger.info(f"成功保存电影: {movie.title}")
            return movie

        except SQLAlchemyError as e:
            logger.error(f"保存电影数据时出错: {str(e)}")
            db.session.rollback()
            return None

    def crawl_single_type(self, type_name):
        """爬取指定类型的电影"""
        if type_name not in MOVIE_TYPES:
            logger.error(f"未知的电影类型: {type_name}")
            return

        logger.info(f"开始爬取 {type_name} 类型的电影")
        url = MOVIE_TYPES[type_name]['url']
        
        try:
            # 获取或创建电影类型对象
            movie_type = MovieType.query.filter_by(name=type_name).first()
            if not movie_type:
                movie_type = MovieType(name=type_name)
                db.session.add(movie_type)
                db.session.commit()

            # 访问页面
            logger.info(f"正在访问页面: {url}")
            self.driver.get(url)
            time.sleep(5)  # 等待页面加载
            
            # 滚动页面以加载更多内容
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            movie_count = 0
            max_retries = 10  # 最大重试次数
            retries = 0
            
            while movie_count < 100 and retries < max_retries:  # 设置目标电影数量为100
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待内容加载
                
                # 获取新的页面高度
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # 使用BeautifulSoup解析当前页面内容
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # 获取电影元素
                movie_elements = []
                selectors = [
                    ".grid-view .item",
                    ".movie-list-item",
                    ".item",
                    ".movie-item-title",
                    "a[href*='/subject/']"
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        movie_elements = elements
                        break
                
                current_count = len(movie_elements)
                logger.info(f"当前找到 {current_count} 部电影")
                
                # 如果高度没有变化且电影数量没有增加，增加重试次数
                if new_height == last_height and current_count == movie_count:
                    retries += 1
                    logger.info(f"页面未加载新内容，重试 {retries}/{max_retries}")
                    time.sleep(2)
                else:
                    movie_count = current_count
                    last_height = new_height
                    retries = 0
            
            logger.info(f"共找到 {movie_count} 部电影")
            
            # 处理找到的电影
            processed_ids = set()
            processed_count = 0
            
            for item in movie_elements:
                try:
                    # 获取电影链接
                    link = None
                    href = None
                    
                    if item.name == 'a':
                        href = item.get('href', '')
                    else:
                        link_elem = (
                            item.select_one('a[href*="/subject/"]') or
                            item.select_one('.title a') or
                            item.select_one('a.title') or
                            item.select_one('a')
                        )
                        if link_elem:
                            href = link_elem.get('href', '')
                    
                    if href and '/subject/' in href:
                        movie_id = re.search(r'/subject/(\d+)/', href)
                        if movie_id:
                            movie_id = movie_id.group(1)
                            if movie_id not in processed_ids:
                                # 检查电影是否已存在
                                existing_movie = Movie.query.filter_by(douban_id=movie_id).first()
                                if existing_movie:
                                    logger.info(f"电影已存在: {movie_id}")
                                    continue
                                
                                # 获取电影详情
                                logger.info(f"正在获取电影 {movie_id} 的详细信息")
                                movie_data = self.get_movie_detail(movie_id)
                                if movie_data:
                                    movie_data['types'] = [type_name]
                                    if self.save_movie(movie_data):
                                        processed_count += 1
                                        processed_ids.add(movie_id)
                                        logger.info(f"成功保存电影: {movie_data.get('title', 'Unknown')} ({processed_count}/{movie_count})")
                                
                                # 随机延迟
                                time.sleep(random.uniform(3, 5))
                
                except Exception as e:
                    logger.error(f"处理电影时出错: {str(e)}")
                    continue

            logger.info(f"完成爬取 {type_name} 类型的电影，共处理 {processed_count} 部")
            
        except Exception as e:
            logger.error(f"爬取电影类型 {type_name} 时出错: {str(e)}")
        
        finally:
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"提交数据库更改时出错: {str(e)}")
                db.session.rollback()

    def get_movie_list(self, type_name):
        """获取指定类型的电影列表"""
        try:
            # 获取电影类型对应的URL
            type_url = self.MOVIE_TYPES.get(type_name)
            if not type_url:
                logger.error(f"未知的电影类型: {type_name}")
                return []

            # 访问电影列表页面
            logger.info(f"正在获取 {type_name} 类型的电影列表...")
            self.driver.get(type_url)
            
            # 等待电影列表加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "item"))
            )
            
            # 获取电影列表
            movie_items = self.driver.find_elements(By.CLASS_NAME, "item")
            movie_list = []
            
            for item in movie_items[:100]:  # 修改这里
                try:
                    # 获取电影链接和ID
                    link_elem = item.find_element(By.CLASS_NAME, "title")
                    movie_url = link_elem.get_attribute("href")
                    douban_id = movie_url.split('/')[-2]
                    
                    # 检查电影是否已存在
                    if Movie.query.filter_by(douban_id=douban_id).first():
                        logger.info(f"电影已存在，跳过: {link_elem.text}")
                        continue
                    
                    movie_list.append({
                        'url': movie_url,
                        'douban_id': douban_id,
                        'title': link_elem.text
                    })
                    
                except Exception as e:
                    logger.warning(f"处理电影列表项时出错: {str(e)}")
                    continue
                    
                # 随机等待0.5-1.5秒
                time.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"成功获取 {len(movie_list)} 部 {type_name} 类型的电影")
            return movie_list
            
        except TimeoutException:
            logger.error(f"等待电影列表加载超时: {type_name}")
            return []
        except WebDriverException as e:
            logger.error(f"获取电影列表时出现WebDriver错误: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取电影列表时出现未知错误: {str(e)}")
            return []

def init_movies():
    """初始化电影数据"""
    spider = DoubanSpider()
    tags = [
        '热门', '最新', '经典', '豆瓣高分', '华语', '欧美',
        '动作', '喜剧', '爱情', '科幻', '悬疑', '恐怖',
        '动画', '纪录片', '音乐', '剧情', '战争', '犯罪'
    ]
    total_saved = 0
    
    for tag in tags:
        try:
            logger.info(f"Crawling movies with tag: {tag}")
            spider.crawl_and_save(tag=tag, limit=5)  # 每个标签爬取5部电影
            time.sleep(random.uniform(3, 6))  # 在不同标签之间添加较长延迟
        except Exception as e:
            logger.error(f"Error crawling tag {tag}: {str(e)}")
            continue
    
    # 获取已保存的电影数量
    from app import create_app
    with create_app().app_context():
        total_movies = Movie.query.count()
        logger.info(f"Total movies in database: {total_movies}")

def main():
    parser = argparse.ArgumentParser(description='豆瓣电影爬虫')
    parser.add_argument('--type', type=str, required=True, help='要爬取的电影类型名称，如：剧情、喜剧、动作等')
    args = parser.parse_args()
    
    # 检查类型是否存在
    if args.type not in MOVIE_TYPES:
        print(f"错误：未知的电影类型 '{args.type}'")
        print("\n可用的电影类型：")
        for type_name in MOVIE_TYPES.keys():
            print(f"- {type_name}")
        return
    
    # 创建Flask应用上下文
    from app import create_app
    app = create_app()
    
    with app.app_context():
        spider = DoubanSpider()
        try:
            print(f"\n开始爬取 {args.type} 类型的电影...")
            spider.crawl_single_type(args.type)
        finally:
            if spider.driver:
                spider.driver.quit()

if __name__ == "__main__":
    main() 