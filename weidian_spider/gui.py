from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
                           QTabWidget, QLabel, QComboBox, QMessageBox, QFileDialog,
                           QListWidget, QListWidgetItem, QDialog, QScrollArea, QLineEdit,
                           QHeaderView, QProgressDialog, QApplication, QGroupBox,
                           QDateEdit, QRadioButton, QCheckBox, QSpinBox, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QDate, QTimer, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QColor, QAction
from PyQt6.QtCharts import QChartView, QChart, QLineSeries, QValueAxis, QBarSeries, QBarSet, QBarCategoryAxis

import sys
import os
from datetime import datetime
from io import StringIO
import json
import requests
import logging
import time

from weidian_spider.db_manager import DatabaseManager
from weidian_spider.template_manager import TemplateManager
from weidian_spider.data_analyzer import DataAnalyzer
from weidian_spider.retry_manager import RetryManager
import traceback

# 确保资源目录存在
RESOURCE_DIR = os.path.join(os.path.dirname(__file__), 'resources')
ICONS_DIR = os.path.join(RESOURCE_DIR, 'icons')

if not os.path.exists(RESOURCE_DIR):
    os.makedirs(RESOURCE_DIR)
if not os.path.exists(ICONS_DIR):
    os.makedirs(ICONS_DIR)

def get_icon_path(icon_name):
    """获取图标路径"""
    return os.path.join(ICONS_DIR, f"{icon_name}.png")

class LogRedirector(StringIO):
    """日志重定向器"""
    def __init__(self, window):
        super().__init__()
        self.window = window
        
    def write(self, text):
        if text.strip():
            if "error" in text.lower() or "exception" in text.lower():
                self.window.log_message("ERROR", text.strip())
            elif "warning" in text.lower():
                self.window.log_message("WARNING", text.strip())
            else:
                self.window.log_message("INFO", text.strip())
                
    def flush(self):
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.is_loaded = False
            self.setWindowTitle('微店商品爬取工具')
            self.setGeometry(100, 100, 1200, 800)
            
            # 加载配置
            self.config = self.load_config()
            
            # 初始化组件
            self.db = DatabaseManager()
            self.template_manager = TemplateManager(RESOURCE_DIR)  # 传入资源目录
            self.data_analyzer = DataAnalyzer(self.db)
            self.retry_manager = RetryManager()
            
            self.log_entries = []
            self.crawler_threads = []
            self.start_button = None
            self.stop_button = None
            self.current_selectors = {}
            
            # 初始化UI
            self.init_ui()
            self.setup_logging()
            
            # 应用配置
            self.apply_config()
            
            # 设置已加载标志
            self.is_loaded = True
            
            self.thread_status = {}
            self.total_threads = 0
            self.completed_threads = 0
            
        except Exception as e:
            logging.error("MainWindow initialization failed", exc_info=True)
            raise

    def load_config(self):
        """加载配置"""
        try:
            config_path = os.path.join(RESOURCE_DIR, 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.get_default_config()
        except Exception as e:
            self.log_message("ERROR", f"加载配失败: {str(e)}")
            return self.get_default_config()

    def get_default_config(self):
        """获取默认配置"""
        return {
            'crawler': {
                'max_retries': 3,
                'retry_delay': 2,
                'timeout': 30,
                'batch_size': 5,
                'download_media': True,
                'media_types': ['image', 'video'],
                'save_path': os.path.join(RESOURCE_DIR, 'downloads')
            },
            'ui': {
                'theme': 'default',
                'font_size': 12,
                'window_size': [1200, 800],
                'auto_save': True,
                'save_interval': 300
            },
            'network': {
                'use_proxy': False,
                'proxy_list': [],
                'timeout': 30,
                'retry_codes': [500, 502, 503, 504]
            },
            'database': {
                'auto_backup': True,
                'backup_interval': 86400,
                'max_backups': 7
            }
        }

    def save_config(self):
        """保存配置"""
        try:
            config_path = os.path.join(RESOURCE_DIR, 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.log_message("INFO", "配置已保存")
        except Exception as e:
            self.log_message("ERROR", f"保存配置失败: {str(e)}")

    def apply_config(self):
        """应用配置"""
        try:
            # 应用爬虫配置
            if hasattr(self, 'retry_manager'):
                self.retry_manager.max_retries = self.config['crawler']['max_retries']
                self.retry_manager.retry_delay = self.config['crawler']['retry_delay']

            # 应用UI配置
            if 'ui' in self.config:
                font_size = self.config['ui']['font_size']
                self.setStyleSheet(f"""
                    QWidget {{
                        font-size: {font_size}px;
                    }}
                """)
                
                if hasattr(self, 'log_text'):
                    self.log_text.setStyleSheet(f"""
                        QTextEdit {{
                            background-color: #1e1e1e;
                            color: #ffffff;
                            font-family: Consolas, Monaco, monospace;
                            font-size: {font_size}px;
                            padding: 10px;
                            border: none;
                        }}
                    """)

            # 应用网络配置
            if 'network' in self.config:
                if self.config['network']['use_proxy']:
                    # 设置代理
                    pass

            # 应用数据库配置
            if 'database' in self.config and hasattr(self, 'db'):
                if self.config['database']['auto_backup']:
                    self.setup_auto_backup()

        except Exception as e:
            self.log_message("ERROR", f"应用配置失败: {str(e)}")

    def setup_auto_backup(self):
        """设置自动备份"""
        try:
            if self.config['database']['auto_backup']:
                backup_interval = self.config['database']['backup_interval']
                self.backup_timer = QTimer(self)
                self.backup_timer.timeout.connect(self.auto_backup_database)
                self.backup_timer.start(backup_interval * 1000)  # 转换为毫秒
        except Exception as e:
            self.log_message("ERROR", f"设置自动备份失败: {str(e)}")

    def auto_backup_database(self):
        """自动备份数据库"""
        try:
            backup_dir = os.path.join(RESOURCE_DIR, 'backups')
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')
            
            self.db.backup_database(backup_path)
            self.log_message("INFO", f"数据库已自动备份到: {backup_path}")
            
            # 清理旧备份
            self.cleanup_old_backups()
        except Exception as e:
            self.log_message("ERROR", f"自动备份失败: {str(e)}")

    def cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backup_dir = os.path.join(RESOURCE_DIR, 'backups')
            max_backups = self.config['database']['max_backups']
            
            backups = sorted([
                os.path.join(backup_dir, f) 
                for f in os.listdir(backup_dir) 
                if f.startswith('backup_') and f.endswith('.db')
            ])
            
            while len(backups) > max_backups:
                oldest = backups.pop(0)
                os.remove(oldest)
                self.log_message("INFO", f"已删除旧备份: {oldest}")
        except Exception as e:
            self.log_message("ERROR", f"清旧备份失败: {str(e)}")

    def init_ui(self):
        """初始化用户界面"""
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # 创建菜单栏
            self.create_menu_bar()
            
            # 创建工具栏
            self.create_toolbar()
            
            # 创建标签页
            self.tabs = QTabWidget()
            layout.addWidget(self.tabs)
            
            # 爬取页面
            crawl_tab = self.create_crawl_tab()
            self.tabs.addTab(crawl_tab, "爬取")
            
            # 历史记录页面
            history_tab = self.create_history_tab()
            self.tabs.addTab(history_tab, "历史记录")
            
            # 日志页面
            log_tab = self.create_log_tab()
            self.tabs.addTab(log_tab, "系统日志")
            
            # 状态栏
            self.statusBar().showMessage('就绪')
            
            # 移除这行，因为它会覆盖其他设置
            # self.disable_crawl_controls(True)
            
        except Exception as e:
            logging.error("UI initialization failed", exc_info=True)
            raise

    def show_about(self):
        """显示关于对话框"""
        try:
            about_text = """
            <h2>微店商品爬取工具</h2>
            <p>版本: 1.0.0</p>
            <p>一用于爬取微店商品信息的具，支持：</p>
            <ul>
                <li>自定义选择爬取内容</li>
                <li>批量爬取商品信息</li>
                <li>数据导出功能</li>
                <li>失败重试机制</li>
            </ul>
            <p>使用说明请参考"帮助"菜单。</p>
            """
            
            QMessageBox.about(self, "关于", about_text)
            
        except Exception as e:
            self.log_message("ERROR", f"显示关于对话框失败: {str(e)}")

    def setup_logging(self):
        """设置日志系统"""
        try:
            # 创建日志目录
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # 设置日志文件
            log_file = os.path.join(log_dir, f'spider_{datetime.now().strftime("%Y%m%d")}.log')
            
            # 配置日志处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            console_handler = logging.StreamHandler(sys.stdout)
            
            # 设置日志格式
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 配置根日志记录器
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
            
            # 重定向标准输出到日志窗口
            sys.stdout = LogRedirector(self)
            sys.stderr = LogRedirector(self)
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise

    def log_message(self, level, message):
        """记录日志消息"""
        try:
            entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': level,
                'message': message
            }
            self.log_entries.append(entry)
            
            # 根据日志级别设置颜色
            color = self.get_log_color(level)
            formatted_message = f'<span style="color: {color}">[{entry["timestamp"]}] [{level}] {message}</span>'
            
            # 直接添加到日志显示区域
            if hasattr(self, 'log_text'):
                self.log_text.append(formatted_message)
                
                # 滚动到底部
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
            # 更新状态栏
            if level == "ERROR":
                self.statusBar().showMessage(f"错误: {message}")
            
        except Exception as e:
            print(f"Error logging message: {str(e)}")

    def get_log_color(self, level):
        """获取日志级别"""
        colors = {
            "INFO": "#00FF00",    # 绿色
            "WARNING": "#FFA500",  # 橙色
            "ERROR": "#FF0000"     # 红色
        }
        return colors.get(level, "#FFFFFF")  # 默认白色

    def update_log_filter(self):
        """更新日志过滤器"""
        try:
            if not hasattr(self, 'log_text'):
                return
                
            self.log_text.clear()
            filter_type = self.log_filter_combo.currentText()
            search_text = self.log_search.text().lower()
            
            for entry in self.log_entries:
                # 检查日志类型
                if filter_type == "全部日志" or (
                    filter_type == "正常信息" and entry['level'] == "INFO" or
                    filter_type == "警告信息" and entry['level'] == "WARNING" or
                    filter_type == "错误信息" and entry['level'] == "ERROR"
                ):
                    # 检查搜索文本
                    if not search_text or search_text in entry['message'].lower():
                        color = self.get_log_color(entry['level'])
                        formatted_message = f'<span style="color: {color}">[{entry["timestamp"]}] [{entry["level"]}] {entry["message"]}</span>'
                        self.log_text.append(formatted_message)
            
            # 滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print(f"Error updating log filter: {str(e)}")

    def clear_logs(self):
        """清空日志"""
        try:
            reply = QMessageBox.question(
                self,
                '确认清空',
                '确定要清空所有日志吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log_entries.clear()
                if hasattr(self, 'log_text'):
                    self.log_text.clear()
                self.log_message("INFO", "日志已清空")
                
        except Exception as e:
            print(f"Error clearing logs: {str(e)}")

    def create_log_tab(self):
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 日志过滤控件
        filter_group = QGroupBox("日志过滤")
        filter_layout = QHBoxLayout()
        
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["全部日志", "正常信息", "警告信息", "错误信息"])
        self.log_filter_combo.currentTextChanged.connect(self.update_log_filter)
        
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("搜索日志...")
        self.log_search.textChanged.connect(self.update_log_filter)
        
        filter_layout.addWidget(QLabel("日志类型:"))
        filter_layout.addWidget(self.log_filter_combo)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.log_search)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
                padding: 10px;
                border: none;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 钮组
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("导出日志")
        export_btn.clicked.connect(self.export_logs)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
        
        return tab

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = QAction('导入链接', self)
        import_action.setShortcut('Ctrl+I')
        import_action.setStatusTip('从文件导入链接')
        import_action.triggered.connect(self.import_urls)
        file_menu.addAction(import_action)
        
        export_action = QAction('导出数', self)
        export_action.setShortcut('Ctrl+E')
        export_action.setStatusTip('导出爬取的数据')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('退出程序')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        retry_action = QAction('失败任务', self)
        retry_action.setStatusTip('查看失败的任务')
        retry_action.triggered.connect(self.show_failed_tasks)
        tools_menu.addAction(retry_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.setStatusTip('关于本程序')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def import_urls(self):
        """从文件导入URL"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "选择文件",
                "",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_name:
                with open(file_name, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                    
                valid_count = 0
                for url in urls:
                    if self.is_valid_url(url) and not self.check_url_duplicates(url):
                        self.url_list.addItem(url)
                        valid_count += 1
                
                if valid_count > 0:
                    self.log_message("INFO", f"成功导入 {valid_count} 个有效链接")
                    self.start_button.setEnabled(True)
                else:
                    self.log_message("WARNING", "没有找到有效的链接")
                    QMessageBox.warning(self, "警告", "文件中没有有效的链接！")
                    
        except Exception as e:
            self.log_message("ERROR", f"导入链接失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def is_valid_url(self, url):
        """验证URL是否有效"""
        try:
            url = url.lower().strip()
            return 'weidian.com' in url or 'youshop10.com' in url
        except:
            return False

    def check_url_duplicates(self, url):
        """检查URL是否重复"""
        try:
            for i in range(self.url_list.count()):
                if self.url_list.item(i).text() == url:
                    return True
            return False
        except Exception as e:
            self.log_message("ERROR", f"检查URL重复失败: {str(e)}")
            return False

    def export_data(self):
        """导出数据"""
        try:
            # 检查是有据导
            records = self.db.get_all_records()
            if not records:
                QMessageBox.warning(self, "警告", "没有可导出的数据！")
                return

            # 选择导出格式
            format_dialog = QDialog(self)
            format_dialog.setWindowTitle("选择导出格")
            layout = QVBoxLayout(format_dialog)

            format_group = QGroupBox("导出格式")
            format_layout = QVBoxLayout()
            
            excel_radio = QRadioButton("Excel格式 (.xlsx)")
            excel_radio.setChecked(True)
            csv_radio = QRadioButton("CSV格式 (.csv)")
            json_radio = QRadioButton("JSON格式 (.json)")
            markdown_radio = QRadioButton("Markdown格式 (.md)")
            
            format_layout.addWidget(excel_radio)
            format_layout.addWidget(csv_radio)
            format_layout.addWidget(json_radio)
            format_layout.addWidget(markdown_radio)
            format_group.setLayout(format_layout)
            layout.addWidget(format_group)

            # 选择导出内容
            content_group = QGroupBox("导出内容")
            content_layout = QVBoxLayout()
            
            all_radio = QRadioButton("导出所有记录")
            all_radio.setChecked(True)
            selected_radio = QRadioButton("仅导出选中记录")
            
            content_layout.addWidget(all_radio)
            content_layout.addWidget(selected_radio)
            content_group.setLayout(content_layout)
            layout.addWidget(content_group)

            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(format_dialog.accept)
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(format_dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            if format_dialog.exec() == QDialog.DialogCode.Accepted:
                # 确定导出格式
                if excel_radio.isChecked():
                    file_filter = "Excel Files (*.xlsx)"
                    suffix = ".xlsx"
                elif csv_radio.isChecked():
                    file_filter = "CSV Files (*.csv)"
                    suffix = ".csv"
                elif json_radio.isChecked():
                    file_filter = "JSON Files (*.json)"
                    suffix = ".json"
                else:
                    file_filter = "Markdown Files (*.md)"
                    suffix = ".md"

                # 选择保存位置
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "导出数据",
                    f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}",
                    file_filter
                )

                if file_name:
                    # 获取要导出的记录
                    if selected_radio.isChecked():
                        selected_rows = set(item.row() for item in self.history_table.selectedItems())
                        if not selected_rows:
                            QMessageBox.warning(self, "警告", "请先选择要导出的记录！")
                            return
                        export_records = [records[row] for row in selected_rows]
                    else:
                        export_records = records

                    # 执行导出
                    success, message = self.data_analyzer.export_batch_data(
                        export_records,
                        format=suffix[1:]  # 移除点号
                    )

                    if success:
                        self.log_message("INFO", f"据已导出到: {file_name}")
                        QMessageBox.information(self, "成功", "数据导出成功！")
                    else:
                        self.log_message("ERROR", f"导出失败: {message}")
                        QMessageBox.warning(self, "错误", f"导出失败: {message}")

        except Exception as e:
            self.log_message("ERROR", f"导出数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def create_history_tab(self):
        """创建历史记录标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["时间", "平台", "标题", "价格", "操作"])
        
        # 设置表格列宽
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.history_table.setColumnWidth(0, 150)
        self.history_table.setColumnWidth(1, 80)
        self.history_table.setColumnWidth(3, 80)
        self.history_table.setColumnWidth(4, 100)
        
        layout.addWidget(self.history_table)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_history)
        export_btn = QPushButton("导出选中")
        export_btn.clicked.connect(self.export_selected)
        
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
        
        # 加载历史记录
        self.refresh_history()
        
        return tab

    def refresh_history(self):
        """刷新历史记录"""
        try:
            records = self.db.get_all_records()
            self.history_table.setRowCount(len(records))
            
            for i, record in enumerate(records):
                try:
                    # 获取数据并确保是字典格式
                    data = record['data']
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except json.JSONDecodeError:
                            self.log_message("WARNING", f"记录 {i+1} 的数据格式错误，跳过显示")
                            continue
                    
                    if not isinstance(data, dict):
                        self.log_message("WARNING", f"记录 {i+1} 的数据类型错误，跳过显示")
                        continue
                    
                    # 设置表格内容
                    self.history_table.setItem(i, 0, QTableWidgetItem(record['timestamp']))
                    self.history_table.setItem(i, 1, QTableWidgetItem(record['platform']))
                    
                    # 获取标题和价格
                    title = "未知标题"
                    price = "未知价格"
                    
                    # 遍历所有键值对查找标题和价格
                    for key, value in data.items():
                        if not value:  # 跳过空值
                            continue
                            
                        key = str(key).lower()
                        if any(word in key for word in ['title', '标题', '名称']):
                            if isinstance(value, list):
                                title = value[0] if value else "未知标题"
                            else:
                                title = str(value)
                        elif any(word in key for word in ['price', '价格']):
                            if isinstance(value, list):
                                price = value[0] if value else "未知价格"
                            else:
                                price = str(value)
                    
                    self.history_table.setItem(i, 2, QTableWidgetItem(str(title)))
                    self.history_table.setItem(i, 3, QTableWidgetItem(f"¥{price}"))
                    
                    # 操作按钮
                    btn_widget = QWidget()
                    btn_layout = QHBoxLayout(btn_widget)
                    btn_layout.setContentsMargins(2, 2, 2, 2)
                    
                    view_btn = QPushButton("查看")
                    view_btn.clicked.connect(lambda checked, r=record: self.view_details(r))
                    btn_layout.addWidget(view_btn)
                    
                    delete_btn = QPushButton("删除")
                    delete_btn.clicked.connect(lambda checked, r=record: self.delete_record(r))
                    btn_layout.addWidget(delete_btn)
                    
                    self.history_table.setCellWidget(i, 4, btn_widget)
                    
                except Exception as e:
                    self.log_message("ERROR", f"处理记录 {i+1} 失败: {str(e)}")
                    continue  # 跳过错误的记录，继续处理下一个
                    
            self.log_message("INFO", "历史记录已刷新")
            
        except Exception as e:
            self.log_message("ERROR", f"刷新历史记录失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"刷新失败: {str(e)}")

    def delete_record(self, record):
        """删除记录"""
        try:
            reply = QMessageBox.question(
                self,
                '确认删除',
                '确定要删除这条记录吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.db.delete_record(record['id']):
                    self.log_message("INFO", "记录已删除")
                    self.refresh_history()
                else:
                    raise Exception("删除失败")
                    
        except Exception as e:
            self.log_message("ERROR", f"删除记录失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def show_template_manager(self):
        """显示模板管理器"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("模板管理")
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout(dialog)

            # 模板列表
            template_table = QTableWidget()
            template_table.setColumnCount(5)
            template_table.setHorizontalHeaderLabels(["模板名称", "创建时间", "最后使用", "描述", "操作"])
            
            # 设置表格样式
            header = template_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            
            template_table.setColumnWidth(0, 120)
            template_table.setColumnWidth(1, 150)
            template_table.setColumnWidth(2, 150)
            template_table.setColumnWidth(4, 100)
            
            # 加载模板数据
            templates = self.template_manager.load_templates()
            template_table.setRowCount(len(templates))
            
            for i, (name, data) in enumerate(templates.items()):
                template_table.setItem(i, 0, QTableWidgetItem(name))
                template_table.setItem(i, 1, QTableWidgetItem(data.get('created_at', '')))
                template_table.setItem(i, 2, QTableWidgetItem(data.get('last_used', '')))
                template_table.setItem(i, 3, QTableWidgetItem(data.get('description', '')))
                
                # 操作按钮
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, n=name: self.edit_template(n))
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, n=name: self.delete_template(n))
                
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(delete_btn)
                template_table.setCellWidget(i, 4, btn_widget)
            
            layout.addWidget(template_table)

            # 按钮组
            btn_layout = QHBoxLayout()
            
            new_btn = QPushButton("新建模板")
            new_btn.clicked.connect(self.create_new_template)
            btn_layout.addWidget(new_btn)
            
            import_btn = QPushButton("导入模板")
            import_btn.clicked.connect(self.import_template)
            btn_layout.addWidget(import_btn)
            
            export_btn = QPushButton("导出模板")
            export_btn.clicked.connect(lambda: self.export_template(template_table))
            btn_layout.addWidget(export_btn)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示模板管理器失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法打开模板管理器: {str(e)}")

    def create_new_template(self):
        """创建新模板"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("新建模板")
            dialog.setMinimumWidth(400)
            layout = QVBoxLayout(dialog)
            
            # 模板名称
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("模板名称:"))
            name_input = QLineEdit()
            name_layout.addWidget(name_input)
            layout.addLayout(name_layout)
            
            # 模板描述
            desc_layout = QHBoxLayout()
            desc_layout.addWidget(QLabel("模板描述:"))
            desc_input = QTextEdit()
            desc_input.setMaximumHeight(100)
            desc_layout.addWidget(desc_input)
            layout.addLayout(desc_layout)
            
            # 选择要爬取的内容
            content_group = QGroupBox("爬取内容")
            content_layout = QVBoxLayout()
            
            checkboxes = {}
            for item in ["商品标题", "商品价格", "商规格", "商品主图", "详情图片"]:
                cb = QCheckBox(item)
                checkboxes[item] = cb
                content_layout.addWidget(cb)
            
            content_group.setLayout(content_layout)
            layout.addWidget(content_group)
            
            # 按
            btn_layout = QHBoxLayout()
            save_btn = QPushButton("保存")
            save_btn.clicked.connect(lambda: self.save_template(
                dialog, name_input.text(), desc_input.toPlainText(), 
                {k: v.isChecked() for k, v in checkboxes.items()}
            ))
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(save_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"创建模板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"创建模板失败: {str(e)}")

    def save_template(self, dialog, name, description, selections):
        """保存模板"""
        try:
            if not name:
                QMessageBox.warning(dialog, "警告", "请输入模板名称！")
                return
                
            if not any(selections.values()):
                QMessageBox.warning(dialog, "警告", "请至少选择一项爬取内容！")
                return
                
            # 保存模板
            self.template_manager.save_template(name, selections, description)
            self.log_message("INFO", f"模板 '{name}' 已保存")
            dialog.accept()
            
        except Exception as e:
            self.log_message("ERROR", f"保存模失败: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"保存失败: {str(e)}")

    def edit_template(self, template_name):
        """编辑模板"""
        try:
            template_data = self.template_manager.get_template(template_name)
            if not template_data:
                QMessageBox.warning(self, "警告", f"模板 '{template_name}' 不存在！")
                return
                
            # 显示编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"编辑模板 - {template_name}")
            dialog.setMinimumWidth(400)
            layout = QVBoxLayout(dialog)
            
            # 模板描述
            desc_layout = QHBoxLayout()
            desc_layout.addWidget(QLabel("模板描述:"))
            desc_input = QTextEdit()
            desc_input.setPlainText(template_data.get('description', ''))
            desc_input.setMaximumHeight(100)
            desc_layout.addWidget(desc_input)
            layout.addLayout(desc_layout)
            
            # 选择要爬取的内容
            content_group = QGroupBox("爬取内容")
            content_layout = QVBoxLayout()
            
            checkboxes = {}
            selections = template_data.get('selectors', {})
            for item in ["商品标题", "商品价格", "商品规格", "商品主图", "详情图片"]:
                cb = QCheckBox(item)
                cb.setChecked(selections.get(item, False))
                checkboxes[item] = cb
                content_layout.addWidget(cb)
            
            content_group.setLayout(content_layout)
            layout.addWidget(content_group)
            
            # 按钮
            btn_layout = QHBoxLayout()
            save_btn = QPushButton("保存")
            save_btn.clicked.connect(lambda: self.update_template(
                dialog, template_name, desc_input.toPlainText(), 
                {k: v.isChecked() for k, v in checkboxes.items()}
            ))
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(save_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"编辑板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"编辑失败: {str(e)}")

    def update_template(self, dialog, name, description, selections):
        """更新模板"""
        try:
            if not any(selections.values()):
                QMessageBox.warning(dialog, "警告", "请至少选择一项爬取内容！")
                return
                
            # 更新模板
            self.template_manager.save_template(name, selections, description)
            self.log_message("INFO", f"模板 '{name}' 已更新")
            dialog.accept()
            
        except Exception as e:
            self.log_message("ERROR", f"更新模板失败: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"更新失败: {str(e)}")

    def delete_template(self, template_name):
        """删除模板"""
        try:
            reply = QMessageBox.question(
                self,
                '确认删除',
                f'确定要删除模板 "{template_name}" 吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.template_manager.delete_template(template_name)
                self.log_message("INFO", f"模板 '{template_name}' 已删除")
                
        except Exception as e:
            self.log_message("ERROR", f"删除模板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def show_failed_tasks(self):
        """显示失败任务列表"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("失败任务管理")
            dialog.setMinimumSize(800, 500)
            
            layout = QVBoxLayout(dialog)
            
            # 失败任务表格
            task_table = QTableWidget()
            task_table.setColumnCount(5)
            task_table.setHorizontalHeaderLabels(["URL", "错误信息", "失败时间", "重试次数", "操作"])
            
            # 设置表格列宽
            header = task_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            
            task_table.setColumnWidth(2, 150)
            task_table.setColumnWidth(3, 80)
            task_table.setColumnWidth(4, 100)
            
            # 加载失败任务
            failed_tasks = self.retry_manager.get_failed_tasks()
            task_table.setRowCount(len(failed_tasks))
            
            for i, task in enumerate(failed_tasks):
                task_table.setItem(i, 0, QTableWidgetItem(task['url']))
                task_table.setItem(i, 1, QTableWidgetItem(task['error']))
                task_table.setItem(i, 2, QTableWidgetItem(task['time']))
                task_table.setItem(i, 3, QTableWidgetItem(str(task['retries'])))
                
                # 操作按钮
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                retry_btn = QPushButton("重试")
                retry_btn.setEnabled(task['retries'] < 3)
                retry_btn.clicked.connect(lambda checked, url=task['url']: self.retry_task(url))
                btn_layout.addWidget(retry_btn)
                
                task_table.setCellWidget(i, 4, btn_widget)
            
            layout.addWidget(task_table)
            
            # 按组
            btn_layout = QHBoxLayout()
            
            retry_all_btn = QPushButton("全部重试")
            retry_all_btn.clicked.connect(lambda: self.retry_all_tasks(task_table))
            btn_layout.addWidget(retry_all_btn)
            
            clear_btn = QPushButton("清空列表")
            clear_btn.clicked.connect(lambda: self.clear_failed_tasks(task_table))
            btn_layout.addWidget(clear_btn)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示失败任务列表失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示失败任务: {str(e)}")

    def retry_task(self, task_id):
        """重试单个失败任务"""
        try:
            if self.retry_manager.should_retry(task_id):
                self.log_message("INFO", f"正在重试任: {task_id}")
                
                # 创建的爬虫线程
                thread = CrawlerThread(task_id, "微店", self.current_selectors)
                thread.progress.connect(self.handle_progress)
                thread.result.connect(self.handle_crawler_result)
                thread.finished.connect(self.handle_crawler_finished)
                thread.error.connect(self.handle_crawler_error)
                
                self.crawler_threads.append(thread)
                thread.start()
            else:
                QMessageBox.warning(self, "警告", "该任务已达到最大重试次数！")
                
        except Exception as e:
            self.log_message("ERROR", f"重试任务失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"重试失败: {str(e)}")

    def retry_all_tasks(self, table):
        """重试所有可重试的失败任务"""
        try:
            retry_count = 0
            for i in range(table.rowCount()):
                task_id = table.item(i, 0).text()
                if self.retry_manager.should_retry(task_id):
                    self.retry_task(task_id)
                    retry_count += 1
                    
            if retry_count > 0:
                self.log_message("INFO", f"已重试 {retry_count} 个任务")
            else:
                QMessageBox.information(self, "提示", "没有可重试的任")
                
        except Exception as e:
            self.log_message("ERROR", f"批重试任务失: {str(e)}")
            QMessageBox.critical(self, "错误", f"重试失败: {str(e)}")

    def remove_failed_task(self, task_id):
        """移除失败任务"""
        try:
            reply = QMessageBox.question(
                self,
                '确认移除',
                f'确定要移除任务 "{task_id}" 吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.retry_manager.remove_task(task_id)
                self.log_message("INFO", f"已移除任务: {task_id}")
                
        except Exception as e:
            self.log_message("ERROR", f"移除任务失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"移除失败: {str(e)}")

    def clear_failed_tasks(self, table):
        """清空失败任务列表"""
        try:
            if table.rowCount() == 0:
                return
                
            reply = QMessageBox.question(
                self,
                '认清空',
                '确定要清空所有失败任务吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.retry_manager.clear()
                table.setRowCount(0)
                self.log_message("INFO", "已清空失败任务列表")
                
        except Exception as e:
            self.log_message("ERROR", f"清空失败任务列表失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"清空失败: {str(e)}")

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar('工具栏')
        toolbar.setMovable(False)
        
        # 添加链接按钮
        add_action = QAction('添加链接', self)
        add_action.setIcon(QIcon(get_icon_path('add')))
        add_action.setStatusTip('添加新的商品链接')
        add_action.triggered.connect(self.add_url)
        toolbar.addAction(add_action)
        
        # 导入链接按钮
        import_action = QAction('导入链接', self)
        import_action.setIcon(QIcon(get_icon_path('import')))
        import_action.setStatusTip('从文件导入链接')
        import_action.triggered.connect(self.import_urls)
        toolbar.addAction(import_action)
        
        toolbar.addSeparator()
        
        # 开始爬取按钮
        start_btn = QPushButton('开始爬取')
        start_btn.setIcon(QIcon(get_icon_path('start')))
        start_btn.setStatusTip('���始爬取商品信息')
        start_btn.clicked.connect(self.start_crawling)
        start_btn.setEnabled(False)  # 默认禁用
        self.start_button = start_btn
        toolbar.addWidget(start_btn)
        
        # 停止取按钮
        stop_btn = QPushButton('停止爬取')
        stop_btn.setIcon(QIcon(get_icon_path('stop')))
        stop_btn.setStatusTip('停止爬取')
        stop_btn.clicked.connect(self.stop_crawling)
        stop_btn.setEnabled(False)  # 默认禁用
        self.stop_button = stop_btn
        toolbar.addWidget(stop_btn)
        
        return toolbar

    def check_start_button_state(self):
        """检查并更新开始按钮状态"""
        try:
            if hasattr(self, 'start_button') and hasattr(self, 'url_list'):
                # 只有当URL列表不为空时才启用开始按钮
                self.start_button.setEnabled(self.url_list.count() > 0)
        except Exception as e:
            logging.error(f"Error checking start button state: {str(e)}")

    def start_crawling(self):
        """开始爬取"""
        try:
            if self.url_list.count() == 0:
                QMessageBox.warning(self, "警告", "请先添加商品链接！")
                return
                
            # 显示元素选择器对话框
            selector_dialog = ElementSelectorDialog(self)
            if selector_dialog.exec() != QDialog.DialogCode.Accepted:
                return
                
            selected_elements = selector_dialog.selected_elements
            
            if not selected_elements or not selected_elements.get('selectors'):
                QMessageBox.warning(self, "警告", "请选择要爬取的元素！")
                return
                
            # 禁用爬取页面的控件
            self.disable_crawl_controls(True)
            
            # 切换到日志标签页
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "系统日志":
                    self.tabs.setCurrentIndex(i)
                    break
            
            # 清空之前的线程
            self.clean_threads()
            
            # 获取总URL数量
            total_urls = self.url_list.count()
            self.log_message("INFO", f"开始爬取 {total_urls} 个商品...")
            
            # 保存当前选择器
            self.current_selectors = selected_elements
            
            # 创建并启动爬虫线程
            for i in range(total_urls):
                item = self.url_list.item(i)
                url = item.text()
                
                thread = CrawlerThread(url, "微店", selected_elements)
                thread.progress.connect(self.handle_progress)
                thread.result.connect(self.handle_crawler_result)
                thread.finished.connect(lambda success, t=total_urls: 
                    self.handle_crawler_finished(success, t))
                thread.error.connect(self.handle_crawler_error)
                thread.status_changed.connect(lambda status, u=url: 
                    self.handle_status_changed(u, status))
                thread.retry_count_changed.connect(lambda count, u=url: 
                    self.handle_retry_count_changed(u, count))
                
                self.crawler_threads.append(thread)
                thread.start()
                
                # 添加延迟，避免同时打开太多浏览器
                time.sleep(1)
            
            # 更新状态栏
            self.update_status(f"正在爬取 {total_urls} 个商品...")
                
        except Exception as e:
            self.log_message("ERROR", f"爬取过程出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"爬取失败: {str(e)}")
            self.disable_crawl_controls(False)

    def handle_status_changed(self, url, status):
        """处理线程状态变化"""
        try:
            if url in self.thread_status:
                self.thread_status[url]['status'] = status
                self.update_progress_display()
        except Exception as e:
            self.log_message("ERROR", f"更新状态失败: {str(e)}")

    def handle_retry_count_changed(self, url, count):
        """处理重试次数变化"""
        try:
            if url in self.thread_status:
                self.thread_status[url]['retries'] = count
                self.update_progress_display()
        except Exception as e:
            self.log_message("ERROR", f"更新重试次数失败: {str(e)}")

    def update_progress_display(self):
        """更新进度显示"""
        try:
            status_counts = {
                'success': 0,
                'failed': 0,
                'running': 0,
                'retrying': 0
            }
            
            for status in self.thread_status.values():
                if status['status'] in status_counts:
                    status_counts[status['status']] += 1
            
            status_text = (
                f"成功: {status_counts['success']} | "
                f"失败: {status_counts['failed']} | "
                f"运行中: {status_counts['running']} | "
                f"重试中: {status_counts['retrying']}"
            )
            
            self.update_status(status_text)
            
        except Exception as e:
            self.log_message("ERROR", f"更新进度显示失败: {str(e)}")

    def disable_crawl_controls(self, disabled=True):
        """禁用/启用爬取页面的控件"""
        try:
            # 禁用/启用URL输入和按钮
            self.url_input.setEnabled(not disabled)
            self.url_list.setEnabled(not disabled)
            
            # 遍历爬取页面的所有按钮
            crawl_tab = self.tabs.widget(0)  # 假设爬取页面是第一个标签页
            for button in crawl_tab.findChildren(QPushButton):
                button.setEnabled(not disabled)
            
            # 更新开始/停止按钮状态
            if hasattr(self, 'start_button'):
                self.start_button.setEnabled(not disabled)
            if hasattr(self, 'stop_button'):
                self.stop_button.setEnabled(disabled)
                
            # 如果禁用，添加半透明遮罩
            if disabled:
                crawl_tab.setStyleSheet("QWidget { opacity: 0.7; }")
            else:
                crawl_tab.setStyleSheet("")
                
        except Exception as e:
            self.log_message("ERROR", f"更新控件状态失败: {str(e)}")

    def handle_crawler_finished(self, success, total_urls):
        """处理爬虫完成"""
        try:
            active_threads = [t for t in self.crawler_threads if t.isRunning()]
            completed = total_urls - len(active_threads)
            
            # 更新状态栏
            self.update_status(f"已完成: {completed}/{total_urls}")
            
            # 如果所有线程都完成了
            if not active_threads:
                self.log_message("INFO", "所有任务已完成")
                self.disable_crawl_controls(False)
                self.update_status("爬取完成")
                
        except Exception as e:
            self.log_message("ERROR", f"处理爬虫完成事件失败: {str(e)}")

    def stop_crawling(self):
        """停止爬取"""
        try:
            reply = QMessageBox.question(
                self,
                '确认停止',
                '确定要停止爬取吗？正在进行的任务将被中断。',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message("INFO", "正在停止爬取...")
                for thread in self.crawler_threads:
                    thread.stop()
                self.clean_threads()
                self.disable_crawl_controls(False)
                self.update_status("爬取已停止")
                
        except Exception as e:
            self.log_message("ERROR", f"停止爬取失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止失败: {str(e)}")

    def clean_threads(self):
        """清理线程"""
        try:
            for thread in self.crawler_threads:
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()
            self.crawler_threads.clear()
            self.log_message("INFO", "线程已清理")
        except Exception as e:
            self.log_message("ERROR", f"清理线程失败: {str(e)}")

    def add_url(self):
        """添加单个URL"""
        try:
            url = self.url_input.toPlainText().strip()
            if not url:
                QMessageBox.warning(self, "警告", "请输入商品链接！")
                return
                
            if not self.is_valid_url(url):
                QMessageBox.warning(self, "警告", "请输入有效的微店商品链接！")
                return
                
            if self.check_url_duplicates(url):
                QMessageBox.warning(self, "警告", "该链接已存在！")
                return
                
            self.url_list.addItem(url)
            self.url_input.clear()
            self.log_message("INFO", f"已添加链接: {url}")
            
            # 更新开始按钮状态
            self.check_start_button_state()
            
        except Exception as e:
            self.log_message("ERROR", f"添加链接失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def is_valid_url(self, url):
        """验证URL是否有效"""
        try:
            url = url.lower().strip()
            return 'weidian.com' in url or 'youshop10.com' in url
        except:
            return False

    def check_url_duplicates(self, url):
        """检查URL是否重复"""
        try:
            for i in range(self.url_list.count()):
                if self.url_list.item(i).text() == url:
                    return True
            return False
        except Exception as e:
            self.log_message("ERROR", f"检查URL重复失败: {str(e)}")
            return False

    def create_crawl_tab(self):
        """创建爬取标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # URL输入区域
        input_group = QGroupBox("添加链接")
        input_layout = QVBoxLayout()
        
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("请输入商品链接，支持批量输入（每行一个）或拖拽导入...")
        self.url_input.setMaximumHeight(100)
        input_layout.addWidget(self.url_input)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_url)
        clear_input_btn = QPushButton("空输入")
        clear_input_btn.clicked.connect(self.url_input.clear)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_input_btn)
        input_layout.addLayout(btn_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # URL列表
        list_group = QGroupBox("链接列")
        list_layout = QVBoxLayout()
        
        self.url_list = QListWidget()
        self.url_list.setAcceptDrops(True)
        list_layout.addWidget(self.url_list)
        
        # 列表操作按钮
        list_btn_layout = QHBoxLayout()
        clear_list_btn = QPushButton("清空列表")
        clear_list_btn.clicked.connect(self.clear_url_list)
        remove_selected_btn = QPushButton("删除选中")
        remove_selected_btn.clicked.connect(self.remove_selected_urls)
        list_btn_layout.addWidget(clear_list_btn)
        list_btn_layout.addWidget(remove_selected_btn)
        list_layout.addLayout(list_btn_layout)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        return tab

    def list_drag_enter_event(self, event):
        """列表拖拽进事件"""
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def list_drop_event(self, event):
        """列表放置事件"""
        try:
            text = event.mimeData().text()
            urls = text.strip().split('\n')
            
            added_count = 0
            for url in urls:
                url = url.strip()
                if self.is_valid_url(url):
                    # 检查重复
                    is_duplicate = False
                    for i in range(self.url_list.count()):
                        if self.url_list.item(i).text() == url:
                            is_duplicate = True
                            break
                            
                    if not is_duplicate:
                        self.url_list.addItem(url)
                        added_count += 1
                        
            if added_count > 0:
                self.log_message("INFO", f"通过拖放添加了 {added_count} 个链接")
            else:
                self.log_message("WARNING", "没有添加任何有效链接")
                
            event.accept()
            
        except Exception as e:
            self.log_message("ERROR", f"处理拖放事件失败: {str(e)}")
            event.ignore()

    def clear_url_list(self):
        """清空URL列表"""
        try:
            if self.url_list.count() == 0:
                return
                
            reply = QMessageBox.question(
                self,
                '确认清空',
                '确定要清空所有链接吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.url_list.clear()
                self.log_message("INFO", "已清空链接列表")
                # 更新开始按钮状态
                self.check_start_button_state()
                
        except Exception as e:
            self.log_message("ERROR", f"清空链接列表失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"清空失败: {str(e)}")

    def remove_selected_urls(self):
        """删除选中的URL"""
        try:
            selected_items = self.url_list.selectedItems()
            if not selected_items:
                return
                
            reply = QMessageBox.question(
                self,
                '确认删除',
                f'确定要删除选中的 {len(selected_items)} 个链接吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                for item in selected_items:
                    self.url_list.takeItem(self.url_list.row(item))
                self.log_message("INFO", f"已删 {len(selected_items)} 个链接")
                
                # 更新开始按钮状态
                self.check_start_button_state()
                
        except Exception as e:
            self.log_message("ERROR", f"删除链接失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def export_selected(self):
        """导出选中的记录"""
        try:
            selected_items = self.history_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选要导出的记录")
                return

            # 选择导出格式
            format_dialog = QDialog(self)
            format_dialog.setWindowTitle("选择导出格式")
            layout = QVBoxLayout(format_dialog)

            format_group = QGroupBox("导出格式")
            format_layout = QVBoxLayout()
            
            excel_radio = QRadioButton("Excel格式 (.xlsx)")
            excel_radio.setChecked(True)
            csv_radio = QRadioButton("CSV格式 (.csv)")
            json_radio = QRadioButton("JSON格式 (.json)")
            markdown_radio = QRadioButton("Markdown格式 (.md)")
            
            format_layout.addWidget(excel_radio)
            format_layout.addWidget(csv_radio)
            format_layout.addWidget(json_radio)
            format_layout.addWidget(markdown_radio)
            format_group.setLayout(format_layout)
            layout.addWidget(format_group)

            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(format_dialog.accept)
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(format_dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            if format_dialog.exec() == QDialog.DialogCode.Accepted:
                # 确定导出格式
                if excel_radio.isChecked():
                    file_filter = "Excel Files (*.xlsx)"
                    suffix = ".xlsx"
                elif csv_radio.isChecked():
                    file_filter = "CSV Files (*.csv)"
                    suffix = ".csv"
                elif json_radio.isChecked():
                    file_filter = "JSON Files (*.json)"
                    suffix = ".json"
                else:
                    file_filter = "Markdown Files (*.md)"
                    suffix = ".md"

                # 选择保存位置
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "导出数据",
                    f"export_selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}",
                    file_filter
                )

                if file_name:
                    # 获取选中的记录
                    selected_rows = set(item.row() for item in selected_items)
                    records = [self.db.get_all_records()[row] for row in selected_rows]

                    # 执行导出
                    success, message = self.data_analyzer.export_batch_data(
                        records,
                        format=suffix[1:]  # 移除点号
                    )

                    if success:
                        self.log_message("INFO", f"选中数据已导出到: {file_name}")
                        QMessageBox.information(self, "成功", "数据导出成功！")
                    else:
                        self.log_message("ERROR", f"导出失败: {message}")
                        QMessageBox.warning(self, "错误", f"导出失败: {message}")

        except Exception as e:
            self.log_message("ERROR", f"导出选中数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导失败: {str(e)}")

    def import_template(self):
        """导入模板"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "导入模板",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_name:
                with open(file_name, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    
                # 验证模板数据
                if self.validate_template(template_data):
                    self.template_manager.save_template(
                        template_data['name'],
                        template_data['selectors'],
                        template_data.get('description', '')
                    )
                    self.log_message("INFO", f"模板 '{template_data['name']}' 已导入")
                    QMessageBox.information(self, "成功", "模板导成功！")
                else:
                    QMessageBox.warning(self, "错误", "无效的模板文件！")
                    
        except Exception as e:
            self.log_message("ERROR", f"导入模板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def export_template(self, template_table):
        """导出模板"""
        try:
            selected_items = template_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请选择要导出模板！")
                return
                
            template_name = selected_items[0].text()
            template_data = self.template_manager.get_template(template_name)
            
            if template_data:
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "导出模板",
                    f"{template_name}.json",
                    "JSON Files (*.json);;All Files (*)"
                )
                
                if file_name:
                    with open(file_name, 'w', encoding='utf-8') as f:
                        json.dump(template_data, f, ensure_ascii=False, indent=2)
                    self.log_message("INFO", f"模板已导出到: {file_name}")
                    QMessageBox.information(self, "成功", "模板导出成功！")
                    
        except Exception as e:
            self.log_message("ERROR", f"导出模板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def validate_template(self, data):
        """验证模板数据"""
        try:
            # 检查必需字段
            required_fields = ['name', 'selectors']
            if not all(field in data for field in required_fields):
                return False
                
            # 检查选择器格式
            selectors = data['selectors']
            if not isinstance(selectors, dict):
                return False
                
            # 检查选择器项
            valid_selectors = {
                "title", "price", "specs", 
                "main_images", "detail_images"
            }
            if not all(key in valid_selectors for key in selectors.keys()):
                return False
                
            # 检查值类型
            if not all(isinstance(value, bool) for value in selectors.values()):
                return False
                
            return True
            
        except Exception:
            return False

    def handle_template_import(self, template_data):
        """处理模板导入"""
        try:
            # 检查模板名称是否已存在
            existing_templates = self.template_manager.load_templates()
            if template_data['name'] in existing_templates:
                reply = QMessageBox.question(
                    self,
                    '模板已存在',
                    f'模板 "{template_data["name"]}" 已存在，是否覆？',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return False
                    
            # 保存模板
            self.template_manager.save_template(
                template_data['name'],
                template_data['selectors'],
                template_data.get('description', '')
            )
            
            return True
            
        except Exception as e:
            self.log_message("ERROR", f"处理模板导入失败: {str(e)}")
            return False

    def get_template_preview(self, template_data):
        """获取模板预览信息"""
        try:
            preview = f"模板名称: {template_data['name']}\n\n"
            
            if 'description' in template_data:
                preview += f"描述: {template_data['description']}\n\n"
                
            preview += "选择的内容:\n"
            for key, value in template_data['selectors'].items():
                if value:
                    preview += f"- {self.get_selector_name(key)}\n"
                    
            return preview
            
        except Exception:
            return "无法生成预览"

    def get_selector_name(self, selector_key):
        """获取选择器的显示名称"""
        names = {
            'title': '商品标题',
            'price': '商品价格',
            'specs': '商品规格',
            'main_images': '商品主图',
            'detail_images': '详情图片'
        }
        return names.get(selector_key, selector_key)

    def handle_progress(self, level, message):
        """处理进度信息"""
        self.log_message(level, message)
        self.update_status(message)

    def handle_crawler_result(self, result):
        """处理爬虫结果"""
        try:
            # 获取标题用于显示
            title = "未知标题"
            for key, value in result['data'].items():
                if 'title' in key.lower() and value:
                    title = value if isinstance(value, str) else value[0]
                    break
            
            # 保存到数据库
            record_id = self.db.save_record(result)
            
            if record_id:
                self.log_message("INFO", f"数据已保存: {title}")
                # 更新历史记录表格
                self.refresh_history()
            else:
                raise Exception("保存记录失败")
            
        except Exception as e:
            self.log_message("ERROR", f"保存数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def handle_crawler_error(self, url, error):
        """处理爬虫错误"""
        self.log_message("ERROR", f" {url} 失败: {error}")
        if self.retry_manager.should_retry(url):
            self.log_message("INFO", f"准备重试: {url}")
            self.retry_manager.add_retry(url)
            # 重新创建线程进行爬取
            thread = CrawlerThread(url, "微店", self.current_selectors)
            thread.progress.connect(self.handle_progress)
            thread.result.connect(self.handle_crawler_result)
            thread.finished.connect(self.handle_crawler_finished)
            thread.error.connect(self.handle_crawler_error)
            self.crawler_threads.append(thread)
            thread.start()
        else:
            self.retry_manager.add_failed_task(url, error)
            self.log_message("WARNING", f"{url} 达到最大重试次数")

    def view_details(self, record):
        """查看商品详情"""
        try:
            # 获取数据并确保是字典格式
            data = record['data']
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    raise Exception("数据格式错误")
            
            if not isinstance(data, dict):
                raise Exception("数据类型错误")
            
            dialog = QDialog(self)
            dialog.setWindowTitle("商品详情")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # 使用QTextEdit显示Markdown格式的详情
            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            
            # 构建Markdown格式的商品信息
            markdown_text = "# 商品详情\n\n"
            
            # 添加所有数据
            for key, value in data.items():
                if value:  # 跳过空值
                    markdown_text += f"\n## {key}\n"
                    if isinstance(value, list):
                        if key.lower().endswith(('images', 'imgs', 'pictures')):
                            # 图片显示
                            for i, img_url in enumerate(value, 1):
                                markdown_text += f"\n![图片{i}]({img_url})\n"
                        else:
                            # 列表显示
                            for item in value:
                                markdown_text += f"- {item}\n"
                    else:
                        # 单个值显示
                        markdown_text += f"{value}\n"
            
            # 添加基本信息
            markdown_text += f"\n## 其他信息\n"
            markdown_text += f"- **URL**: {record['url']}\n"
            markdown_text += f"- **平台**: {record['platform']}\n"
            markdown_text += f"- **爬取时间**: {record['timestamp']}\n"
            if record.get('status'):
                markdown_text += f"- **状态**: {record['status']}\n"
            
            detail_text.setMarkdown(markdown_text)
            layout.addWidget(detail_text)
            
            # 按钮组
            btn_layout = QHBoxLayout()
            
            # 导出按钮
            export_btn = QPushButton("导出详情")
            export_btn.clicked.connect(lambda: self.export_details(record))
            btn_layout.addWidget(export_btn)
            
            # 复制链接按钮
            copy_url_btn = QPushButton("复制链接")
            copy_url_btn.clicked.connect(lambda: self.copy_to_clipboard(record['url']))
            btn_layout.addWidget(copy_url_btn)
            
            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示详情: {str(e)}")

    def export_details(self, record):
        """导出详情"""
        try:
            # 获取数据并确保是字典格式
            data = record['data']
            if isinstance(data, str):
                data = json.loads(data)
            
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "导出详情",
                f"商品详情_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                "Markdown Files (*.md);;All Files (*)"
            )
            
            if file_name:
                # 构建Markdown内容
                markdown_text = f"# 商品详情\n\n"
                markdown_text += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                # 添加所有数据
                for key, value in data.items():
                    if value:
                        markdown_text += f"\n## {key}\n"
                        if isinstance(value, list):
                            if key.lower().endswith(('images', 'imgs', 'pictures')):
                                for i, img_url in enumerate(value, 1):
                                    markdown_text += f"\n![图片{i}]({img_url})\n"
                            else:
                                for item in value:
                                    markdown_text += f"- {item}\n"
                        else:
                            markdown_text += f"{value}\n"
                
                # 添加基本信息
                markdown_text += f"\n## 其他信息\n"
                markdown_text += f"- **URL**: {record['url']}\n"
                markdown_text += f"- **平台**: {record['platform']}\n"
                markdown_text += f"- **爬取时间**: {record['timestamp']}\n"
                
                # 保存文件
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(markdown_text)
                    
                self.log_message("INFO", f"详情已导出到: {file_name}")
                QMessageBox.information(self, "成功", "详情导出成功！")
                
        except Exception as e:
            self.log_message("ERROR", f"导出详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.log_message("INFO", "已复制到剪贴板")
        except Exception as e:
            self.log_message("ERROR", f"复制到剪贴板失败: {str(e)}")

    def show_full_image(self, img_url):
        """显示完整大图"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("图片预览")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            scroll = QScrollArea()
            image_label = QLabel()
            
            response = requests.get(img_url)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            # 保持宽高比例缩放
            screen_size = QApplication.primaryScreen().size()
            max_width = screen_size.width() * 0.8
            max_height = screen_size.height() * 0.8
            
            scaled_pixmap = pixmap.scaled(
                int(max_width), 
                int(max_height),
                Qt.AspectRatioMode.KeepAspectRatio
            )
            
            image_label.setPixmap(scaled_pixmap)
            scroll.setWidget(image_label)
            layout.addWidget(scroll)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示大图失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示图片: {str(e)}")

    def update_chart_sizes(self):
        """更图表大小"""
        try:
            if hasattr(self, 'success_chart_view') and hasattr(self, 'count_chart_view'):
                width = self.width() * 0.9
                height = self.height() * 0.35
                self.success_chart_view.setMinimumSize(width, height)
                self.count_chart_view.setMinimumSize(width, height)
        except Exception as e:
            self.log_message("ERROR", f"更新图表大小失败: {str(e)}")

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        try:
            super().resizeEvent(event)
            self.update_chart_sizes()
        except Exception as e:
            self.log_message("ERROR", f"处理窗口大小改变事件失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            reply = QMessageBox.question(
                self,
                '确认退出',
                '确定要退出程序吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message("INFO", "程序正在关闭...")
                
                # 停止所有爬虫线程
                self.stop_all_threads()
                
                # 关闭数据库连接
                if hasattr(self, 'db'):
                    self.db.close()
                
                # 清理临时文件
                self.cleanup_temp_files()
                
                # 保存配置
                if hasattr(self, 'config'):
                    self.save_config()
                
                # 等待所有线程完全停止
                self.wait_for_threads()
                
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            self.log_message("ERROR", f"程序关闭时出错: {str(e)}")
            event.accept()

    def stop_all_threads(self):
        """停止所有线程"""
        try:
            # 停止爬虫线程
            for thread in self.crawler_threads:
                if thread.isRunning():
                    thread.stop()
                    thread.wait(1000)  # 等待最多1秒
                    if thread.isRunning():
                        thread.terminate()  # 强制终止
            
            self.crawler_threads.clear()
            self.log_message("INFO", "所有爬虫线程已停止")
            
        except Exception as e:
            self.log_message("ERROR", f"停止线程失败: {str(e)}")

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            # 清理临时目录
            temp_dir = os.path.join(RESOURCE_DIR, 'temp')
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
            
            self.log_message("INFO", "临时文件已清理")
            
        except Exception as e:
            self.log_message("ERROR", f"清理临时文件失败: {str(e)}")

    def wait_for_threads(self):
        """等待所有线程完成"""
        try:
            # 等待最多3秒
            for _ in range(30):
                running_threads = [t for t in self.crawler_threads if t.isRunning()]
                if not running_threads:
                    break
                time.sleep(0.1)
                
            self.log_message("INFO", "所有线程已完成")
            
        except Exception as e:
            self.log_message("ERROR", f"等待线程完成失败: {str(e)}")

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """放置事件"""
        try:
            urls = []
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        # 如果是文件，读取文件内容
                        with open(url.toLocalFile(), 'r', encoding='utf-8') as f:
                            urls.extend(f.read().splitlines())
                    else:
                        urls.append(url.toString())
            elif event.mimeData().hasText():
                urls = event.mimeData().text().splitlines()
            
            # 添加有效的URL
            valid_count = 0
            for url in urls:
                url = url.strip()
                if self.is_valid_url(url):
                    self.url_list.addItem(url)
                    valid_count += 1
            
            if valid_count > 0:
                self.log_message("INFO", f"通过拖放添加了 {valid_count} 个链接")
                self.start_button.setEnabled(True)
            else:
                self.log_message("WARNING", "没有添加任何有效链接")
                
            event.accept()
            
        except Exception as e:
            self.log_message("ERROR", f"处理拖放事件失败: {str(e)}")
            event.ignore()

    def keyPressEvent(self, event):
        """键盘事件"""
        try:
            # Ctrl+V: 粘贴
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
                clipboard = QApplication.clipboard()
                text = clipboard.text()
                if text:
                    urls = text.splitlines()
                    valid_count = 0
                    for url in urls:
                        url = url.strip()
                        if self.is_valid_url(url):
                            self.url_list.addItem(url)
                            valid_count += 1
                    
                    if valid_count > 0:
                        self.log_message("INFO", f"通过粘贴添加了 {valid_count} 个链接")
                    else:
                        self.log_message("WARNING", "没有加任何有效链接")
            
            # Ctrl+S: 保存当前数据
            elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_S:
                self.export_data()
            
            # Ctrl+R: 刷新历史记录
            elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R:
                self.refresh_history()
            
            # Esc: 停止爬取
            elif event.key() == Qt.Key.Key_Escape:
                if self.stop_button.isEnabled():
                    self.stop_crawling()
                    
        except Exception as e:
            self.log_message("ERROR", f"处理键盘事件失败: {str(e)}")

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        try:
            menu = QMenu(self)
            
            # 添加链接
            add_action = menu.addAction("添加链接")
            add_action.triggered.connect(self.add_url)
            
            # 导入链接
            import_action = menu.addAction("导入链接")
            import_action.triggered.connect(self.import_urls)
            
            menu.addSeparator()
            
            # 开始爬取
            start_action = menu.addAction("开始爬取")
            start_action.triggered.connect(self.start_crawling)
            start_action.setEnabled(self.start_button.isEnabled())
            
            # 停止爬取
            stop_action = menu.addAction("停止爬取")
            stop_action.triggered.connect(self.stop_crawling)
            stop_action.setEnabled(self.stop_button.isEnabled())
            
            menu.addSeparator()
            
            # 导出数据
            export_action = menu.addAction("导出数据")
            export_action.triggered.connect(self.export_data)
            
            menu.exec(event.globalPos())
            
        except Exception as e:
            self.log_message("ERROR", f"显示右键菜单失败: {str(e)}")

    def show_help(self):
        """显示帮助信息"""
        try:
            help_text = """
            <h2>微店商品爬取工具使用说明</h2>
            
            <h3>基本操作</h3>
            <ul>
                <li>添加链接：
                    <ul>
                        <li>直接输入链接后点击"添加"</li>
                        <li>从文件导入多个链接</li>
                        <li>拖拽链接到程序窗口</li>
                        <li>复制链接后按Ctrl+V粘贴</li>
                    </ul>
                </li>
                <li>开始爬：
                    <ul>
                        <li>选择要爬取的内容</li>
                        <li>点击"开始爬取"按钮</li>
                        <li>可以随时点击"停止"按钮中断爬取</li>
                    </ul>
                </li>
                <li>查看结果：
                    <ul>
                        <li>在"历史记录"标签页查看爬取结果</li>
                        <li>点击"查看"按钮查看详细信息</li>
                        <li>可导出数据为多种格式</li>
                    </ul>
                </li>
            </ul>
            
            <h3>快捷键</h3>
            <ul>
                <li>Ctrl+V粘贴链接</li>
                <li>Ctrl+S：保存数据</li>
                <li>Ctrl+R：刷新历史记录</li>
                <li>Esc：停止爬取</li>
            </ul>
            
            <h3>其他功能</h3>
            <ul>
                <li>模板管理：保存常用的爬取设置</li>
                <li>失败重试：自动重试失败的任务</li>
                <li>数据计：查看爬取数据统计信息</li>
                <li>日志记录：记录所有操作和错误信息</li>
            </ul>
            """
            
            dialog = QDialog(self)
            dialog.setWindowTitle("使用说明")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            help_text_edit = QTextEdit()
            help_text_edit.setReadOnly(True)
            help_text_edit.setHtml(help_text)
            layout.addWidget(help_text_edit)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示帮助信息失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示帮助信息: {str(e)}")

    def update_status(self, message):
        """更新状态栏信息"""
        try:
            self.statusBar().showMessage(message)
        except Exception as e:
            print(f"Error updating status: {str(e)}")

    def update_window_title(self):
        """更新窗口标题"""
        try:
            count = self.url_list.count()
            title = f"微店商品爬取工具 - {count} 个链接"
            if self.crawler_threads:
                active_threads = len([t for t in self.crawler_threads if t.isRunning()])
                if active_threads > 0:
                    title += f" (正在爬取: {active_threads})"
            self.setWindowTitle(title)
        except Exception as e:
            self.log_message("ERROR", f"更新窗口标题失败: {str(e)}")

    def handle_url_input(self):
        """处理URL输入"""
        try:
            text = self.url_input.toPlainText()
            # 自动检测粘贴的多行文本
            if '\n' in text:
                urls = text.strip().split('\n')
                valid_count = 0
                for url in urls:
                    url = url.strip()
                    if self.is_valid_url(url) and not self.check_url_duplicates(url):
                        self.url_list.addItem(url)
                        valid_count += 1
                
                if valid_count > 0:
                    self.log_message("INFO", f"已添加 {valid_count} 个有效链接")
                self.url_input.clear()
                
        except Exception as e:
            self.log_message("ERROR", f"处理URL输入失败: {str(e)}")

    def save_window_state(self):
        """保存窗口状态"""
        try:
            settings = {
                'window_geometry': self.geometry().getRect(),
                'window_state': self.windowState(),
                'splitter_state': self.splitter.saveState().data() if hasattr(self, 'splitter') else None,
                'last_export_path': getattr(self, 'last_export_path', ''),
                'last_import_path': getattr(self, 'last_import_path', '')
            }
            
            with open('window_state.json', 'w') as f:
                json.dump(settings, f)
                
        except Exception as e:
            self.log_message("ERROR", f"保存窗口状态失败: {str(e)}")

    def load_window_state(self):
        """加载窗状态"""
        try:
            if os.path.exists('window_state.json'):
                with open('window_state.json', 'r') as f:
                    settings = json.load(f)
                    
                # 恢复窗口位置和大小
                if 'window_geometry' in settings:
                    self.setGeometry(*settings['window_geometry'])
                    
                # 恢复窗口状态
                if 'window_state' in settings:
                    self.setWindowState(settings['window_state'])
                    
                # 恢复分割器状态
                if hasattr(self, 'splitter') and settings.get('splitter_state'):
                    self.splitter.restoreState(settings['splitter_state'])
                    
                # 恢复路径
                if 'last_export_path' in settings:
                    self.last_export_path = settings['last_export_path']
                if 'last_import_path' in settings:
                    self.last_import_path = settings['last_import_path']
                    
        except Exception as e:
            self.log_message("ERROR", f"加载窗口状态失败: {str(e)}")

    def update_progress(self, current, total):
        """更新进度条"""
        try:
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.setValue(current)
                percentage = int(current / total * 100)
                self.progress_dialog.setLabelText(f"正在爬取... {percentage}%")
                
                if current >= total:
                    self.progress_dialog.close()
                    
        except Exception as e:
            self.log_message("ERROR", f"更新进度条失败: {str(e)}")

    def handle_network_error(self, error):
        """处理网络错误"""
        try:
            error_type = type(error).__name__
            error_msg = str(error)
            
            if "ConnectionError" in error_type:
                self.log_message("ERROR", "网络连接失败，检查网络置")
            elif "Timeout" in error_type:
                self.log_message("ERROR", "请求超时，请稍后重试")
            elif "HTTPError" in error_type:
                self.log_message("ERROR", f"HTTP错误: {error_msg}")
            else:
                self.log_message("ERROR", f"网络错误: {error_msg}")
                
        except Exception as e:
            self.log_message("ERROR", f"处理网络错误失败: {str(e)}")

    def check_updates(self):
        """检查更新"""
        try:
            version = "1.0.0"  # 当前版本
            self.log_message("INFO", f"当前版本: {version}")
            self.log_message("INFO", "正在检查更新...")
            
            # TODO: 实现实际的更新检查逻辑
            
        except Exception as e:
            self.log_message("ERROR", f"检查更新失败: {str(e)}")

    def show_settings_dialog(self):
        """显示设置对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("设置")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            
            # 代理设置
            proxy_group = QGroupBox("代理设置")
            proxy_layout = QVBoxLayout()
            
            proxy_check = QCheckBox("使用代理")
            proxy_check.setChecked(False)
            proxy_layout.addWidget(proxy_check)
            
            proxy_input = QLineEdit()
            proxy_input.setPlaceholderText("代理地址 (例如: http://127.0.0.1:8080)")
            proxy_input.setEnabled(False)
            proxy_layout.addWidget(proxy_input)
            
            proxy_group.setLayout(proxy_layout)
            layout.addWidget(proxy_group)
            
            # 保存设置
            save_group = QGroupBox("保存设置")
            save_layout = QVBoxLayout()
            
            auto_save = QCheckBox("自动保存结果")
            auto_save.setChecked(True)
            save_layout.addWidget(auto_save)
            
            save_path = QLineEdit()
            save_path.setPlaceholderText("保存路径")
            save_layout.addWidget(save_path)
            
            save_group.setLayout(save_layout)
            layout.addWidget(save_group)
            
            # 按钮
            btn_layout = QHBoxLayout()
            
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"显示设置对话框失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示设置: {str(e)}")

    def create_batch_task(self):
        """创建批量任务"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("创建批量任务")
            dialog.setMinimumWidth(500)
            
            layout = QVBoxLayout(dialog)
            
            # 任务设置
            task_group = QGroupBox("任务设置")
            task_layout = QVBoxLayout()
            
            # 时间间隔
            interval_layout = QHBoxLayout()
            interval_layout.addWidget(QLabel("爬取间隔:"))
            interval_spin = QSpinBox()
            interval_spin.setRange(1, 60)
            interval_spin.setValue(5)
            interval_layout.addWidget(interval_spin)
            interval_layout.addWidget(QLabel("秒"))
            task_layout.addLayout(interval_layout)
            
            # 重试次数
            retry_layout = QHBoxLayout()
            retry_layout.addWidget(QLabel("重试次数:"))
            retry_spin = QSpinBox()
            retry_spin.setRange(0, 5)
            retry_spin.setValue(3)
            retry_layout.addWidget(retry_spin)
            task_layout.addLayout(retry_layout)
            
            task_group.setLayout(task_layout)
            layout.addWidget(task_group)
            
            # 按钮
            btn_layout = QHBoxLayout()
            start_btn = QPushButton("开始")
            start_btn.clicked.connect(lambda: self.start_batch_task(
                interval_spin.value(),
                retry_spin.value(),
                dialog
            ))
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(start_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"创建批量任务失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"创建任务失败: {str(e)}")

    def start_batch_task(self, interval, max_retries, dialog):
        """开始批量任务"""
        try:
            if self.url_list.count() == 0:
                QMessageBox.warning(dialog, "警告", "先添加商品链接！")
                return
                
            # 保存设置
            self.retry_manager.max_retries = max_retries
            
            # 关闭设置对框
            dialog.accept()
            
            # 开始爬取
            self.start_crawling(interval=interval)
            
        except Exception as e:
            self.log_message("ERROR", f"启动批量任务失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动任务失败: {str(e)}")

    def analyze_data(self):
        """数据分析"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("数据分析")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # 创建图表
            chart_view = QChartView()
            chart = QChart()
            chart.setTitle("商品价格分布")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            
            # 获取数据
            records = self.db.get_all_records()
            prices = []
            for record in records:
                data = json.loads(record['data'])
                try:
                    price = float(data['price'])
                    prices.append(price)
                except:
                    continue
            
            # 创柱状图
            if prices:
                series = QBarSeries()
                
                # 计算价格区间
                min_price = min(prices)
                max_price = max(prices)
                interval = (max_price - min_price) / 10
                
                # 统计每个区间的数量
                ranges = []
                counts = []
                for i in range(10):
                    start = min_price + i * interval
                    end = start + interval
                    count = len([p for p in prices if start <= p < end])
                    ranges.append(f"{start:.0f}-{end:.0f}")
                    counts.append(count)
                
                # 添加数据
                bar_set = QBarSet("数量")
                bar_set.append(counts)
                series.append(bar_set)
                
                chart.addSeries(series)
                
                # 设置坐标轴
                axis_x = QBarCategoryAxis()
                axis_x.append(ranges)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                axis_y.setRange(0, max(counts) * 1.1)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
            
            chart_view.setChart(chart)
            layout.addWidget(chart_view)
            
            # 统计信息
            stats_group = QGroupBox("统计信息")
            stats_layout = QVBoxLayout()
            
            if prices:
                stats_text = f"""
                商品数量: {len(prices)}
                平均价格: ¥{sum(prices)/len(prices):.2f}
                最高价格: ¥{max(prices):.2f}
                最低价格: ¥{min(prices):.2f}
                价格区间: ¥{max_price-min_price:.2f}
                """
            else:
                stats_text = "暂无数据"
            
            stats_label = QLabel(stats_text)
            stats_layout.addWidget(stats_label)
            
            stats_group.setLayout(stats_layout)
            layout.addWidget(stats_group)
            
            # 按钮
            btn_layout = QHBoxLayout()
            
            export_btn = QPushButton("导出分析")
            export_btn.clicked.connect(lambda: self.export_analysis(prices))
            btn_layout.addWidget(export_btn)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            self.log_message("ERROR", f"数据分析失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"分析失败: {str(e)}")

    def export_analysis(self, prices):
        """导出分析结果"""
        try:
            if not prices:
                QMessageBox.warning(self, "警告", "没有可导出的数据！")
                return
                
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析",
                f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                "Markdown Files (*.md);;All Files (*)"
            )
            
            if file_name:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(f"""# 商品价格分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本统计
- 商品数量: {len(prices)}
- 平均价格: ¥{sum(prices)/len(prices):.2f}
- 最高价格: ¥{max(prices):.2f}
- 最低价格: ¥{min(prices):.2f}
- 价格区间: ¥{max(prices)-min(prices):.2f}

## 价格分布
""")
                    # 添加价格分布统计
                    interval = (max(prices) - min(prices)) / 10
                    for i in range(10):
                        start = min(prices) + i * interval
                        end = start + interval
                        count = len([p for p in prices if start <= p < end])
                        f.write(f"- ¥{start:.0f}-{end:.0f}: {count}个商品\n")
                
                self.log_message("INFO", f"分析结果已导出到: {file_name}")
                QMessageBox.information(self, "成功", "分析结果导出成功！")
                
        except Exception as e:
            self.log_message("ERROR", f"导出分析结果失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def export_logs(self):
        """导出日志"""
        try:
            if not self.log_entries:
                QMessageBox.warning(self, "警告", "没有可出的日志！")
                return

            # 选择保存格式和位置
            file_name, selected_filter = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "文本文件 (*.txt);;HTML文件 (*.html);;Markdown文件 (*.md)"
            )
            
            if not file_name:
                return
                
            # 根据选择的格式导出
            if selected_filter == "HTML文件 (*.html)":
                self.export_logs_html(file_name)
            elif selected_filter == "Markdown文 (*.md)":
                self.export_logs_markdown(file_name)
            else:
                self.export_logs_text(file_name)
                
            self.log_message("INFO", f"日志已导出到: {file_name}")
            QMessageBox.information(self, "成功", "日志导出成功！")
                
        except Exception as e:
            self.log_message("ERROR", f"导出日志失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def export_logs_text(self, file_name):
        """导出为本格式"""
        with open(file_name, 'w', encoding='utf-8') as f:
            for entry in self.log_entries:
                f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")

    def export_logs_html(self, file_name):
        """导出为HTML格式"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Consolas, Monaco, monospace;
                    background-color: #1e1e1e;
                    color: #ffffff;
                    padding: 20px;
                }
                .log-entry {
                    margin: 5px 0;
                    white-space: pre-wrap;
                }
                .INFO { color: #00FF00; }
                .WARNING { color: #FFA500; }
                .ERROR { color: #FF0000; }
            </style>
        </head>
        <body>
        <h1>爬日志</h1>
        <p>导出时间: {}</p>
        <div class="log-content">
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        for entry in self.log_entries:
            html_content += f'<div class="log-entry {entry["level"]}">[{entry["timestamp"]}] [{entry["level"]}] {entry["message"]}</div>\n'

        html_content += """
        </div>
        </body>
        </html>
        """

        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def export_logs_markdown(self, file_name):
        """导出为Markdown格式"""
        markdown_content = f"""# 爬虫日志
导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 日志内容

"""
        for entry in self.log_entries:
            level_mark = {
                "INFO": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌"
            }.get(entry['level'], "•")
            
            markdown_content += f"{level_mark} **[{entry['timestamp']}] [{entry['level']}]** {entry['message']}\n\n"

        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

    def get_log_summary(self):
        """获取志摘要"""
        total = len(self.log_entries)
        info_count = sum(1 for entry in self.log_entries if entry['level'] == "INFO")
        warning_count = sum(1 for entry in self.log_entries if entry['level'] == "WARNING")
        error_count = sum(1 for entry in self.log_entries if entry['level'] == "ERROR")
        
        return {
            'total': total,
            'info': info_count,
            'warning': warning_count,
            'error': error_count
        }

class ElementSelectorDialog(QDialog):
    """元素选择器对话框"""
    def __init__(self, parent=None, template_name=None):
        super().__init__(parent)
        self.selected_elements = {}
        self.template_name = template_name
        self.setWindowTitle("选择爬取内容")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        """初化界面"""
        layout = QVBoxLayout(self)

        # 模板选择
        template_group = QGroupBox("模板管理")
        template_layout = QHBoxLayout()
        
        self.template_combo = QComboBox()
        self.refresh_templates()
        template_layout.addWidget(QLabel("选择模板:"))
        template_layout.addWidget(self.template_combo)
        
        save_template_btn = QPushButton("保存为模板")
        save_template_btn.clicked.connect(self.save_as_template)
        template_layout.addWidget(save_template_btn)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        # 选择器列表
        selector_group = QGroupBox("已选择的内容")
        selector_layout = QVBoxLayout()
        
        self.selector_table = QTableWidget()
        self.selector_table.setColumnCount(4)
        self.selector_table.setHorizontalHeaderLabels(["名称", "选择器", "预览", "操作"])
        self.selector_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        selector_layout.addWidget(self.selector_table)
        
        # 添加选择器按钮
        add_btn_layout = QHBoxLayout()
        add_selector_btn = QPushButton("添加选择器")
        add_selector_btn.clicked.connect(self.add_selector)
        add_btn_layout.addWidget(add_selector_btn)
        selector_layout.addLayout(add_btn_layout)
        
        selector_group.setLayout(selector_layout)
        layout.addWidget(selector_group)

        # 爬取选项
        options_group = QGroupBox("爬取选项")
        options_layout = QVBoxLayout()
        
        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("爬取延迟:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 60)
        self.delay_spin.setValue(3)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addWidget(QLabel("秒"))
        options_layout.addLayout(delay_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 按钮组
        btn_layout = QHBoxLayout()
        
        start_btn = QPushButton("开始爬取")
        start_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # 如果指定了模板，加载它
        if self.template_name:
            self.load_template(self.template_name)

        # 连接模板选择信号
        self.template_combo.currentTextChanged.connect(self.on_template_selected)

    def refresh_templates(self):
        """刷新模板列表"""
        self.template_combo.clear()
        self.template_combo.addItem("不使用模板")
        templates = self.parent().template_manager.get_templates()
        for name in templates.keys():
            self.template_combo.addItem(name)

    def on_template_selected(self, template_name):
        """当选择模板时"""
        if template_name and template_name != "不使用模板":
            template = self.parent().template_manager.load_template(template_name)
            if template:
                self.load_template_data(template)

    def load_template_data(self, template):
        """加载模板数据"""
        try:
            # 清空现选择器
            self.selector_table.setRowCount(0)
            
            # 添加模板中的选择器
            for name, selector in template['selectors'].items():
                self.add_selector_to_table(name, selector)
                
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载模板失败: {str(e)}")

    def save_as_template(self):
        """保存为新模板"""
        try:
            name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:")
            if ok and name:
                description, ok = QInputDialog.getText(self, "模板描述", "请输入模板描述:")
                if ok:
                    selectors = self.get_current_selectors()
                    if self.parent().template_manager.save_template(name, selectors, description):
                        QMessageBox.information(self, "成功", "模板保存成功！")
                        self.refresh_templates()
                        self.template_combo.setCurrentText(name)
                    else:
                        QMessageBox.warning(self, "错误", "保存模板失败！")
                        
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存模板失败: {str(e)}")

    def get_current_selectors(self):
        """获取当前所有选择器"""
        selectors = {}
        for row in range(self.selector_table.rowCount()):
            name = self.selector_table.item(row, 0).text()
            selector = self.selector_table.item(row, 1).text()
            selectors[name] = selector
        return selectors

    def add_selector(self):
        """添加新的选择器"""
        try:
            # 创建选择器对话框
            selector_dialog = SelectorDialog(self)
            if selector_dialog.exec() == QDialog.DialogCode.Accepted:
                name = selector_dialog.name_input.text()
                selector = selector_dialog.selector_input.text()
                preview = selector_dialog.preview_text.toPlainText()
                
                # 添加到表格
                self.add_selector_to_table(name, selector, preview)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加选择器失败: {str(e)}")

    def add_selector_to_table(self, name, selector, preview=""):
        """添加选择器到表格"""
        try:
            row = self.selector_table.rowCount()
            self.selector_table.insertRow(row)
            
            # 添加名称
            self.selector_table.setItem(row, 0, QTableWidgetItem(name))
            # 添加选择器
            self.selector_table.setItem(row, 1, QTableWidgetItem(selector))
            # 添加预览
            self.selector_table.setItem(row, 2, QTableWidgetItem(preview))
            
            # 添加操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda: self.edit_selector(row))
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda: self.delete_selector(row))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            self.selector_table.setCellWidget(row, 3, btn_widget)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加选择器到表格失败: {str(e)}")

    def edit_selector(self, row):
        """编辑选择器"""
        try:
            name = self.selector_table.item(row, 0).text()
            selector = self.selector_table.item(row, 1).text()
            preview = self.selector_table.item(row, 2).text()
            
            selector_dialog = SelectorDialog(self)
            selector_dialog.name_input.setText(name)
            selector_dialog.selector_input.setText(selector)
            selector_dialog.preview_text.setText(preview)
            
            if selector_dialog.exec() == QDialog.DialogCode.Accepted:
                self.selector_table.item(row, 0).setText(selector_dialog.name_input.text())
                self.selector_table.item(row, 1).setText(selector_dialog.selector_input.text())
                self.selector_table.item(row, 2).setText(selector_dialog.preview_text.toPlainText())
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑选择器失败: {str(e)}")

    def delete_selector(self, row):
        """删除选择器"""
        try:
            reply = QMessageBox.question(
                self,
                '确认删除',
                '确定要删除这个选择器吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.selector_table.removeRow(row)
                
        except Exception as e:
            QMessageBox.critical(self, "错���", f"删除选择器失败: {str(e)}")

    def accept(self):
        """确认选择"""
        try:
            # 获取所有选择器
            selectors = {}
            for row in range(self.selector_table.rowCount()):
                name = self.selector_table.item(row, 0).text()
                selector = self.selector_table.item(row, 1).text()
                selectors[name] = selector
                
            if not selectors:
                QMessageBox.warning(self, "警告", "请至少添加一个选择器！")
                return
                
            self.selected_elements = {
                'selectors': selectors,
                'delay': self.delay_spin.value()
            }
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"确认选择失败: {str(e)}")

class SelectorDialog(QDialog):
    """选择器对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = ""
        self.selector = ""
        self.preview = ""
        self.browser = None
        self.setWindowTitle("添加选择器")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 名称输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_input = QLineEdit(self.name)
        self.name_input.setPlaceholderText("例如：商品标题、价格等")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 选择器输入
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("选择器:"))
        self.selector_input = QLineEdit(self.selector)
        self.selector_input.setPlaceholderText('点击"选择"按钮在网页上选择元素')
        self.selector_input.setReadOnly(True)
        selector_layout.addWidget(self.selector_input)
        
        # 批量选择选项
        self.batch_select = QCheckBox("选择所有同类元素")
        self.batch_select.setChecked(True)
        selector_layout.addWidget(self.batch_select)
        
        pick_btn = QPushButton("选择")
        pick_btn.clicked.connect(self.pick_element)
        selector_layout.addWidget(pick_btn)
        layout.addLayout(selector_layout)
        
        # 预览区域
        preview_group = QGroupBox("内容预览")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("选择元素后将显示预览内容")
        self.preview_text.setMaximumHeight(100)
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def pick_element(self):
        """选择网页元素"""
        try:
            # 获取主窗口
            main_window = self.parent()
            while main_window and not isinstance(main_window, MainWindow):
                main_window = main_window.parent()
                
            if not main_window or not hasattr(main_window, 'url_list') or main_window.url_list.count() == 0:
                QMessageBox.warning(self, "警告", "请先添加要爬取的URL！")
                return
                
            url = main_window.url_list.item(0).text()
            
            # 创建浏览器实例
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            
            # 配置Chrome选项
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_experimental_option('detach', True)
            
            # 创建Service对象
            service = Service()
            
            # 创建浏览器实例
            self.browser = webdriver.Chrome(service=service, options=options)
            
            # 打网页
            self.browser.get(url)
            
            # 注入选择器工具的JavaScript代码
            js_code = """
            // 创建样式
            var style = document.createElement('style');
            style.textContent = `
                .element-picker-hover { 
                    outline: 3px dashed #FF4444 !important;
                    outline-offset: 2px !important;
                    cursor: pointer !important;
                }
                .element-picker-selected { 
                    outline: 5px solid #44FF44 !important;
                    outline-offset: 3px !important;
                    background-color: rgba(0, 255, 0, 0.15) !important;
                    box-shadow: 0 0 10px rgba(0, 255, 0, 0.5) !important;
                }
                .element-picker-similar {
                    outline: 3px solid #4444FF !important;
                    outline-offset: 2px !important;
                    background-color: rgba(0, 0, 255, 0.1) !important;
                }
            `;
            document.head.appendChild(style);
            
            var isBatchSelect = arguments[0];  // 从Python传入是否批量选择
            var hoveredElement = null;
            var selectedElements = [];
            
            function handleMouseMove(e) {
                if (e.target.classList.contains('element-picker-selected')) {
                    return;  // 已选中的元素不显示悬停效果
                }
                
                if (hoveredElement && hoveredElement !== e.target) {
                    hoveredElement.classList.remove('element-picker-hover');
                    // 移除之前悬停元素的相似元素标记
                    if (isBatchSelect) {
                        var oldSelector = generateSelector(hoveredElement);
                        document.querySelectorAll(oldSelector).forEach(el => {
                            if (el !== hoveredElement && !el.classList.contains('element-picker-selected')) {
                                el.classList.remove('element-picker-similar');
                            }
                        });
                    }
                }
                
                hoveredElement = e.target;
                hoveredElement.classList.add('element-picker-hover');
                
                // 显示新悬停元素的相似元素
                if (isBatchSelect) {
                    var newSelector = generateSelector(hoveredElement);
                    document.querySelectorAll(newSelector).forEach(el => {
                        if (el !== hoveredElement && !el.classList.contains('element-picker-selected')) {
                            el.classList.add('element-picker-similar');
                        }
                    });
                }
                
                e.stopPropagation();
            }
            
            function handleMouseOut(e) {
                if (hoveredElement) {
                    hoveredElement.classList.remove('element-picker-hover');
                    // 移除相似元素标记
                    if (isBatchSelect) {
                        var selector = generateSelector(hoveredElement);
                        document.querySelectorAll(selector).forEach(el => {
                            if (el !== hoveredElement && !el.classList.contains('element-picker-selected')) {
                                el.classList.remove('element-picker-similar');
                            }
                        });
                    }
                }
            }
            
            function handleClick(e) {
                e.preventDefault();
                e.stopPropagation();
                
                var element = e.target;
                var selector = generateSelector(element);
                
                // 移除之前的选中状态
                selectedElements.forEach(el => {
                    el.classList.remove('element-picker-selected');
                });
                selectedElements = [];
                
                if (isBatchSelect) {
                    // 批量选择所有相似元素
                    var similarElements = document.querySelectorAll(selector);
                    selectedElements = Array.from(similarElements);
                    
                    // 标记所有选中的元素
                    similarElements.forEach(el => {
                        el.classList.remove('element-picker-similar');
                        el.classList.remove('element-picker-hover');
                        el.classList.add('element-picker-selected');
                    });
                } else {
                    // 单个选择
                    element.classList.remove('element-picker-hover');
                    element.classList.add('element-picker-selected');
                    selectedElements = [element];
                }
                
                // 返回结果
                window.selectedElement = {
                    selector: selector,
                    text: selectedElements.map(el => el.innerText.trim()).join('\\n'),
                    count: selectedElements.length
                };
            }
            
            // 添加事件监听
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseout', handleMouseOut);
            document.addEventListener('click', handleClick);
            
            // 生成选择器
            function generateSelector(element) {
                if (element.id) {
                    return '#' + element.id;
                }
                
                var selector = element.tagName.toLowerCase();
                var classes = Array.from(element.classList)
                    .filter(c => !c.startsWith('element-picker-'))
                    .map(c => '.' + c)
                    .join('');
                    
                if (classes) {
                    selector += classes;
                }
                
                // 添加属性选择器
                ['name', 'type', 'data-id'].forEach(attr => {
                    if (element.hasAttribute(attr)) {
                        selector += `[${attr}="${element.getAttribute(attr)}"]`;
                    }
                });
                
                return selector;
            }
            """
            
            # 执行JavaScript代码，传入批量选择状态
            self.browser.execute_script(js_code, self.batch_select.isChecked())
            
            # 显示提示
            if self.batch_select.isChecked():
                msg = "请点击任意元素，将自动选择所有相似元素。选择完成后关闭浏览器窗口。"
            else:
                msg = "请点击要爬取的元素，选择完成后关闭浏览器窗口。"
            QMessageBox.information(self, "提示", msg)
            
            # 等待选择结果
            while self.browser:
                try:
                    result = self.browser.execute_script("return window.selectedElement;")
                    if result:
                        self.selector_input.setText(result['selector'])
                        self.preview_text.setText(result['text'])
                        break
                except:
                    pass
                QApplication.processEvents()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择元素失败: {str(e)}")
        finally:
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
                self.browser = None

    def accept(self):
        """确认对话框"""
        try:
            name = self.name_input.text().strip()
            selector = self.selector_input.text().strip()
            
            if not name:
                QMessageBox.warning(self, "警告", "请输入选择器名称！")
                return
                
            if not selector:
                QMessageBox.warning(self, "警告", "请选择要爬取的元素！")
                return
                
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"确认选择失败: {str(e)}")

class CrawlerThread(QThread):
    progress = pyqtSignal(str, str)  # 类型, 消息
    result = pyqtSignal(dict)  # 爬取结果
    error = pyqtSignal(str, str)  # URL, 错误信息
    status_changed = pyqtSignal(str)  # 状态
    retry_count_changed = pyqtSignal(int)  # 重试次数
    finished = pyqtSignal(bool)  # 是否成功

    def __init__(self, url, platform, selected_elements, max_retries=3):
        super().__init__()
        self.url = url
        self.platform = platform
        self.selected_elements = selected_elements
        self.should_stop = False
        self.max_retries = max_retries
        self.current_retry = 0
        self.browser = None

    def run(self):
        """运行爬虫"""
        try:
            if self.should_stop:
                return
                
            self.status_changed.emit("running")
            self.progress.emit("INFO", f"开始爬取: {self.url}")
            
            # 创建浏览器实例
            if not self.browser:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                options = Options()
                options.add_argument('--start-maximized')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                service = Service()
                self.browser = webdriver.Chrome(service=service, options=options)
                self.browser.set_page_load_timeout(30)
            
            # 爬取数据
            try:
                # 打开页面
                self.browser.get(self.url)
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 获取数据
                result = {}
                for name, selector in self.selected_elements['selectors'].items():
                    try:
                        elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        if name.lower().endswith(('images', 'imgs', 'pictures')):
                            # 处理图片元素
                            image_urls = []
                            for element in elements:
                                if element.tag_name == 'img':
                                    src = element.get_attribute('src')
                                    if src:
                                        image_urls.append(src)
                                else:
                                    imgs = element.find_elements(By.TAG_NAME, 'img')
                                    for img in imgs:
                                        src = img.get_attribute('src')
                                        if src:
                                            image_urls.append(src)
                            result[name] = image_urls
                            
                            # 下载图片
                            if self.selected_elements.get('download_images', False):
                                self.download_images(name, image_urls)
                        else:
                            # 处理文本元素
                            texts = [elem.text.strip() for elem in elements if elem.text.strip()]
                            result[name] = texts[0] if len(texts) == 1 else texts if texts else None
                            
                    except Exception as e:
                        self.progress.emit("WARNING", f"获取元素 {name} 失败: {str(e)}")
                        result[name] = None
                
                if not any(result.values()):
                    raise Exception("未获取到任何数据")
                
                # 确保至少有一个有效值
                if not any(v for v in result.values() if v is not None):
                    raise Exception("所有元素都为空")
                
                # 构建完整数据
                data = {
                    'url': self.url,
                    'platform': self.platform,
                    'data': result,  # 不进行JSON序列化
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'retry_count': self.current_retry
                }
                
                self.result.emit(data)
                self.status_changed.emit("success")
                self.finished.emit(True)
                return
                
            except Exception as e:
                if self.should_stop:
                    return
                    
                self.current_retry += 1
                self.retry_count_changed.emit(self.current_retry)
                
                if self.current_retry < self.max_retries:
                    self.progress.emit("WARNING", f"第 {self.current_retry} 次重试: {str(e)}")
                    self.status_changed.emit("retrying")
                    time.sleep(min(self.current_retry * 2, 10))
                    
                    if self.browser:
                        try:
                            self.browser.quit()
                        except:
                            pass
                        self.browser = None
                    
                    self.run()
                else:
                    self.error.emit(self.url, str(e))
                    self.status_changed.emit("failed")
                    self.finished.emit(False)
                    
        except Exception as e:
            self.error.emit(self.url, str(e))
            self.status_changed.emit("failed")
            self.finished.emit(False)
        finally:
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
                self.browser = None

    def download_images(self, name, image_urls):
        """下载图片"""
        try:
            # 创建保存目录
            save_dir = os.path.join('downloads', 
                                  f"{self.url.split('?')[0].split('/')[-1]}_{int(time.time())}")
            img_dir = os.path.join(save_dir, name)
            os.makedirs(img_dir, exist_ok=True)
            
            # 下载图片
            for i, url in enumerate(image_urls):
                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        file_path = os.path.join(img_dir, f'image_{i+1}.jpg')
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        self.progress.emit("INFO", f"已下载图片 {i+1}/{len(image_urls)}")
                except Exception as e:
                    self.progress.emit("WARNING", f"下载图片 {i+1} 失败: {str(e)}")
                    
        except Exception as e:
            self.progress.emit("ERROR", f"创建图片目录失败: {str(e)}")

    def stop(self):
        """停止爬虫"""
        try:
            self.should_stop = True
            self.status_changed.emit("stopped")
            
            # 关闭浏览器
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
                finally:
                    self.browser = None
            
            # 等待线程完成
            self.wait(1000)  # 等待最多1秒
            
        except Exception as e:
            print(f"Error stopping crawler thread: {str(e)}")

    def handle_crawler_result(self, result):
        """处理爬虫结果"""
        try:
            # 解析数据
            data = json.loads(result['data'])
            
            # 保存到数据库
            self.db.save_record(result)
            self.log_message("INFO", f"数据已保存: {data.get('title', '未知标题')}")
            
            # 更新历史记录表格
            self.refresh_history()
            
        except Exception as e:
            self.log_message("ERROR", f"保存数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def download_media_files(self, result, record_id):
        """下载媒体文件"""
        try:
            # 创建保存目录
            base_dir = os.path.join('downloads', f"{record_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # 下载图片
            if 'images' in result:
                image_dir = os.path.join(base_dir, 'images')
                os.makedirs(image_dir, exist_ok=True)
                
                for i, img_url in enumerate(result['images']):
                    try:
                        response = requests.get(img_url, timeout=30)
                        if response.status_code == 200:
                            file_path = os.path.join(image_dir, f'image_{i+1}.jpg')
                            with open(file_path, 'wb') as f:
                                f.write(response.content)
                            # 保存记录
                            self.parent().db.save_media_file(record_id, 'image', file_path, img_url)
                            self.progress.emit("INFO", f"已下载图片 {i+1}")
                    except Exception as e:
                        self.progress.emit("WARNING", f"下载图片失败: {str(e)}")
            
            # 下载视频
            if 'videos' in result:
                video_dir = os.path.join(base_dir, 'videos')
                os.makedirs(video_dir, exist_ok=True)
                
                for i, video_url in enumerate(result['videos']):
                    try:
                        response = requests.get(video_url, timeout=60, stream=True)
                        if response.status_code == 200:
                            file_path = os.path.join(video_dir, f'video_{i+1}.mp4')
                            with open(file_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            # 保存记录
                            self.parent().db.save_media_file(record_id, 'video', file_path, video_url)
                            self.progress.emit("INFO", f"已下载视频 {i+1}")
                    except Exception as e:
                        self.progress.emit("WARNING", f"下载视频失败: {str(e)}")
                        
        except Exception as e:
            self.progress.emit("ERROR", f"下载媒体文件失败: {str(e)}")

def main():
    """程序入口函数"""
    try:
        # 设置异常钩子
        sys._excepthook = sys.excepthook
        def exception_hook(exctype, value, traceback):
            print('Exception hook called')
            print(exctype, value, traceback)
            sys._excepthook(exctype, value, traceback)
            sys.exit(1)
        sys.excepthook = exception_hook

        app = QApplication(sys.argv)
        
        # 设置应用程序异常处理
        def handle_exception(exc_type, exc_value, exc_traceback):
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            QMessageBox.critical(None, "错误", 
                f"程序发生错误:\n{str(exc_value)}\n\n详细信息已记到日志文件。")
            logging.error(error_msg)
            
        sys.excepthook = handle_exception
        
        window = MainWindow()
        window.show()
        return app.exec()
        
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "错误", f"程序启动失败:\n{str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())