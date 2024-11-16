# 微店商品爬虫工具

## 版本记录

### v1.3.0 (2024-11-16)
- 优化了元素选择器界面
- 恢复可视化选择元素功能
- 移除了手动输入选择器功能
- 改进了选择器生成逻辑
- 优化了错误处理机制
- 改进了用户界面交互
- 添加了更多的用户提示

### v1.2.0 (2024-11-16)
- 添加了模板管理系统
- 支持保存和加载爬取模板
- 添加了模板编辑功能
- 支持按平台分类模板
- 添加了模板使用统计
- 优化了数据序列化逻辑
- 改进了重试机制
- 添加了配置管理系统
- 支持自动备份数据库

### v1.1.0 (2024-11-15)
- 添加了图片和视频的下载功能
- 添加了媒体文件的持久化存储
- 修复了元素选择器中URL检测的问题
- 改进了数据库结构，支持媒体文件记录
- 优化了ChromeDriver的启动配置

### v1.0.0 (2024-11-15)
- 初始版本发布
- 修复了程序启动时的闪退问题
- 修复了ChromeDriver自动关闭的问题
- 添加了全局异常处理
- 改进了日志记录系统
- 优化了元素选择器功能
- 添加了多元素选择支持

## 最新功能

### 元素选择器
- 可视化选择页面元素
- 实时预览选择内容
- 自动生成选择器规则
- 优化的用户界面
- 更好的错误提示

### 模板管理
- 支持创建和编辑爬取模板
- 按平台分类管理模板
- 记录模板使用统计
- 支持模板导入导出
- 实时预览模板效果

### 配置管理
- 支持自定义爬虫配置
- 支持UI主题配置
- 支持网络代理配置
- 支持数据库配置
- 配置文件自动保存

### 数据备份
- 支持数据库自动备份
- 自定义备份间隔
- 自动清理旧备份
- 支持手动备份还原

## 使用说明

### 1. 元素选择
1. 点击"添加选择器"按钮
2. 输入选择器名称（如：商品标题）
3. 点击"选择"按钮
4. 在打开的网页中点击要爬取的元素
5. 确认预览内容无误后点击"确定"

### 2. 模板使用
1. 选择已有模板或创建新模板
2. 可以编辑和修改现有模板
3. 支持导入导出模板
4. 记录模板使用频率

### 3. 爬取控制
1. 设置爬取延迟
2. 选择是否下载媒体文件
3. 支持批量爬取
4. 自动失败重试

## 待优化功能
- [ ] 优化选择器生成算法
- [ ] 添加更多选择器类型支持
- [ ] 改进元素预览功能
- [ ] 添加批量选择功能
- [ ] 优化模板推荐系统

## 技术栈
- **GUI框架**: PyQt6
- **爬虫核心**: Selenium
- **浏览器驱动**: ChromeDriver
- **数据存储**: SQLite3
- **数据处理**: pandas
- **数据导出**: openpyxl (Excel), csv, json

## 环境要求
- Python 3.7+
- Chrome浏览器
- ChromeDriver
- PyQt6
- Selenium
- pandas
- openpyxl

## 安装说明
1. 克隆代码仓库
2. 安装依赖包: `pip install -r requirements.txt`
3. 安装Chrome浏览器和ChromeDriver
4. 运行程序: `python run_spider.py`

## 注意事项
- 请遵守网站的爬虫协议
- 建议设置适当的爬取延迟
- 定期备份重要数据
- 及时更新ChromeDriver
