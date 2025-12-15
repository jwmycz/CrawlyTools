# 爬虫管理系统

## 项目简介

CrawlyTools是一个爬虫管理系统，提供了图形化界面用于管理、运行和调度各种爬虫任务。系统支持多线程爬虫执行、动态模块加载、项目导入、定时任务管理等功能，为爬虫开发和管理提供了便捷的解决方案。

## 功能特点

- 🎨 **图形化界面**：基于wxPython构建的友好界面，方便操作和管理
- 🧵 **多线程执行**：支持并发运行多个爬虫任务，提高执行效率
- 🔄 **动态模块加载**：自动从crawlers目录加载爬虫模块，支持热重载
- 📦 **项目导入**：支持导入单个Python文件、项目压缩包或整个项目目录
- ⏰ **定时任务**：基于APScheduler的定时任务管理，支持Cron表达式
- 📊 **系统监控**：实时监控系统资源使用情况
- 📝 **日志管理**：完善的日志记录和查看功能
- ⚙️ **参数配置**：支持为每个爬虫任务配置自定义参数

## 系统架构

```
CrawlyTools/
├── core/              # 核心模块
│   ├── base_crawler.py      # 爬虫基类
│   ├── crawler_manager.py   # 爬虫管理器
│   └── db_manager.py        # 数据库管理器
├── crawlers/          # 爬虫模块目录
├── utils/             # 工具模块
│   ├── log_manager.py       # 日志管理器
│   └── scheduler_manager.py # 调度管理器
├── main.py            # 主程序入口
├── requirements.txt   # 依赖包列表
└── README.md          # 项目说明文档
```

### 核心组件

- **BaseCrawler**：所有爬虫的基类，提供基本的爬虫生命周期管理
- **CrawlerManager**：负责爬虫的加载、运行和管理
- **CrawlerWrapper**：包装自定义脚本，使其能够在系统中运行
- **LogManager**：处理所有日志记录和查看功能
- **DBManager**：管理定时任务和任务状态的数据库操作
- **SchedulerManager**：管理定时任务的调度执行

## 安装步骤

### 1. 克隆或下载项目

```bash
git clone https://github.com/jwmycz/CrawlyTools
cd CrawlyTools
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 使用方法

### 基本操作

1. **运行爬虫**：选择任务列表中的爬虫，点击"运行选中任务"按钮
2. **停止爬虫**：选择正在运行的爬虫，点击"停止选中任务"按钮
3. **定时设置**：点击"定时设置"按钮，配置定时任务
4. **重新加载**：点击"重新加载模块"按钮，重新加载所有爬虫模块
5. **导入模块**：点击"导入爬虫模块"按钮，导入新的爬虫文件或项目

### 参数设置

爬虫参数可以通过以下方式设置：

1. **双击任务**：在任务列表中双击要设置参数的任务
2. **右键菜单**：在任务列表中右键点击任务，选择"编辑参数"

支持的参数格式：

- **key=value格式**：`env=ly,debug=True`
- **命令行参数格式**：`--env ly --debug`
- **字典格式**：`{"env":"ly","debug":true}`

### 项目导入

系统支持三种导入方式：

1. **单个Python文件**：导入单个爬虫脚本文件
2. **项目压缩包(.zip)**：导入完整的项目压缩包
3. **项目目录**：直接导入项目目录

导入时会保留项目的目录结构，并允许用户选择运行文件。

## 爬虫开发规范

### 基于BaseCrawler开发

```python
from core.base_crawler import BaseCrawler

class MyCrawler(BaseCrawler):
    def __init__(self, task_name):
        super().__init__(task_name)
        # 初始化配置
    
    def crawl(self):
        # 爬虫核心逻辑
        self.logger.info("开始爬取数据")
        # 实现爬取逻辑
        self.logger.info("爬取完成")
```

### 脚本式爬虫

也可以直接编写脚本式爬虫，系统会通过CrawlerWrapper包装执行：

```python
import requests

# 脚本式爬虫逻辑
print("开始爬取数据")
response = requests.get("https://example.com")
print(f"响应状态：{response.status_code}")
print("爬取完成")
```

## 定时任务管理

系统提供了统一的定时任务管理界面：

1. **添加任务**：点击"添加定时任务"按钮，设置任务名、Cron表达式和参数
2. **编辑任务**：选择任务后点击"编辑选中任务"按钮
3. **删除任务**：选择任务后点击"删除选中任务"按钮
4. **刷新任务**：点击"刷新任务列表"按钮，更新任务状态

### Cron表达式格式

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6) (星期日=0)
│ │ │ │ │
* * * * *
```

示例：
- `0 0 * * *`：每天凌晨执行
- `0 */6 * * *`：每6小时执行一次
- `0 9-17 * * 1-5`：工作日9点到17点，每小时执行一次

## 项目配置

### 环境变量

支持通过.env文件配置系统参数：

```env
# 数据库配置
DB_PATH=./crawler.db

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs

# 系统配置
MAX_CRAWLERS=10
LOG_UPDATE_INTERVAL=1000
```

### 项目配置文件

导入项目时会自动生成`project_config.json`文件，记录项目的运行文件和配置：

```json
{
  "run_file": "start.py",
  "project_name": "my_project"
}
```

## 常见问题

### Q: 导入项目后无法运行怎么办？

A: 请检查：
1. 是否选择了正确的运行文件
2. 项目是否包含必要的依赖
3. 运行文件是否有语法错误

### Q: 爬虫运行时出现"name os is not defined"错误？

A: 这是因为缺少必要的模块导入，请确保在爬虫文件顶部导入了所有需要的模块：

```python
import os
import sys
```

### Q: 如何查看爬虫的详细日志？

A: 选择任务列表中的爬虫，右侧日志面板会显示该爬虫的实时日志。

### Q: 定时任务不执行怎么办？

A: 请检查：
1. Cron表达式是否正确
2. 定时任务是否处于启用状态
3. 系统时间是否正确

## 技术栈

- **Python**：3.10+
- **wxPython**：图形界面框架
- **APScheduler**：定时任务调度
- **SQLite**：任务数据存储
