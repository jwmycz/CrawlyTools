import threading
import time
import logging
from abc import ABC, abstractmethod

class BaseCrawler(ABC, threading.Thread):
    def __init__(self, task_name, params=None):
        threading.Thread.__init__(self)
        self.task_name = task_name
        self.params = params or {}
        self.status = "未运行"
        self.last_run_time = None
        self.error_info = None
        self.running = False
        self.logger = logging.getLogger(task_name)
        self.logs = []
        
    def run(self):
        self.status = "运行中"
        self.last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.running = True
        self.logs.clear()
        self.error_info = None
        
        try:
            self.logger.info(f"开始运行爬虫: {self.task_name}")
            self.logger.info(f"参数: {self.params}")
            self.crawl()
            self.status = "完成"
            self.logger.info(f"爬虫运行完成: {self.task_name}")
        except Exception as e:
            self.status = "失败"
            self.error_info = str(e)
            self.logger.error(f"爬虫运行失败: {self.task_name}")
            self.logger.error(f"错误信息: {e}")
        finally:
            self.running = False
    
    @abstractmethod
    def crawl(self):
        pass
    
    def stop(self):
        self.running = False
        self.status = "未运行"
        self.logger.info(f"爬虫已停止: {self.task_name}")
    
    def get_logs(self):
        return self.logs
    
    def add_log(self, message):
        self.logs.append(message)
