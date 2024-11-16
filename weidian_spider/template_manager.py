import os
import json
from datetime import datetime

class TemplateManager:
    def __init__(self, resource_dir):
        self.template_dir = os.path.join(resource_dir, 'templates')
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)

    def get_templates(self, platform=None):
        """获取所有模板"""
        templates = {}
        try:
            for file_name in os.listdir(self.template_dir):
                if file_name.endswith('.json'):
                    with open(os.path.join(self.template_dir, file_name), 'r', encoding='utf-8') as f:
                        template = json.load(f)
                        if platform is None or template.get('platform') == platform:
                            templates[template['name']] = template
            return templates
        except Exception as e:
            print(f"Error getting templates: {str(e)}")
            return {}

    def save_template(self, name, selectors, description=""):
        """保存模板"""
        try:
            template_data = {
                'name': name,
                'selectors': selectors,
                'description': description,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_used': None,
                'use_count': 0,
                'platform': 'weidian'  # 默认平台
            }
            
            file_path = os.path.join(self.template_dir, f"{name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving template: {str(e)}")
            return False

    def load_template(self, name):
        """加载模板"""
        try:
            file_path = os.path.join(self.template_dir, f"{name}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                # 更新使用时间和次数
                template['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                template['use_count'] += 1
                self.save_template(
                    template['name'],
                    template['selectors'],
                    template['description']
                )
                return template
            return None
        except Exception as e:
            print(f"Error loading template: {str(e)}")
            return None

    def delete_template(self, name):
        """删除模板"""
        try:
            file_path = os.path.join(self.template_dir, f"{name}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting template: {str(e)}")
            return False 