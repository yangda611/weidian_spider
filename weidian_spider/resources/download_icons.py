import os
import requests
from PIL import Image
from io import BytesIO

def get_project_root():
    """获取项目根目录"""
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current))

# 创建图标目录
icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
if not os.path.exists(icons_dir):
    os.makedirs(icons_dir)
    print(f"Created icons directory: {icons_dir}")

print(f"Icons will be saved to: {icons_dir}")

# 图标配置
ICONS = {
    'logo': {
        'url': 'https://img.icons8.com/color/96/shopping-cart--v1.png',
        'size': 32
    },
    'add': {
        'url': 'https://img.icons8.com/material-outlined/96/add.png',
        'size': 24
    },
    'delete': {
        'url': 'https://img.icons8.com/material-outlined/96/delete.png',
        'size': 24
    },
    'view': {
        'url': 'https://img.icons8.com/material-outlined/96/view-details.png',
        'size': 24
    },
    'export': {
        'url': 'https://img.icons8.com/material-outlined/96/export.png',
        'size': 24
    }
}

def download_and_resize_icon(name, url, size):
    try:
        print(f"Downloading {name} icon...")
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        
        # 调整大小
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # 保存
        output_path = os.path.join(icons_dir, f'{name}.png')
        img.save(output_path, 'PNG')
        print(f"Saved: {output_path}")
        
    except Exception as e:
        print(f"Error downloading {name}: {str(e)}")

def main():
    for name, config in ICONS.items():
        download_and_resize_icon(name, config['url'], config['size'])
    print("Done!")

if __name__ == "__main__":
    main() 