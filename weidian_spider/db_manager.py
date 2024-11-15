import sqlite3
import json
import os
from datetime import datetime

class DatabaseManager:
    """数据库管理类"""
    def __init__(self):
        """初始化数据库连接"""
        # 确保数据目录存在
        self.db_dir = 'data'
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
            
        self.db_path = os.path.join(self.db_dir, 'spider_data.db')
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()
        
    def create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        # 爬取记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            template_name TEXT,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
        ''')
        
        # 爬取统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_crawls INTEGER DEFAULT 0,
            successful_crawls INTEGER DEFAULT 0,
            failed_crawls INTEGER DEFAULT 0,
            platform TEXT NOT NULL
        )
        ''')
        
        self.conn.commit()
        
    def save_record(self, record):
        """保存爬取记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO records (url, platform, data, timestamp, template_name, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                record['url'],
                record['platform'],
                json.dumps(record['data'], ensure_ascii=False),
                record['timestamp'],
                record.get('template_name'),
                'success'
            ))
            
            # 更新统计信息
            self.update_statistics(record['platform'], True)
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Database error: {str(e)}")
            return False
            
    def get_all_records(self):
        """获取所有记录"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id, url, platform, data, timestamp, template_name, status, error_message 
        FROM records 
        ORDER BY timestamp DESC
        ''')
        
        columns = ['id', 'url', 'platform', 'data', 'timestamp', 
                  'template_name', 'status', 'error_message']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    def get_records_by_ids(self, record_ids):
        """根据ID获取记录"""
        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(record_ids))
        cursor.execute(f'''
        SELECT id, url, platform, data, timestamp, template_name, status, error_message 
        FROM records 
        WHERE id IN ({placeholders})
        ORDER BY timestamp DESC
        ''', record_ids)
        
        columns = ['id', 'url', 'platform', 'data', 'timestamp', 
                  'template_name', 'status', 'error_message']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    def update_statistics(self, platform, success=True):
        """更新爬取统计信息"""
        try:
            cursor = self.conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 检查今天的统计记录是否存在
            cursor.execute('''
            SELECT id FROM statistics 
            WHERE date = ? AND platform = ?
            ''', (today, platform))
            
            result = cursor.fetchone()
            if result:
                # 更新现有记录
                if success:
                    cursor.execute('''
                    UPDATE statistics 
                    SET total_crawls = total_crawls + 1,
                        successful_crawls = successful_crawls + 1
                    WHERE date = ? AND platform = ?
                    ''', (today, platform))
                else:
                    cursor.execute('''
                    UPDATE statistics 
                    SET total_crawls = total_crawls + 1,
                        failed_crawls = failed_crawls + 1
                    WHERE date = ? AND platform = ?
                    ''', (today, platform))
            else:
                # 创建新记录
                cursor.execute('''
                INSERT INTO statistics (date, platform, total_crawls, successful_crawls, failed_crawls)
                VALUES (?, ?, 1, ?, ?)
                ''', (today, platform, 1 if success else 0, 0 if success else 1))
                
            self.conn.commit()
        except Exception as e:
            print(f"Error updating statistics: {str(e)}")
            
    def get_statistics(self, days=7):
        """获取统计信息"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT date, platform, total_crawls, successful_crawls, failed_crawls 
        FROM statistics 
        ORDER BY date DESC 
        LIMIT ?
        ''', (days,))
        
        columns = ['date', 'platform', 'total', 'success', 'failed']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close() 