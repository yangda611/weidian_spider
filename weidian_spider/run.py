from main import WeidianSpider
from url_processor import URLProcessor

def main():
    # 创建爬虫实例
    spider = WeidianSpider()
    processor = URLProcessor(spider)
    
    # 从文件读取URL并处理
    results = processor.process_urls_from_file('urls.txt')
    
    # 保存结果到Excel
    processor.save_to_excel(results)

if __name__ == "__main__":
    main() 