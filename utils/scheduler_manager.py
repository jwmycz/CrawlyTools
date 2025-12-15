from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from core.db_manager import DBManager
from core.crawler_manager import CrawlerManager
import time
import logging
import threading

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, crawler_manager):
        self.scheduler = BackgroundScheduler()
        self.db_manager = crawler_manager.db_manager  # 使用传入的crawler_manager中的db_manager，而不是创建新实例
        self.crawler_manager = crawler_manager
        self.job_map = {}
        self.lock = threading.Lock()
        
        # 添加事件监听器
        self.scheduler.add_listener(self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # 调度器初始化完成，任务将在start()方法中加载
        print("调度器初始化完成")
    
    def load_tasks(self):
        """从数据库加载所有定时任务"""
        print("开始加载定时任务...")
        try:
            cron_tasks = self.db_manager.get_all_cron_tasks()
            print(f"从数据库获取到 {len(cron_tasks)} 个定时任务")
            for task in cron_tasks:
                try:
                    task_name, cron_expression, enabled, params, last_run, next_run = task
                    print(f"加载定时任务: {task_name}, 表达式: {cron_expression}, 状态: {'启用' if enabled else '禁用'}")
                    self.add_job(task_name, cron_expression, bool(enabled), params)
                except Exception as e:
                    logger.error(f"加载定时任务失败: {task}, 错误: {e}")
                    print(f"加载定时任务失败: {task}, 错误: {e}")
            print("定时任务加载完成")
        except Exception as e:
            logger.error(f"从数据库获取定时任务失败: {e}")
            print(f"从数据库获取定时任务失败: {e}")
    
    def add_job(self, task_name, cron_expression, enabled=True, params=None):
        """添加或更新定时任务"""
        with self.lock:
            # 先移除已有的同名任务
            if task_name in self.job_map:
                self.scheduler.remove_job(self.job_map[task_name])
                del self.job_map[task_name]
        
        # 解析参数
        parsed_params = params if isinstance(params, dict) else self._parse_params(params)
        
        # 添加新任务
        try:
            job = self.scheduler.add_job(
                func=self.run_crawler, 
                trigger=CronTrigger.from_crontab(cron_expression),
                id=task_name,
                name=task_name,
                args=[task_name, parsed_params],
                replace_existing=True
            )
            
            with self.lock:
                self.job_map[task_name] = job.id
            
            # 更新数据库中的下一次运行时间
            # 兼容不同版本的APScheduler
            next_run = None
            if hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            self.db_manager.update_cron_task_run_time(task_name, next_run=next_run)
            
            # 如果任务被禁用，则暂停
            if not enabled:
                self.scheduler.pause_job(job.id)
            
            logger.info(f"添加定时任务成功: {task_name}, 表达式: {cron_expression}, 状态: {'启用' if enabled else '禁用'}")
            return True
        except Exception as e:
            logger.error(f"添加定时任务失败: {task_name}, 错误: {e}")
            return False
    
    def remove_job(self, task_name):
        """移除定时任务"""
        with self.lock:
            if task_name in self.job_map:
                job_id = self.job_map[task_name]
                self.scheduler.remove_job(job_id)
                del self.job_map[task_name]
                # 从数据库删除
                self.db_manager.delete_cron_task(task_name)
                logger.info(f"移除定时任务成功: {task_name}")
                return True
        logger.warning(f"定时任务不存在: {task_name}")
        return False
    
    def update_job(self, task_name, cron_expression, enabled=True, params=None):
        """更新定时任务"""
        # 先删除旧任务，再添加新任务
        self.remove_job(task_name)
        return self.add_job(task_name, cron_expression, enabled, params)
    
    def enable_job(self, task_name, enabled=True):
        """启用或禁用定时任务"""
        with self.lock:
            if task_name in self.job_map:
                job_id = self.job_map[task_name]
                if enabled:
                    self.scheduler.resume_job(job_id)
                else:
                    self.scheduler.pause_job(job_id)
                # 更新数据库状态
                self.db_manager.enable_cron_task(task_name, enabled)
                logger.info(f"{'启用' if enabled else '禁用'}定时任务成功: {task_name}")
                return True
        logger.warning(f"定时任务不存在: {task_name}")
        return False
    
    def _parse_params(self, params_str):
        """解析参数字符串为字典"""
        params = {}
        if not params_str:
            return params
        try:
            # 尝试直接解析为字典
            if isinstance(params_str, str):
                import ast
                # 首先尝试将字符串解析为字典
                try:
                    params = ast.literal_eval(params_str)
                    # 确保解析结果是字典
                    if not isinstance(params, dict):
                        params = {}
                except:
                    # 如果直接解析失败，尝试解析为key=value格式
                    params = {}
                    
                    # 检查是否为直接的命令行参数字符串，如"--env ly --debug"
                    if params_str.strip().startswith("--"):
                        # 特殊处理：直接作为__args__参数
                        params["__args__"] = params_str.strip()
                    else:
                        # 传统的key=value格式
                        pairs = params_str.split(',')
                        for pair in pairs:
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                params[key.strip()] = value.strip()
                            else:
                                # 单个值，如--verbose
                                key = pair.strip()
                                if key.startswith("--"):
                                    params[key] = ""
                                else:
                                    params[key] = ""
        except Exception as e:
            logger.error(f"解析参数失败: {e}")
        return params
    
    def run_crawler(self, task_name, params=None):
        """定时任务回调函数，执行爬虫"""
        logger.info(f"定时任务触发: {task_name}, 参数: {params}")
        print(f"定时任务触发: {task_name}, 参数: {params}")
        
        # 更新数据库中的最后运行时间
        last_run = time.strftime('%Y-%m-%d %H:%M:%S')
        self.db_manager.update_cron_task_run_time(task_name, last_run=last_run)
        logger.info(f"更新任务 {task_name} 最后运行时间为: {last_run}")
        print(f"更新任务 {task_name} 最后运行时间为: {last_run}")
        
        # 执行爬虫
        try:
            print(f"正在执行爬虫: {task_name}")
            logger.info(f"正在执行爬虫: {task_name}")
            self.crawler_manager.run_crawler(task_name, params)
            logger.info(f"定时任务执行成功: {task_name}")
            print(f"定时任务执行成功: {task_name}")
        except Exception as e:
            logger.error(f"定时任务执行失败: {task_name}, 错误: {e}")
            print(f"定时任务执行失败: {task_name}, 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def job_listener(self, event):
        """任务执行事件监听器"""
        if event.exception:
            logger.error(f"定时任务 {event.job_id} 执行出错: {event.exception}")
        else:
            logger.info(f"定时任务 {event.job_id} 执行成功")
        
        # 更新下一次运行时间
        job = self.scheduler.get_job(event.job_id)
        if job:
            # 兼容不同版本的APScheduler
            next_run = None
            if hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            self.db_manager.update_cron_task_run_time(event.job_id, next_run=next_run)
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")
            print("调度器已启动")
            # 测试添加一个简单的任务，验证调度器是否正常工作
            # try:
                # 添加一个简单的测试任务，每秒执行一次，只执行3次
            #     def test_job():
            #         print("测试任务执行成功")
            #         logger.info("测试任务执行成功")
            #     # 只在开发环境添加测试任务
            #     import os
            #     if os.environ.get('DEBUG', 'false').lower() == 'true':
            #         self.scheduler.add_job(
            #             func=test_job,
            #             trigger='interval',
            #             seconds=1,
            #             id='test_job',
            #             name='test_job',
            #             replace_existing=True,
            #             max_instances=1,
            #             misfire_grace_time=10
            #         )
            #         logger.info("添加测试任务成功")
            #         print("添加测试任务成功")
            # except Exception as e:
            #     logger.error(f"添加测试任务失败: {e}")
            #     print(f"添加测试任务失败: {e}")
            
            # 在调度器启动后加载定时任务
            # print("调度器启动后开始加载定时任务")
            # threading.Thread(target=self.load_tasks, daemon=True).start()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已停止")
    

    
    def get_job_status(self, task_name):
        """获取任务状态"""
        with self.lock:
            if task_name in self.job_map:
                job_id = self.job_map[task_name]
                job = self.scheduler.get_job(job_id)
                if job:
                    # 兼容不同版本的APScheduler
                    next_run = None
                    if hasattr(job, 'next_run_time') and job.next_run_time:
                        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
                    # 检查任务是否启用：如果next_run_time不为None，则任务启用
                    enabled = job.next_run_time is not None
                    return {
                        'task_name': task_name,
                        'enabled': enabled,
                        'next_run': next_run,
                        'job_id': job.id
                    }
        return None
    
    def get_all_job_status(self):
        """获取所有任务状态"""
        status_list = []
        try:
            with self.lock:
                for task_name, job_id in self.job_map.items():
                    job = self.scheduler.get_job(job_id)
                    if job:
                        # 兼容不同版本的APScheduler
                        next_run = None
                        if hasattr(job, 'next_run_time') and job.next_run_time:
                            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
                        # 检查任务是否启用：如果next_run_time不为None，则任务启用
                        enabled = job.next_run_time is not None
                        status_list.append({
                            'task_name': task_name,
                            'enabled': enabled,
                            'next_run': next_run,
                            'job_id': job.id
                        })
            logger.info(f"获取所有任务状态成功，共 {len(status_list)} 个任务")
            print(f"获取所有任务状态成功，共 {len(status_list)} 个任务")
            return status_list
        except Exception as e:
            logger.error(f"获取所有任务状态失败: {e}")
            print(f"获取所有任务状态失败: {e}")
            import traceback
            traceback.print_exc()
            return status_list