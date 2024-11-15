from .main import WeidianSpider
from .url_processor import URLProcessor

def test_single_url():
    """测试单个URL的爬取"""
    spider = WeidianSpider()
    # 这里替换成实际的商品URL
    test_url = "https://weidian.com/item.html?itemID=12345678"
    result = spider.get_product_info(test_url)
    print("爬取结果:", result)

def test_multiple_urls():
    """测试多个URL的批量爬取"""
    spider = WeidianSpider()
    processor = URLProcessor(spider)
    results = processor.process_urls_from_file('urls.txt')
    processor.save_to_excel(results)

if __name__ == "__main__":
    # 选择要测试的功能
    print("1. 测试单个URL")
    print("2. 测试批量爬取")
    choice = input("请选择测试功能 (1/2): ")
    
    if choice == "1":
        test_single_url()
    elif choice == "2":
        test_multiple_urls() 