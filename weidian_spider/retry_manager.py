import time
from datetime import datetime

class RetryManager:
    """重试管理器"""
    def __init__(self, max_retries=3, delay=2):
        self.max_retries = max_retries
        self.delay = delay
        self.retry_count = {}
        self.failed_tasks = []

    def should_retry(self, task_id):
        """判断是否应该重试"""
        current_retries = self.retry_count.get(task_id, 0)
        return current_retries < self.max_retries

    def add_retry(self, task_id):
        """添加重试次数"""
        self.retry_count[task_id] = self.retry_count.get(task_id, 0) + 1
        time.sleep(self.delay)  # 延迟一段时间后重试

    def add_failed_task(self, task_id, error):
        """添加失败任务"""
        self.failed_tasks.append({
            'task_id': task_id,
            'error': str(error),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'retries': self.retry_count.get(task_id, 0)
        })

    def get_failed_tasks(self):
        """获取失败任务列表"""
        return self.failed_tasks

    def clear(self):
        """清理重试记录"""
        self.retry_count.clear()
        self.failed_tasks.clear() 