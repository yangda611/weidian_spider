from concurrent.futures import ThreadPoolExecutor
import time
import pandas as pd

class URLProcessor:
    def __init__(self, spider):
        self.spider = spider
        
    def process_urls_from_file(self, file_path):
        """从文件中读取URL并处理"""
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
            
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for url in urls:
                time.sleep(2)
                futures.append(executor.submit(self.spider.get_product_info, url))
            
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
                    
        return results
        
    def save_to_excel(self, results, output_file='output/products.xlsx'):
        """将结果保存到Excel文件"""
        df = pd.DataFrame(results)
        df.to_excel(output_file, index=False)
        print(f"Results saved to {output_file}") 