import json
import os
from datetime import datetime

class TemplateManager:
    """模板管理器"""
    def __init__(self):
        self.template_dir = 'templates'
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
        self.template_file = os.path.join(self.template_dir, 'crawl_templates.json')
        
    def save_template(self, name, selectors, description=""):
        """保存模板"""
        try:
            templates = self.load_templates()
            templates[name] = {
                'selectors': selectors,
                'description': description,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_used': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving template: {str(e)}")
            return False
            
    def load_templates(self):
        """加载所有模板"""
        try:
            if os.path.exists(self.template_file):
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading templates: {str(e)}")
            return {}
            
    def get_template(self, name):
        """获取指定模板"""
        templates = self.load_templates()
        return templates.get(name)
        
    def update_last_used(self, name):
        """更新模板最后使用时间"""
        templates = self.load_templates()
        if name in templates:
            templates[name]['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
                
    def delete_template(self, name):
        """删除模板"""
        templates = self.load_templates()
        if name in templates:
            del templates[name]
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
            return True
        return False 