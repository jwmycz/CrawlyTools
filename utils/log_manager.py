import logging
import os
from logging.handlers import RotatingFileHandler

class LogManager:
    def __init__(self, log_dir="logs"):
        import os
        # 确保日志目录在当前工作目录
        self.log_dir = os.path.join(os.getcwd(), log_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"已创建日志目录: {self.log_dir}")
        
        # 配置根日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def get_logger(self, name):
        # 为每个任务创建一个独立的logger，使用唯一名称
        logger = logging.getLogger(f"crawler.{name}")
        
        # 清除已有处理器，确保每个任务都有独立的日志文件
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        
        # 创建文件处理器
        log_file = os.path.join(self.log_dir, f"{name}.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'  # 明确指定utf-8编码，解决中文乱码问题
        )
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # 防止日志传播到父logger
        
        return logger
    
    def get_log_content(self, name, max_lines=200):
        """
        获取日志内容，只返回最新的max_lines行
        
        Args:
            name: 任务名称
            max_lines: 最大显示行数，默认为200
            
        Returns:
            最新的max_lines行日志内容
        """
        log_file = os.path.join(self.log_dir, f"{name}.log")
        if not os.path.exists(log_file):
            return ""
        
        try:
            # 优先使用utf-8编码
            with open(log_file, 'r', encoding='utf-8') as f:
                return self._get_last_n_lines(f, max_lines)
        except UnicodeDecodeError:
            try:
                # 如果utf-8失败，尝试使用gbk编码
                with open(log_file, 'r', encoding='gbk') as f:
                    return self._get_last_n_lines(f, max_lines)
            except:
                # 如果都失败，返回空字符串
                return ""
        except Exception:
            # 其他异常情况，返回空字符串
            return ""
    
    def _get_last_n_lines(self, file_obj, max_lines):
        """
        从文件对象中获取最后N行，高效处理大文件
        
        Args:
            file_obj: 文件对象
            max_lines: 最大行数
            
        Returns:
            最后N行的内容
        """
        if max_lines <= 0:
            return ""
        
        buf = []
        buffer_size = 1024 * 4  # 4KB缓冲区
        
        # 移动到文件末尾
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        
        # 计算需要读取的最大位置
        max_pos = max(0, file_size - buffer_size * (max_lines + 1))
        
        # 从后往前读取缓冲区
        pos = file_size
        while pos > max_pos:
            # 计算当前缓冲区的起始位置
            read_pos = max(max_pos, pos - buffer_size)
            file_obj.seek(read_pos)
            
            # 读取缓冲区内容
            buffer = file_obj.read(pos - read_pos)
            pos = read_pos
            
            # 将缓冲区内容按行分割，并添加到结果列表
            buf.extend(buffer.splitlines(True))  # True保留换行符
            
            # 如果已经获取了足够的行，提前结束
            if len(buf) >= max_lines:
                break
        
        # 只保留最后max_lines行
        lines = buf[-max_lines:]
        
        # 确保第一行是完整的
        if len(lines) > 1 and not lines[0].endswith('\n'):
            lines.pop(0)
        
        return ''.join(lines)
    
    def clear_log(self, name):
        log_file = os.path.join(self.log_dir, f"{name}.log")
        if os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("")
