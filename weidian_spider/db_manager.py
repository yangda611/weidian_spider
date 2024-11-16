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
        
        # 媒体文件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            file_type TEXT NOT NULL,  -- 'image' or 'video'
            file_path TEXT NOT NULL,
            original_url TEXT NOT NULL,
            download_time TEXT NOT NULL,
            FOREIGN KEY (record_id) REFERENCES records(id)
        )
        ''')
        
        self.conn.commit()
        
    def save_record(self, record):
        """保存爬取记录"""
        try:
            cursor = self.conn.cursor()
            
            # 确保数据是JSON字符串
            data = record['data']
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            
            cursor.execute('''
            INSERT INTO records (url, platform, data, timestamp, status)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                record['url'],
                record['platform'],
                data,  # 已序列化的数据
                record['timestamp'],
                'success'
            ))
            
            # 更新统计信息
            self.update_statistics(record['platform'], True)
            
            self.conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            print(f"Database error: {str(e)}")
            return None
            
    def get_all_records(self):
        """获取所有记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, url, platform, data, timestamp, template_name, status, error_message 
            FROM records 
            ORDER BY timestamp DESC
            ''')
            
            columns = ['id', 'url', 'platform', 'data', 'timestamp', 
                      'template_name', 'status', 'error_message']
            records = []
            
            for row in cursor.fetchall():
                try:
                    record = dict(zip(columns, row))
                    
                    # 尝试解析JSON数据
                    if record['data']:
                        try:
                            record['data'] = json.loads(record['data'])
                        except json.JSONDecodeError:
                            record['data'] = {'error': '数据格式错误'}
                    else:
                        record['data'] = {}
                        
                    records.append(record)
                    
                except Exception as e:
                    print(f"Error processing record: {str(e)}")
                    continue
                    
            return records
            
        except Exception as e:
            print(f"Error getting records: {str(e)}")
            return []
        
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
        
    def save_media_file(self, record_id, file_type, file_path, original_url):
        """保存媒体文件记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO media_files (record_id, file_type, file_path, original_url, download_time)
            VALUES (?, ?, ?, ?, ?)
            ''', (record_id, file_type, file_path, original_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving media file: {str(e)}")
            return False 

    def delete_record(self, record_id):
        """删除记录"""
        try:
            cursor = self.conn.cursor()
            
            # 删除相关的媒体文件记录
            cursor.execute('DELETE FROM media_files WHERE record_id = ?', (record_id,))
            
            # 删除主记录
            cursor.execute('DELETE FROM records WHERE id = ?', (record_id,))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error deleting record: {str(e)}")
            return False 