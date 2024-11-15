from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time
import json
import os

class WeidianSpider:
    def __init__(self):
        self.setup_driver()
        self.output_dir = 'output'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.selectors = {}  # 存储用户选择的选择器

    def setup_driver(self):
        """设置Chrome驱动"""
        options = webdriver.ChromeOptions()
        # 不使用无头模式，让用户可以看到页面
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(30)

    def select_elements(self, url):
        """让用户选择要爬取的元素"""
        try:
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载
            
            # 注入选择器工具的JavaScript代码
            self.driver.execute_script("""
                window.selectedElements = {};
                
                function addSelector(type, element) {
                    // 移除之前的高亮
                    if (window.selectedElements[type]) {
                        window.selectedElements[type].style.outline = '';
                    }
                    // 高亮新选择的元素
                    element.style.outline = '2px solid red';
                    window.selectedElements[type] = element;
                    
                    // 获取元素的选择器
                    return getSelector(element);
                }
                
                function getSelector(element) {
                    // 尝试获取id
                    if (element.id) {
                        return '#' + element.id;
                    }
                    
                    // 尝试获取类名
                    if (element.className) {
                        return '.' + element.className.split(' ')[0];
                    }
                    
                    // 使用元素路径
                    let path = [];
                    while (element.parentElement) {
                        let tag = element.tagName.toLowerCase();
                        let siblings = Array.from(element.parentElement.children);
                        if (siblings.length > 1) {
                            let index = siblings.indexOf(element) + 1;
                            tag += ':nth-child(' + index + ')';
                        }
                        path.unshift(tag);
                        element = element.parentElement;
                    }
                    return path.join(' > ');
                }
                
                // 添加点击事件监听器
                document.addEventListener('click', function(e) {
                    if (window.selectorType) {
                        e.preventDefault();
                        e.stopPropagation();
                        let selector = addSelector(window.selectorType, e.target);
                        window.selectorCallback(window.selectorType, selector);
                    }
                }, true);
            """)
            
            return True
        except Exception as e:
            print(f"Error setting up selector: {str(e)}")
            return False

    def get_product_info(self, url, selected_areas):
        """获取商品信息"""
        try:
            if not self.select_elements(url):
                return None
            
            # 等待用户选择元素
            for area in selected_areas:
                self.wait_for_selection(area)
            
            # 获取选择的元素内容
            product_info = {}
            for area in selected_areas:
                if area in self.selectors:
                    selector = self.selectors[area]
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if area in ['main_images', 'detail_images']:
                            # 对于图片，获取src属性
                            if element.tag_name == 'img':
                                product_info[area] = element.get_attribute('src')
                            else:
                                imgs = element.find_elements(By.TAG_NAME, 'img')
                                product_info[area] = [img.get_attribute('src') for img in imgs]
                        else:
                            # 对于其他元素，获取文本内容
                            product_info[area] = element.text.strip()
                    except Exception as e:
                        print(f"Error getting content for {area}: {str(e)}")
                        product_info[area] = ''
            
            return product_info
            
        except Exception as e:
            print(f"Error getting product info: {str(e)}")
            return None

    def wait_for_selection(self, area_type):
        """等待用户选择元素"""
        self.driver.execute_script("""
            window.selectorType = arguments[0];
            window.selectorCallback = arguments[1];
        """, area_type, self.handle_selection)
        
        # 显示选择提示
        self.driver.execute_script("""
            let tip = document.createElement('div');
            tip.style.position = 'fixed';
            tip.style.top = '10px';
            tip.style.left = '50%';
            tip.style.transform = 'translateX(-50%)';
            tip.style.background = 'rgba(0,0,0,0.8)';
            tip.style.color = 'white';
            tip.style.padding = '10px';
            tip.style.borderRadius = '5px';
            tip.style.zIndex = '10000';
            tip.textContent = '请选择' + arguments[0] + '区域';
            document.body.appendChild(tip);
        """, self.get_area_name(area_type))
        
        # 等待用户选择
        while area_type not in self.selectors:
            time.sleep(0.5)
            
        # 移除提示
        self.driver.execute_script("""
            document.body.removeChild(document.body.lastChild);
            window.selectorType = null;
        """)

    def handle_selection(self, area_type, selector):
        """处理用户的选择"""
        self.selectors[area_type] = selector

    def get_area_name(self, area_type):
        """获取区域类型的中文名称"""
        names = {
            'title': '商品标题',
            'price': '商品价格',
            'specs': '商品规格',
            'main_images': '商品主图',
            'detail_images': '详情图片'
        }
        return names.get(area_type, area_type)

    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass
            