import pandas as pd
import json
from datetime import datetime, timedelta
import os

class DataAnalyzer:
    """数据分析器"""
    def __init__(self, db_manager):
        self.db = db_manager
        self.export_dir = 'exports'
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def analyze_crawl_stats(self, days=30):
        """分析爬取统计数据"""
        stats = self.db.get_statistics(days)
        df = pd.DataFrame(stats)
        
        # 计算成功率
        df['success_rate'] = df['success'] / df['total'] * 100
        
        # 按平台分组统计
        platform_stats = df.groupby('platform').agg({
            'total': 'sum',
            'success': 'sum',
            'failed': 'sum',
            'success_rate': 'mean'
        }).round(2)
        
        return {
            'daily_stats': df.to_dict('records'),
            'platform_stats': platform_stats.to_dict('index')
        }

    def export_batch_data(self, record_ids, format='excel'):
        """批量导出数据"""
        try:
            records = self.db.get_records_by_ids(record_ids)
            if not records:
                return False, "没有找到记录"
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == 'excel':
                return self._export_to_excel(records, timestamp)
            elif format == 'json':
                return self._export_to_json(records, timestamp)
            elif format == 'csv':
                return self._export_to_csv(records, timestamp)
            else:
                return False, "不支持的导出格式"
                
        except Exception as e:
            return False, f"导出失败: {str(e)}"

    def _export_to_excel(self, records, timestamp):
        """导出到Excel"""
        try:
            # 准备数据
            data = []
            for record in records:
                record_data = json.loads(record['data'])
                data.append({
                    '时间': record['timestamp'],
                    '平台': record['platform'],
                    '商品标题': record_data.get('title', ''),
                    '价格': record_data.get('price', ''),
                    '规格': ', '.join(record_data.get('specs', [])),
                    '商品链接': record['url'],
                    '主图数量': len(record_data.get('main_images', [])),
                    '详情图数量': len(record_data.get('detail_images', []))
                })
            
            df = pd.DataFrame(data)
            file_path = os.path.join(self.export_dir, f'export_{timestamp}.xlsx')
            df.to_excel(file_path, index=False)
            
            return True, file_path
            
        except Exception as e:
            return False, f"Excel导出失败: {str(e)}"

    def _export_to_json(self, records, timestamp):
        """导出到JSON"""
        try:
            file_path = os.path.join(self.export_dir, f'export_{timestamp}.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            return True, file_path
        except Exception as e:
            return False, f"JSON导出失败: {str(e)}"

    def _export_to_csv(self, records, timestamp):
        """导出到CSV"""
        try:
            data = []
            for record in records:
                record_data = json.loads(record['data'])
                data.append({
                    '时间': record['timestamp'],
                    '平台': record['platform'],
                    '商品标题': record_data.get('title', ''),
                    '价格': record_data.get('price', ''),
                    '规格': '; '.join(record_data.get('specs', [])),
                    '商品链接': record['url']
                })
            
            df = pd.DataFrame(data)
            file_path = os.path.join(self.export_dir, f'export_{timestamp}.csv')
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            return True, file_path
            
        except Exception as e:
            return False, f"CSV导出失败: {str(e)}"

    def generate_report(self, start_date=None, end_date=None):
        """生成分析报告"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        stats = self.analyze_crawl_stats()
        
        report = f"""# 爬取数据分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
统计周期: {start_date} 至 {end_date}

## 总体统计
"""
        
        # 添加平台统计
        for platform, data in stats['platform_stats'].items():
            report += f"""
### {platform}平台
- 总爬取数: {data['total']}
- 成功数: {data['success']}
- 失败数: {data['failed']}
- 成功率: {data['success_rate']}%
"""
        
        return report 