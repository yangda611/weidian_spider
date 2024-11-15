import requests
import json
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from .proxy_pool import ProxyPool

class PddSpider:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': '',  # 需要添加登录后的Cookie
            'Referer': 'https://mobile.yangkeduo.com/'
        }
        self.output_dir = 'output'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.proxy_pool = ProxyPool()
        
    def parse_url(self, url):
        """解析商品URL，获取商品ID"""
        try:
            if 'yangkeduo.com' in url or 'pinduoduo.com' in url:
                parsed = urlparse(url)
                if 'goods_id' in url:
                    return parse_qs(parsed.query)['goods_id'][0]
                else:
                    return parsed.path.split('/')[-1]
            return None
        except Exception as e:
            print(f"Error parsing URL {url}: {str(e)}")
            return None
            
    def _make_request(self, url, stream=False):
        """统一的请求方法，支持代理和重试"""
        max_retries = 3
        for _ in range(max_retries):
            try:
                proxy = self.proxy_pool.get_random_proxy()
                proxies = {'http': proxy, 'https': proxy} if proxy else None
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    proxies=proxies,
                    timeout=15,
                    stream=stream
                )
                
                if response.status_code == 200:
                    return response
                    
            except Exception as e:
                print(f"Request failed: {str(e)}, retrying...")
                time.sleep(2)
                
        raise Exception(f"Failed to fetch {url} after {max_retries} retries")
        
    def get_product_info(self, url):
        """获取商品详细信息"""
        try:
            goods_id = self.parse_url(url)
            if not goods_id:
                return None
                
            # 这里使用拼多多的API，需要替换为实际的API
            api_url = f'https://mobile.yangkeduo.com/proxy/api/api/goodsDetail?goodsId={goods_id}'
            
            response = self._make_request(api_url)
            data = response.json()
            
            if 'goods_id' not in data:
                return None
                
            product_info = {
                'item_id': goods_id,
                'title': data.get('goods_name', ''),
                'price': data.get('min_group_price', 0) / 100,  # 转换为元
                'original_price': data.get('min_normal_price', 0) / 100,
                'description': data.get('goods_desc', ''),
                'images': ','.join(data.get('gallery_urls', [])),
                'detail_images': ','.join(data.get('detail_gallery_urls', [])),
                'video_url': data.get('video_url', ''),
                'sales_count': data.get('sales_tip', '0').replace('已拼', '').replace('件', ''),
                'stock': data.get('stock', 0),
                'shop_name': data.get('mall_name', ''),
                'url': url
            }
            
            self._download_media(product_info)
            
            return product_info
            
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
            return None
            
    def _download_media(self, product_info):
        """下载商品图片和视频"""
        try:
            safe_title = "".join([c for c in product_info['title'] if c.isalnum() or c in (' ', '-', '_')])
            safe_title = safe_title[:30]
            folder_name = f"拼多多_{safe_title}_{product_info['item_id']}"
            product_dir = os.path.join(self.output_dir, folder_name)
            
            if not os.path.exists(product_dir):
                os.makedirs(product_dir)
                
            main_images_dir = os.path.join(product_dir, '主图')
            detail_images_dir = os.path.join(product_dir, '详情图')
            video_dir = os.path.join(product_dir, '视频')
            
            os.makedirs(main_images_dir, exist_ok=True)
            os.makedirs(detail_images_dir, exist_ok=True)
            os.makedirs(video_dir, exist_ok=True)
            
            # 下载主图
            for i, img_url in enumerate(product_info['images'].split(',')):
                if img_url:
                    self._download_file(img_url, os.path.join(main_images_dir, f'主图_{i+1}.jpg'))
                    
            # 下载详情图
            for i, img_url in enumerate(product_info['detail_images'].split(',')):
                if img_url:
                    self._download_file(img_url, os.path.join(detail_images_dir, f'详情图_{i+1}.jpg'))
                    
            # 下载视频
            if product_info['video_url']:
                self._download_file(product_info['video_url'], os.path.join(video_dir, '视频.mp4'))
                
            # 保存商品信息
            info_file = os.path.join(product_dir, '商品信息.txt')
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"商品标题：{product_info['title']}\n")
                f.write(f"商品ID：{product_info['item_id']}\n")
                f.write(f"价格：{product_info['price']}\n")
                f.write(f"原价：{product_info['original_price']}\n")
                f.write(f"销量：{product_info['sales_count']}\n")
                f.write(f"库存：{product_info['stock']}\n")
                f.write(f"店铺名：{product_info['shop_name']}\n")
                f.write(f"商品链接：{product_info['url']}\n")
                f.write(f"\n商品描述：\n{product_info['description']}\n")
                
        except Exception as e:
            print(f"Error downloading media: {str(e)}")
            
    def _download_file(self, url, filepath):
        """下载文件"""
        try:
            if not url:
                return
            response = self._make_request(url, stream=True)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            print(f"Error downloading file {url}: {str(e)}") 