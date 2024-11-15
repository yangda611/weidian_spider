import requests
import random
import time
from bs4 import BeautifulSoup
from queue import Queue
import threading
import logging

class ProxyPool:
    def __init__(self):
        self.proxies = Queue()
        self.valid_proxies = []
        self.test_url = 'https://weidian.com'
        self.lock = threading.Lock()
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger('proxy_pool')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('proxy_pool.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def get_proxies_from_kuaidaili(self):
        """从快代理获取免费代理"""
        try:
            url = 'https://www.kuaidaili.com/free/inha/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tr in soup.select('#list tbody tr'):
                ip = tr.select('td[data-title="IP"]')[0].text
                port = tr.select('td[data-title="PORT"]')[0].text
                proxy = f'http://{ip}:{port}'
                self.proxies.put(proxy)
                
        except Exception as e:
            self.logger.error(f"Error fetching proxies from kuaidaili: {str(e)}")

    def get_proxies_from_89ip(self):
        """从89免费代理获取代理"""
        try:
            url = 'https://www.89ip.cn/index_1.html'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tr in soup.select('tbody tr'):
                ip = tr.select('td')[0].text.strip()
                port = tr.select('td')[1].text.strip()
                proxy = f'http://{ip}:{port}'
                self.proxies.put(proxy)
                
        except Exception as e:
            self.logger.error(f"Error fetching proxies from 89ip: {str(e)}")

    def verify_proxy(self, proxy):
        """验证代理是否可用"""
        try:
            response = requests.get(
                self.test_url,
                proxies={'http': proxy, 'https': proxy},
                timeout=10
            )
            if response.status_code == 200:
                with self.lock:
                    self.valid_proxies.append(proxy)
                self.logger.info(f"Valid proxy found: {proxy}")
                return True
        except:
            return False
        return False

    def refresh_proxies(self):
        """刷新代理池"""
        self.valid_proxies.clear()
        while not self.proxies.empty():
            self.proxies.get()
            
        self.get_proxies_from_kuaidaili()
        time.sleep(1)  # 避免请求过快
        self.get_proxies_from_89ip()
        
        # 验证代理
        threads = []
        while not self.proxies.empty():
            proxy = self.proxies.get()
            t = threading.Thread(target=self.verify_proxy, args=(proxy,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.logger.info(f"Proxy pool refreshed. Valid proxies: {len(self.valid_proxies)}")

    def get_random_proxy(self):
        """获取随机代理"""
        if not self.valid_proxies:
            self.refresh_proxies()
        return random.choice(self.valid_proxies) if self.valid_proxies else None 