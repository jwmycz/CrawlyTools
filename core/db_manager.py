import sqlite3
import os
import time

class DBManager:
    def __init__(self, db_file="crawler.db"):
        import os
        # 确保数据库文件在当前工作目录
        self.db_file = os.path.join(os.getcwd(), db_file)
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT UNIQUE NOT NULL,
            module_name TEXT NOT NULL,
            status TEXT DEFAULT '未运行',
            last_run_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建任务日志表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            log_level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建任务运行历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            error_info TEXT,
            params TEXT
        )
        ''')
        
        # 创建定时任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cron_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT UNIQUE NOT NULL,
            cron_expression TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            params TEXT,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_task(self, task_name, module_name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO tasks (task_name, module_name, created_at) VALUES (?, ?, ?)",
            (task_name, module_name, time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    
    def update_task_status(self, task_name, status, last_run_time=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        if last_run_time:
            cursor.execute(
                "UPDATE tasks SET status = ?, last_run_time = ? WHERE task_name = ?",
                (status, last_run_time, task_name)
            )
        else:
            cursor.execute(
                "UPDATE tasks SET status = ? WHERE task_name = ?",
                (status, task_name)
            )
        conn.commit()
        conn.close()
    
    def add_task_log(self, task_name, log_level, message):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO task_logs (task_name, log_level, message) VALUES (?, ?, ?)",
            (task_name, log_level, message)
        )
        conn.commit()
        conn.close()
    
    def add_task_history(self, task_name, status, start_time, end_time=None, error_info=None, params=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO task_history (task_name, status, start_time, end_time, error_info, params) VALUES (?, ?, ?, ?, ?, ?)",
            (task_name, status, start_time, end_time, error_info, str(params) if params else None)
        )
        conn.commit()
        conn.close()
    
    def get_tasks(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT task_name, module_name, status, last_run_time FROM tasks")
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def get_task_history(self, task_name, limit=50):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, start_time, end_time, error_info, params FROM task_history WHERE task_name = ? ORDER BY id DESC LIMIT ?",
            (task_name, limit)
        )
        history = cursor.fetchall()
        conn.close()
        return history
    
    def add_or_update_cron_task(self, task_name, cron_expression, enabled=0, params=None):
        """添加或更新定时任务"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cron_tasks (task_name, cron_expression, enabled, params, updated_at) VALUES (?, ?, ?, ?, ?)",
            (task_name, cron_expression, enabled, str(params) if params else None, time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    
    def get_cron_task(self, task_name):
        """获取指定任务的定时设置"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_name, cron_expression, enabled, params, last_run, next_run FROM cron_tasks WHERE task_name = ?",
            (task_name,)
        )
        task = cursor.fetchone()
        conn.close()
        return task
    
    def get_all_cron_tasks(self):
        """获取所有定时任务"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_name, cron_expression, enabled, params, last_run, next_run FROM cron_tasks"
        )
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def enable_cron_task(self, task_name, enabled=True):
        """启用或禁用定时任务"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cron_tasks SET enabled = ? WHERE task_name = ?",
            (1 if enabled else 0, task_name)
        )
        conn.commit()
        conn.close()
    
    def update_cron_task_run_time(self, task_name, last_run=None, next_run=None):
        """更新定时任务的运行时间"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        if last_run and next_run:
            cursor.execute(
                "UPDATE cron_tasks SET last_run = ?, next_run = ? WHERE task_name = ?",
                (last_run, next_run, task_name)
            )
        elif last_run:
            cursor.execute(
                "UPDATE cron_tasks SET last_run = ? WHERE task_name = ?",
                (last_run, task_name)
            )
        elif next_run:
            cursor.execute(
                "UPDATE cron_tasks SET next_run = ? WHERE task_name = ?",
                (next_run, task_name)
            )
        conn.commit()
        conn.close()
    
    def delete_cron_task(self, task_name):
        """删除定时任务"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM cron_tasks WHERE task_name = ?",
            (task_name,)
        )
        conn.commit()
        conn.close()
