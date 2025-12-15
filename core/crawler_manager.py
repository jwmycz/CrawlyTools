import importlib.util
import os
import sys
import threading
import time
from core.base_crawler import BaseCrawler
from utils.log_manager import LogManager
from core.db_manager import DBManager

class CrawlerWrapper(BaseCrawler):
    """爬虫包装类，用于包装自定义脚本，使其能够在系统中运行"""
    def __init__(self, task_name, module_path):
        super().__init__(task_name)
        self.module_path = module_path
        self.module_name = os.path.basename(module_path)[:-3]
        self.process = None
    
    def crawl(self):
        """执行自定义脚本"""
        import subprocess
        import sys
        
        try:
            self.logger.info(f"开始执行自定义脚本: {self.module_name}")
            self.logger.info(f"脚本路径: {self.module_path}")
            self.logger.info(f"参数: {self.params}")
            
            # 构建命令行参数
            cmd = [sys.executable, self.module_path]
            
            # 如果有参数，处理参数格式
            if self.params:
                for key, value in self.params.items():
                    if key.startswith("--"):
                        # 直接的命令行选项格式，如 "--env": "ly" 或 "--verbose": ""
                        if value:
                            cmd.append(f"{key}={value}")
                        else:
                            cmd.append(key)
                    elif key == "__args__":
                        # 特殊处理，直接作为命令行参数列表添加
                        # 格式示例: "__args__": "--env ly --debug"
                        if isinstance(value, str):
                            cmd.extend(value.split())
                        elif isinstance(value, list):
                            cmd.extend(value)
                    else:
                        # 传统的key=value格式，转换为--key=value
                        cmd.append(f"--{key}={value}")
            
            # 执行脚本，使用Popen以便能够终止进程，使用text=True并指定编码处理
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8',
                errors='replace',
                cwd=os.path.dirname(self.module_path)
            )
            
            # 读取输出
            try:
                stdout, stderr = self.process.communicate(timeout=3600)
            except subprocess.TimeoutExpired:
                # 超时处理
                if self.process:
                    self.process.terminate()
                raise Exception("脚本执行超时")
            
            # 记录输出
            if stdout:
                self.logger.info(f"脚本输出: {stdout}")
            if stderr:
                self.logger.error(f"脚本错误: {stderr}")
            
            if self.process.returncode == 0:
                self.logger.info(f"自定义脚本执行完成: {self.module_name}")
            else:
                self.logger.error(f"自定义脚本执行失败，返回码: {self.process.returncode}")
                self.error_info = f"脚本执行失败，返回码: {self.process.returncode}\n错误信息: {stderr}"
                raise Exception(f"脚本执行失败，返回码: {self.process.returncode}")
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"自定义脚本执行超时: {self.module_name}")
            self.error_info = "脚本执行超时"
            # 超时后终止进程
            if self.process:
                self.process.terminate()
            raise Exception("脚本执行超时")
        except Exception as e:
            self.logger.error(f"执行自定义脚本时出错: {e}")
            self.error_info = str(e)
            # 出错时确保进程终止
            if self.process:
                self.process.terminate()
            raise
        finally:
            # 确保进程被正确清理
            self.process = None
    
    def stop(self):
        """停止自定义脚本"""
        super().stop()
        # 终止子进程
        if self.process is not None:
            try:
                self.process.terminate()
                self.logger.info(f"已终止自定义脚本进程: {self.task_name}")
            except Exception as e:
                self.logger.error(f"终止自定义脚本进程时出错: {e}")
            finally:
                self.process = None

class CrawlerManager:
    def __init__(self):
        self.crawlers = {}
        self.log_manager = LogManager()
        self.db_manager = DBManager()
        self.load_crawlers()
    
    def load_crawlers(self):
        """加载crawlers目录下所有爬虫模块、自定义脚本和导入的项目"""
        # 获取当前工作目录（确保打包后能找到正确的crawlers目录）
        import os
        import sys
        
        # 优先使用当前工作目录
        crawlers_dir = os.path.join(os.getcwd(), "crawlers")
        
        # 如果当前目录没有crawlers目录，尝试使用可执行文件所在目录
        if not os.path.exists(crawlers_dir):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            crawlers_dir = os.path.join(exe_dir, "crawlers")
        
        # 确保crawlers目录存在
        if not os.path.exists(crawlers_dir):
            os.makedirs(crawlers_dir)
            print(f"已创建crawlers目录: {crawlers_dir}")
        
        # 确保crawlers目录在sys.path中
        if crawlers_dir not in sys.path:
            sys.path.insert(0, crawlers_dir)
        
        # 首先处理直接放在crawlers目录下的单个文件
        for file in os.listdir(crawlers_dir):
            file_path = os.path.join(crawlers_dir, file)
            
            if os.path.isfile(file_path) and file.endswith(".py") and not file.startswith("_"):
                module_name = file[:-3]
                self._load_single_crawler_file(module_name, file_path)
        
        # 然后处理子目录（导入的项目）
        for dir_name in os.listdir(crawlers_dir):
            dir_path = os.path.join(crawlers_dir, dir_name)
            
            if os.path.isdir(dir_path) and not dir_name.startswith("_"):
                self._load_project_crawler(dir_name, dir_path)
    
    def _load_single_crawler_file(self, module_name, file_path):
        """加载单个爬虫文件"""
        try:
            # 检查文件内容，避免加载包含阻塞式调度器的文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果文件包含BlockingScheduler或其他阻塞式组件，跳过或特殊处理
            if 'BlockingScheduler' in content:
                print(f"模块 {module_name} 包含阻塞式调度器，将作为自定义脚本加载")
                # 直接作为自定义脚本处理，不加载模块
                crawler = CrawlerWrapper(module_name, file_path)
                crawler.logger = self.log_manager.get_logger(module_name)
                self.crawlers[module_name] = crawler
                self.db_manager.add_task(module_name, module_name)
                return
            
            # 从crawlers目录加载模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找模块中的爬虫类
            found = False
            for name, cls in module.__dict__.items():
                if isinstance(cls, type) and issubclass(cls, BaseCrawler) and cls != BaseCrawler:
                    # 创建爬虫实例
                    crawler = cls(module_name)
                    # 为爬虫配置logger
                    crawler.logger = self.log_manager.get_logger(module_name)
                    self.crawlers[module_name] = crawler
                    # 添加到数据库
                    self.db_manager.add_task(module_name, module_name)
                    found = True
                    break
            
            if not found:
                # 如果没有找到符合规范的爬虫类，将其作为自定义脚本包装
                print(f"模块 {module_name} 中未找到符合规范的爬虫类，将作为自定义脚本加载")
                crawler = CrawlerWrapper(module_name, file_path)
                # 为爬虫配置logger
                crawler.logger = self.log_manager.get_logger(module_name)
                self.crawlers[module_name] = crawler
                # 添加到数据库
                self.db_manager.add_task(module_name, module_name)
        except Exception as e:
            print(f"加载模块 {module_name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_project_crawler(self, project_name, project_path):
        """加载导入的项目爬虫"""
        try:
            import json
            
            # 检查是否存在项目配置文件
            config_file = os.path.join(project_path, "project_config.json")
            if not os.path.exists(config_file):
                # 如果没有配置文件，尝试查找可能的运行文件
                self._try_load_without_config(project_name, project_path)
                return
            
            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 获取运行文件
            run_file = config.get("run_file")
            if not run_file:
                print(f"项目 {project_name} 配置文件中未指定运行文件")
                return
            
            run_file_path = os.path.join(project_path, run_file)
            if not os.path.exists(run_file_path):
                print(f"项目 {project_name} 的运行文件 {run_file} 不存在")
                return
            
            # 将项目目录添加到sys.path
            if project_path not in sys.path:
                sys.path.insert(0, project_path)
            
            # 创建爬虫实例，使用项目名作为任务名
            crawler = CrawlerWrapper(project_name, run_file_path)
            crawler.logger = self.log_manager.get_logger(project_name)
            self.crawlers[project_name] = crawler
            self.db_manager.add_task(project_name, project_name)
            
            print(f"项目 {project_name} 已加载，运行文件: {run_file}")
        except Exception as e:
            print(f"加载项目 {project_name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _try_load_without_config(self, project_name, project_path):
        """尝试在没有配置文件的情况下加载项目"""
        # 查找项目中的main.py或app.py作为默认运行文件
        default_run_files = ["main.py", "app.py", "run.py", "crawl.py"]
        
        for run_file in default_run_files:
            run_file_path = os.path.join(project_path, run_file)
            if os.path.exists(run_file_path):
                # 将项目目录添加到sys.path
                if project_path not in sys.path:
                    sys.path.insert(0, project_path)
                
                # 创建爬虫实例
                crawler = CrawlerWrapper(project_name, run_file_path)
                crawler.logger = self.log_manager.get_logger(project_name)
                self.crawlers[project_name] = crawler
                self.db_manager.add_task(project_name, project_name)
                
                print(f"项目 {project_name} 已加载（无配置文件），默认运行文件: {run_file}")
                return
        
        print(f"项目 {project_name} 中未找到合适的运行文件")
    
    def get_crawlers(self):
        return self.crawlers
    
    def get_crawler(self, task_name):
        return self.crawlers.get(task_name)
    
    def run_crawler(self, task_name, params=None):
        crawler = self.get_crawler(task_name)
        if crawler:
            if crawler.status != "运行中":
                # 更新参数
                if params:
                    crawler.params = params
                # 启动新线程运行爬虫
                crawler.start()
                return True
        return False
    
    def stop_crawler(self, task_name):
        crawler = self.get_crawler(task_name)
        if crawler:
            crawler.stop()
            return True
        return False
    
    def reload_crawlers(self):
        """重新加载所有爬虫模块"""
        self.crawlers.clear()
        self.load_crawlers()
    
    def get_crawler_status(self, task_name):
        crawler = self.get_crawler(task_name)
        if crawler:
            return {
                "task_name": task_name,
                "status": crawler.status,
                "last_run_time": crawler.last_run_time,
                "error_info": crawler.error_info
            }
        return None
    
    def get_all_crawler_status(self):
        status_list = []
        for task_name in self.crawlers:
            status = self.get_crawler_status(task_name)
            if status:
                status_list.append(status)
        return status_list
